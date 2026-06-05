# Self-Driving Cars RL

A full-stack reinforcement learning prototype for training and evaluating an
autonomous highway-driving policy.

The platform includes a vector-state highway environment, a PyTorch DQN agent,
live FastAPI/WebSocket telemetry, checkpointing, deterministic evaluation, and
a React research dashboard.

## Portfolio Highlights

- End-to-end AI product: simulation environment, RL agent, API, database,
  dashboard, Docker, and cloud deployment.
- Deployment-friendly telemetry: WebSocket streaming locally with HTTP polling
  fallback for cloud platforms such as Render.
- Research-style experiment tracking: reward, loss, Q-value, epsilon, replay
  size, speed, progress, crash rate, success rate, and checkpoints.
- Interview-ready dashboard: live track feed, trainer controls, KPI cards,
  reward moving average, route progress, and experiment insights.
- Engineering proof: backend tests, frontend production build, Dockerized
  services, GitHub Actions CI, Alembic migrations, and evaluation scripts.

## Current Capabilities

- DQN with experience replay, target network, Double DQN, and Dueling DQN
- MLP state-vector policy and optional CNN image policy support
- Epsilon-greedy training and deterministic evaluation mode
- Checkpoint save/load and resumable model state
- Highway termination on collision, off-road movement, destination, or timeout
- Reward breakdown for progress, lane keeping, safety, lane changes, collisions,
  off-road movement, and destination completion
- Live simulation frames, reward curve, loss, epsilon, replay size, and actions
- Experiment records with average reward, collision rate, success rate, metrics,
  and checkpoint metadata
- Optional MLflow tracking for parameters, scalar metrics, and checkpoint
  artifacts
- PostgreSQL-ready schema with Alembic migrations and SQLite fallback for local
  development
- Docker Compose and GitHub Actions build/test workflow

## Architecture

```mermaid
flowchart LR
    UI["React Research Dashboard"] <-->|REST + WebSocket| API["FastAPI API"]
    API --> Trainer["DQN Trainer"]
    Trainer --> Env["Highway Environment"]
    Trainer --> Agent["PyTorch DQN Agent"]
    API --> DB["PostgreSQL Experiment Store"]
    Agent --> Checkpoints["Model Checkpoints"]
```

Docker Compose runs a Redis-backed trainer worker. For lightweight local
development, the API can still run the trainer in-process by using
`TRAINER_CONTROL_MODE=local` and SQLite.

## State Representation

The environment returns a normalized 16-value vector:

- ego lane, lane-center offset, speed, and route progress
- nearest vehicle distance and relative speed ahead and behind in each lane

Rendering remains separate from observations so training does not need to
generate a full image for every state.

## Quick Start

```bash
docker compose up --build
```

- Dashboard: <http://localhost:3000>
- API docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>
- PostgreSQL: `localhost:5432`
- MLflow: <http://localhost:5000>

## Cloud Deployment

For cloud deployment, Railway and Render are the simplest options. The project
is a multi-service system, so deploy the API, worker, frontend, PostgreSQL, and
Redis/Key Value as separate services.

For a simple one-service demo deployment, use
[Render Single-Service Deployment](docs/deployment-render-single-service.md).

See [Railway Deployment Guide](docs/deployment-railway.md).
See [Render Deployment Guide](docs/deployment-render.md).

## Local Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-docker.txt pytest
uvicorn app:app --host 0.0.0.0 --port 8000
```

On Windows, activate the environment with `.venv\Scripts\activate`.

Local backend mode defaults to `TRAINER_CONTROL_MODE=local`, so `/train/start`
starts training inside the FastAPI process. For worker mode, run Redis, start
FastAPI with `TRAINER_CONTROL_MODE=redis`, and run:

```bash
cd backend
python trainer_worker.py
```

## Database Migrations

Docker runs migrations automatically before the API starts:

```bash
cd backend
alembic upgrade head
```

Local development defaults to SQLite through `DATABASE_URL=sqlite:///./data.db`.
Production-style Docker Compose uses PostgreSQL:

```text
postgresql://rl_user:rl_password@postgres:5432/self_driving_rl
```

## Experiment Tracking

The trainer supports optional MLflow logging. Local development defaults to
`EXPERIMENT_TRACKER=none`. Docker Compose enables MLflow for the trainer:

```text
EXPERIMENT_TRACKER=mlflow
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_EXPERIMENT_NAME=Self-Driving Cars RL
```

Tracked data includes DQN hyperparameters, reward, loss, Q-value, epsilon,
replay-buffer size, speed, FPS, progress, episode summaries, and checkpoint
artifacts.

