# backend/app.py
import base64
import asyncio
import json
import os
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from db import init_db, SessionLocal
from event_bus import RedisCommandPublisher
from models import Checkpoint, Episode, Experiment, Frame, Metric
from trainer_manager import TrainerManager

app = FastAPI(title="Autonomous Driving RL Backend")

# CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Init DB
init_db()

# Simple WS manager
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: dict):
        text = json.dumps(message)
        coros = [ws.send_text(text) for ws in self.active]
        if coros:
            # send concurrently
            import asyncio
            await asyncio.gather(*coros, return_exceptions=True)

manager = ConnectionManager()

# Trainer manager (runs trainer in background thread)
trainer = TrainerManager()
TRAINER_CONTROL_MODE = os.getenv("TRAINER_CONTROL_MODE", "local").lower()
trainer_commands = RedisCommandPublisher() if TRAINER_CONTROL_MODE == "redis" else None
FRAME_STORE_STEP_INTERVAL = int(os.getenv("FRAME_STORE_STEP_INTERVAL", "50"))
MAX_STORED_FRAMES = int(os.getenv("MAX_STORED_FRAMES", "1000"))
FRONTEND_BUILD_DIR = os.getenv(
    "FRONTEND_BUILD_DIR",
    os.path.join(os.path.dirname(__file__), "static"),
)
FRONTEND_ASSETS_DIR = os.path.join(FRONTEND_BUILD_DIR, "static")

if os.path.exists(FRONTEND_ASSETS_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_ASSETS_DIR), name="frontend-static")

