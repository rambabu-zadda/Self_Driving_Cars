# backend/trainer_manager.py
import threading
import time
import base64
import io
import math
import os
import uuid
from dataclasses import asdict
from PIL import Image
import numpy as np
from env_highway import HighwayEnv as Env
from agent import DQNAgent
from event_bus import HttpTelemetryPublisher
from experiment_tracker import create_experiment_tracker

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
CHECKPOINT_DIR = os.getenv("CHECKPOINT_DIR", "checkpoints")
CHECKPOINT_INTERVAL = int(os.getenv("CHECKPOINT_INTERVAL", "25"))

def pil_to_b64(pil_img: Image.Image) -> str:
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")

class TrainerManager:
    def __init__(self, event_publisher=None):
        self.thread = None
        self.running = False
        self.paused = False
        self.reset_signal = False
        self.experiment_id = None
        self.event_publisher = event_publisher or HttpTelemetryPublisher()
        self.tracker = create_experiment_tracker()

    def start(self):
        if self.running:
            return False
        self.running = True
        self.paused = False
        self.reset_signal = False
        self.experiment_id = f"dqn-{uuid.uuid4().hex[:12]}"
        self.thread = threading.Thread(target=self._train_loop, daemon=True)
        self.thread.start()
        self._post({"type": "status", "status": "running", "experiment_id": self.experiment_id})
        return True

    def pause(self):
        if not self.running:
            return False
        self.paused = True
        self._post({"type": "status", "status": "paused", "experiment_id": self.experiment_id})
        return True

    def resume(self):
        if not self.running:
            return False
        self.paused = False
        self._post({"type": "status", "status": "running", "experiment_id": self.experiment_id})
        return True

    def reset(self):
        if not self.running:
            return False
        self.reset_signal = True
        self._post({"type": "status", "status": "reset", "experiment_id": self.experiment_id})
        return True

    def _post(self, payload: dict):
        try:
            self.event_publisher.publish(payload)
        except Exception as e:
            print("Telemetry publish failed:", e)

    def _train_loop(self):
        env = Env(render_size=(640, 480))
        # get a sample observation safely
        try:
            obs = env._obs()
        except Exception:
            obs = np.zeros((84, 84, 1), dtype=np.uint8)
        obs_shape = obs.shape
        agent = DQNAgent(obs_shape, n_actions=5)
        hyperparameters = asdict(agent.config)
        self.tracker.start_run(
            experiment_id=self.experiment_id,
            run_name=f"DQN Highway {self.experiment_id}",
            params=hyperparameters,
        )
        self._post(
            {
                "type": "experiment_start",
                "experiment_id": self.experiment_id,
                "name": "DQN Highway Training",
                "algorithm": "Double Dueling DQN",
                "hyperparameters": hyperparameters,
            }
        )
        eps = 1.0
        eps_min = 0.05
        eps_decay = 0.995
        latest_loss = None
        latest_q_value = None

        ep_idx = 1
        last_frame_time = None
        fps_smooth = 0.0

        try:
            while self.running and not self.reset_signal:
                obs = env.reset()
                done = False
                total_reward = 0.0
                steps = 0
                crashes = 0

                self._post({"type": "log", "experiment_id": self.experiment_id, "message": f"Episode {ep_idx} started"})

                while not done and self.running and not self.reset_signal:
                    while self.paused and self.running and not self.reset_signal:
                        time.sleep(0.5)

                    action = agent.act(obs, eps)
                    ns, reward, done, info = env.step(action)

                    # guard reward
                    if reward is None or (isinstance(reward, float) and math.isnan(reward)):
                        reward = 0.0

                    agent.push(obs, action, reward, ns, done)
                    update_metrics = agent.update(batch_size=64)
                    if update_metrics:
                        latest_loss = update_metrics["loss"]
                        latest_q_value = update_metrics["q_value"]

                    obs = ns
                    total_reward += float(reward)
                    steps += 1

                    # compute fps
                    now = time.time()
                    if last_frame_time is None:
                        last_frame_time = now
                    dt = max(1e-6, now - last_frame_time)
                    instant_fps = 1.0 / dt
                    fps_smooth = (fps_smooth * 0.85) + (instant_fps * 0.15)
                    last_frame_time = now

                    # render and publish every N steps
                    if steps % 5 == 0:
                        img = env._render_full() if hasattr(env, "_render_full") else env._render()
                        if isinstance(img, np.ndarray):
                            pil = Image.fromarray(img)
                        else:
                            pil = img

                        png_b64 = pil_to_b64(pil)
                        # use env.speed (HighwayEnv defines `speed`)
                        speed = float(getattr(env, "speed", 0.0))

                        payload = {
                            "type": "frame",
                            "experiment_id": self.experiment_id,
                            "episode": ep_idx,
                            "step": steps,
                            "png_b64": png_b64,
                            "metrics": {
                                "episode": ep_idx,
                                "reward": float(total_reward),
                                "reward_step": float(reward),
                                "crashes": int(crashes),
                                "steps": int(steps),
                                "fps": float(fps_smooth),
                                "speed": float(speed),
                                "epsilon": float(eps),
                                "loss": latest_loss,
                                "q_value": latest_q_value,
                                "replay_size": len(agent.replay_buffer),
                                "progress": float(info.get("progress", 0.0)),
                                "reward_breakdown": info.get("reward_breakdown", {}),
                                "action": info.get("action")
                            }
                        }
                        self._post(payload)
                        self.tracker.log_metrics(
                            {
                                "reward_total": total_reward,
                                "reward_step": reward,
                                "loss": latest_loss,
                                "q_value": latest_q_value,
                                "epsilon": eps,
                                "replay_size": len(agent.replay_buffer),
                                "speed": speed,
                                "fps": fps_smooth,
                                "progress": info.get("progress", 0.0),
                            },
                            step=(ep_idx * 10_000) + steps,
                        )

                        # send metric point for chart (total_reward)
                        self._post({"type": "metric_point", "experiment_id": self.experiment_id, "episode": ep_idx, "point": float(total_reward), "step": steps})

                    # crash detection via env info
                    if info.get("crash") or info.get("crashed"):
                        crashes += 1
                        self._post({"type": "log", "experiment_id": self.experiment_id, "message": f"Crash detected at step {steps} in episode {ep_idx}"})
                        self._post({"type": "error", "experiment_id": self.experiment_id, "message": f"Crash in episode {ep_idx} at step {steps}"})
                        done = True

                    if steps > 1500:
                        done = True

                # episode finished
                self._post(
                    {
                        "type": "episode",
                        "experiment_id": self.experiment_id,
                        "metrics": {
                            "episode": ep_idx,
                            "reward": float(total_reward),
                            "crashes": crashes,
                            "duration": steps,
                            "success": int(bool(info.get("destination_reached"))),
                        },
                    }
                )
                self._post({"type": "log", "experiment_id": self.experiment_id, "message": f"Episode {ep_idx} finished (reward={total_reward:.2f}, steps={steps})"})
                self.tracker.log_metrics(
                    {
                        "episode_reward": total_reward,
                        "episode_crashes": crashes,
                        "episode_steps": steps,
                        "episode_success": int(bool(info.get("destination_reached"))),
                    },
                    step=ep_idx,
                )

                if ep_idx % CHECKPOINT_INTERVAL == 0:
                    checkpoint_path = os.path.join(CHECKPOINT_DIR, f"dqn_episode_{ep_idx}.pt")
                    agent.save(
                        checkpoint_path,
                        metadata={"episode": ep_idx, "epsilon": eps, "reward": total_reward},
                    )
                    self._post(
                        {
                            "type": "checkpoint",
                            "experiment_id": self.experiment_id,
                            "episode": ep_idx,
                            "path": checkpoint_path,
                            "reward": float(total_reward),
                            "epsilon": float(eps),
                        }
                    )
                    self._post({"type": "log", "experiment_id": self.experiment_id, "message": f"Checkpoint saved: {checkpoint_path}"})
                    self.tracker.log_artifact(checkpoint_path)

                ep_idx += 1
                eps = max(eps_min, eps * eps_decay)

            # clean stop
            self.running = False
            self.paused = False
            self.reset_signal = False
            self._post({"type": "experiment_end", "experiment_id": self.experiment_id, "status": "stopped"})
            self.tracker.end_run("FINISHED")
            self._post({"type": "status", "status": "stopped", "experiment_id": self.experiment_id})
            self._post({"type": "log", "experiment_id": self.experiment_id, "message": "Trainer stopped"})
        except Exception as ex:
            self._post({"type": "experiment_end", "experiment_id": self.experiment_id, "status": "failed"})
            self.tracker.end_run("FAILED")
            self._post({"type": "error", "experiment_id": self.experiment_id, "message": f"Trainer crashed: {ex}"})
            self.running = False
            self.paused = False
            self.reset_signal = False
            raise