## Evaluation

Training saves a checkpoint every 25 episodes by default.

```bash
cd backend
python evaluate.py checkpoints/dqn_episode_25.pt --episodes 20 --seed 1000
```

The command reports average reward, collision rate, success rate, and average
episode length. Use only measured values from this output in reports or resumes.

Recommended evaluation protocol for resume/report claims:

1. Train until at least one checkpoint is saved.
2. Evaluate the checkpoint on 20 or more fixed-seed episodes.
3. Compare it with the random baseline using `benchmark.py`.
4. Report only measured values, for example average reward, success rate,
   collision rate, and average episode length.
5. Include the seed, episode count, and checkpoint name beside any result.

## Benchmarking

Compare the random baseline with one or more trained DQN checkpoints:

```bash
cd backend
python benchmark.py --episodes 50 --seed 1000 \
  --checkpoint checkpoints/dqn_episode_25.pt
```

The report includes average reward, collision rate, success rate, off-road rate,
average episode length, and action distribution.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `BACKEND_URL` | `http://127.0.0.1:8000` | Trainer publish URL |
| `DATABASE_URL` | `sqlite:///./data.db` | SQLAlchemy database URL |
| `AUTO_CREATE_TABLES` | `true` | SQLite dev convenience; use Alembic for Postgres |
| `EXPERIMENT_TRACKER` | `none` | `none` or `mlflow` |
| `MLFLOW_TRACKING_URI` | `file:./mlruns` | MLflow tracking server or local store |
| `MLFLOW_EXPERIMENT_NAME` | `Self-Driving Cars RL` | MLflow experiment name |
| `TRAINER_CONTROL_MODE` | `local` | `local` or `redis` trainer control |
| `REDIS_URL` | `redis://redis:6379/0` | Redis command queue URL |
| `TRAINER_COMMAND_CHANNEL` | `trainer.commands` | Redis trainer command channel |
| `CHECKPOINT_DIR` | `checkpoints` | Model checkpoint directory |
| `CHECKPOINT_INTERVAL` | `25` | Episodes between checkpoints |
| `FRAME_STORE_STEP_INTERVAL` | `50` | Store one frame every N steps |
| `MAX_STORED_FRAMES` | `1000` | Maximum retained frame rows |
| `REACT_APP_BACKEND` | `http://127.0.0.1:8000` | Frontend API URL |
| `REACT_APP_WS_URL` | derived from API URL | Frontend WebSocket URL |

## Tests

```bash
cd backend
pytest tests

cd ../frontend
npm run build
```

GitHub Actions runs both checks on push and pull request:

- Backend: install dependencies and run `pytest tests`
- Frontend: install packages with `npm ci` and run `npm run build`

## Demo Checklist

Use this checklist before sharing the project with recruiters or faculty:

1. Redeploy the latest GitHub commit.
2. Open the live demo and hard refresh the browser.
3. Click Start and wait for the first training frames.
4. Show trainer status, route progress, reward trend, speed, epsilon, loss, and
   experiment insights.
5. Open `/docs` to show FastAPI endpoints.
6. Show `benchmark.py` or `evaluate.py` output for measured ML performance.
7. Keep a short screen recording or GIF in the README when possible.

## Resume Metrics To Collect

Replace the placeholders below only after running evaluation:

- Evaluated DQN policy over `N` fixed-seed episodes.
- Achieved `X` average reward compared with `Y` random-baseline reward.
- Reduced collision rate from `A%` to `B%`.
- Reached `C%` destination success rate.
- Served live telemetry through FastAPI with dashboard updates every `T` seconds.
- Containerized and deployed the full-stack application as a single cloud
  service for demo access.

## Research Roadmap

1. Move training to a dedicated worker with Redis Pub/Sub.
2. Replace SQLite with PostgreSQL and add Alembic migrations.
3. Add MLflow or Weights & Biases experiment tracking.
4. Implement prioritized replay and n-step returns.
5. Benchmark Random, DQN, Double DQN, PPO, and SAC on fixed seeds.
6. Add scenario editing, collision heatmaps, model comparison, and saliency maps.
7. Add multi-agent traffic and domain-randomized weather scenarios.

## API

- `GET /health`
- `POST /train/start`
- `POST /train/pause`
- `POST /train/resume`
- `POST /train/reset`
- `GET /train/status`
- `GET /episodes`
- `GET /experiments`
- `GET /experiments/{experiment_id}/metrics`
- `GET /checkpoints`
- `GET /frames/latest`
- `POST /publish`
- `WS /ws`