@app.get("/")
def read_root():
    index_path = os.path.join(FRONTEND_BUILD_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Backend is running - visit /docs for API docs."}

@app.get("/health")
def health():
    return {"status": "ok"}

# Training control endpoints
@app.post("/train/start")
def train_start():
    return _control_trainer("start", "started")

@app.post("/train/pause")
def train_pause():
    return _control_trainer("pause", "paused")

@app.post("/train/resume")
def train_resume():
    return _control_trainer("resume", "resumed")

@app.post("/train/reset")
def train_reset():
    return _control_trainer("reset", "reset")

@app.get("/train/status")
def train_status():
    return {
        "running": trainer.running,
        "paused": trainer.paused,
        "reset": trainer.reset_signal,
        "experiment_id": trainer.experiment_id,
        "control_mode": TRAINER_CONTROL_MODE,
    }


def _control_trainer(command: str, response_key: str):
    if TRAINER_CONTROL_MODE == "redis":
        subscribers = trainer_commands.publish(command)
        return {
            response_key: True,
            "queued": True,
            "subscribers": subscribers,
            "control_mode": TRAINER_CONTROL_MODE,
        }
    actions = {
        "start": trainer.start,
        "pause": trainer.pause,
        "resume": trainer.resume,
        "reset": trainer.reset,
    }
    ok = actions[command]()
    return {response_key: ok, "queued": False, "control_mode": TRAINER_CONTROL_MODE}

# Episodes and frames
@app.get("/episodes")
def get_episodes(limit: int = 50):
    db = SessionLocal()
    rows = db.query(Episode).order_by(Episode.created_at.desc()).limit(limit).all()
    res = [
        {
            'id': r.id,
            'experiment_id': r.experiment_id,
            'episode': r.episode,
            'reward': r.reward,
            'crashes': r.crashes,
            'duration': r.duration,
            'success': bool(r.success),
            'created_at': r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    db.close()
    return res


@app.get("/experiments")
def get_experiments(limit: int = 20):
    db = SessionLocal()
    rows = db.query(Experiment).order_by(Experiment.created_at.desc()).limit(limit).all()
    res = []
    for row in rows:
        episodes = (
            db.query(Episode)
            .filter(Episode.experiment_id == row.id)
            .order_by(Episode.episode.asc())
            .all()
        )
        rewards = [episode.reward for episode in episodes if episode.reward is not None]
        crashes = sum(episode.crashes or 0 for episode in episodes)
        successes = sum(episode.success or 0 for episode in episodes)
        res.append(
            {
                "id": row.id,
                "name": row.name,
                "algorithm": row.algorithm,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "ended_at": row.ended_at.isoformat() if row.ended_at else None,
                "episode_count": len(episodes),
                "average_reward": sum(rewards) / len(rewards) if rewards else None,
                "collision_rate": crashes / len(episodes) if episodes else None,
                "success_rate": successes / len(episodes) if episodes else None,
            }
        )
    db.close()
    return res


@app.get("/experiments/{experiment_id}/metrics")
def get_experiment_metrics(experiment_id: str, limit: int = 500):
    db = SessionLocal()
    rows = (
        db.query(Metric)
        .filter(Metric.experiment_id == experiment_id)
        .order_by(Metric.id.desc())
        .limit(limit)
        .all()
    )
    db.close()
    return [
        {
            "episode": row.episode,
            "step": row.step,
            "reward": row.reward,
            "loss": row.loss,
            "epsilon": row.epsilon,
            "q_value": row.q_value,
            "replay_size": row.replay_size,
            "speed": row.speed,
            "progress": row.progress,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in reversed(rows)
    ]


@app.get("/metrics/latest")
def get_latest_metric():
    db = SessionLocal()
    row = db.query(Metric).order_by(Metric.created_at.desc(), Metric.id.desc()).first()
    db.close()
    if not row:
        return JSONResponse({}, status_code=204)
    return _metric_to_dict(row)


@app.get("/checkpoints")
def get_checkpoints(experiment_id: Optional[str] = None, limit: int = 50):
    db = SessionLocal()
    query = db.query(Checkpoint)
    if experiment_id:
        query = query.filter(Checkpoint.experiment_id == experiment_id)
    rows = query.order_by(Checkpoint.created_at.desc()).limit(limit).all()
    db.close()
    return [
        {
            "id": row.id,
            "experiment_id": row.experiment_id,
            "episode": row.episode,
            "path": row.path,
            "reward": row.reward,
            "epsilon": row.epsilon,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]

@app.get("/frames/latest")
def get_latest_frame():
    db = SessionLocal()
    f = db.query(Frame).order_by(Frame.created_at.desc()).first()
    db.close()
    if not f:
        return JSONResponse({}, status_code=204)
    return {
        "experiment_id": f.experiment_id,
        "episode": f.episode,
        "step": f.step,
        "png_b64": base64.b64encode(f.png).decode('ascii'),
    }

# Publish endpoint (trainer posts here)
@app.post("/publish")
async def publish(request: Request):
    payload = await request.json()

    # Save to DB if present
    try:
        db = SessionLocal()
        experiment_id = payload.get("experiment_id")

        if payload.get("type") == "experiment_start" and experiment_id:
            experiment = db.get(Experiment, experiment_id) or Experiment(id=experiment_id)
            experiment.name = payload.get("name", "DQN Highway Training")
            experiment.algorithm = payload.get("algorithm", "DQN")
            experiment.status = "running"
            experiment.hyperparameters_json = json.dumps(payload.get("hyperparameters", {}))
            db.merge(experiment)
            db.commit()

        if payload.get("type") == "experiment_end" and experiment_id:
            experiment = db.get(Experiment, experiment_id)
            if experiment:
                experiment.status = payload.get("status", "stopped")
                experiment.ended_at = datetime.now(timezone.utc)
                db.commit()

        step = int(payload.get("step", 0))
        should_store_frame = step % FRAME_STORE_STEP_INTERVAL == 0
        if payload.get("type") == "frame" and payload.get("png_b64") and should_store_frame:
            png = base64.b64decode(payload["png_b64"])
            f = Frame(
                experiment_id=experiment_id,
                episode=int(payload.get("episode", 0)),
                step=step,
                png=png,
            )
            db.add(f)
            db.commit()
            stale_ids = [
                row[0]
                for row in db.query(Frame.id)
                .order_by(Frame.id.desc())
                .offset(MAX_STORED_FRAMES)
                .all()
            ]
            if stale_ids:
                db.query(Frame).filter(Frame.id.in_(stale_ids)).delete(
                    synchronize_session=False
                )
                db.commit()

        if payload.get("type") == "frame" and payload.get("metrics") and experiment_id:
            m = payload["metrics"]
            db.add(
                Metric(
                    experiment_id=experiment_id,
                    episode=int(m.get("episode", payload.get("episode", 0))),
                    step=int(m.get("steps", payload.get("step", 0))),
                    reward=_float_or_none(m.get("reward")),
                    loss=_float_or_none(m.get("loss")),
                    epsilon=_float_or_none(m.get("epsilon")),
                    q_value=_float_or_none(m.get("q_value")),
                    replay_size=_int_or_none(m.get("replay_size")),
                    speed=_float_or_none(m.get("speed")),
                    progress=_float_or_none(m.get("progress")),
                )
            )
            db.commit()

        if payload.get("type") == "episode" and payload.get("metrics"):
            m = payload["metrics"]
            e = Episode(
                experiment_id=experiment_id,
                episode=int(m.get("episode", 0)),
                reward=float(m.get("reward", 0.0)),
                crashes=int(m.get("crashes", 0)),
                duration=int(m.get("duration", 0)),
                success=int(m.get("success", 0)),
            )
            db.add(e)
            db.commit()

        if payload.get("type") == "checkpoint" and experiment_id:
            db.add(
                Checkpoint(
                    experiment_id=experiment_id,
                    episode=int(payload.get("episode", 0)),
                    path=payload.get("path", ""),
                    reward=_float_or_none(payload.get("reward")),
                    epsilon=_float_or_none(payload.get("epsilon")),
                )
            )
            db.commit()
    except Exception as e:
        print("DB save failed:", e)
    finally:
        try: db.close()
        except: pass

    # Broadcast via WS
    try:
        await manager.broadcast(payload)
    except Exception as e:
        print("Broadcast error:", e)

    return {"status": "ok"}


def _float_or_none(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _metric_to_dict(row: Metric):
    return {
        "experiment_id": row.experiment_id,
        "episode": row.episode,
        "step": row.step,
        "reward": row.reward,
        "loss": row.loss,
        "epsilon": row.epsilon,
        "q_value": row.q_value,
        "replay_size": row.replay_size,
        "speed": row.speed,
        "progress": row.progress,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if message == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "pong"}))
    except Exception:
        manager.disconnect(websocket)
