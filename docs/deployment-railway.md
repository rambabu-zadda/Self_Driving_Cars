# Railway Deployment Guide

Railway is the recommended first cloud target for this project because the app
is a multi-service system: React frontend, FastAPI backend, trainer worker,
PostgreSQL, Redis, and optional MLflow.

Railway does not run `docker-compose.yml` directly. Create separate Railway
services that map to the Compose services.

## 1. Create Project

1. Open Railway.
2. Create a new empty project.
3. Add the GitHub repository:
   `rambabu-zadda/Self_Driving_Cars`.

## 2. Add Managed Databases

Add these database services from Railway:

- PostgreSQL
- Redis

Use Railway's generated connection variables instead of hardcoded local Compose
URLs.

## 3. Backend Service

Create a service from the GitHub repository.

Settings:

- Root directory: `backend`
- Dockerfile path: `Dockerfile`
- Public networking: enabled
- Health check path: `/health`

Variables:

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
TRAINER_CONTROL_MODE=redis
AUTO_CREATE_TABLES=false
CHECKPOINT_DIR=/app/checkpoints
FRAME_STORE_STEP_INTERVAL=50
MAX_STORED_FRAMES=1000
```

After deployment, copy the public backend URL. It will look like:

```text
https://your-backend.up.railway.app
```

## 4. Trainer Worker Service

Create another service from the same GitHub repository.

Settings:

- Root directory: `backend`
- Dockerfile path: `Dockerfile`
- Public networking: disabled
- Start command:

```bash
python trainer_worker.py
```

Variables:

```text
BACKEND_URL=https://your-backend.up.railway.app
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
CHECKPOINT_DIR=/app/checkpoints
CHECKPOINT_INTERVAL=25
EXPERIMENT_TRACKER=none
```

Set `EXPERIMENT_TRACKER=mlflow` only after the MLflow service is deployed.

## 5. Frontend Service

Create a service from the same GitHub repository.

Settings:

- Root directory: `frontend`
- Dockerfile path: `Dockerfile`
- Public networking: enabled

Build variables:

```text
REACT_APP_BACKEND=https://your-backend.up.railway.app
REACT_APP_WS_URL=wss://your-backend.up.railway.app/ws
```

The frontend Dockerfile builds a production React bundle and serves it using a
small Node static server on Railway's `$PORT`.

## 6. Optional MLflow Service

Create a third backend-derived service if you want MLflow.

Settings:

- Root directory: `backend`
- Dockerfile path: `Dockerfile.mlflow`
- Public networking: enabled or private, depending on whether you want to open
  MLflow in the browser.
- Start command:

```bash
mlflow server --host 0.0.0.0 --port $PORT --backend-store-uri $DATABASE_URL --default-artifact-root /mlflow/artifacts
```

Variables:

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

Then update the trainer worker:

```text
EXPERIMENT_TRACKER=mlflow
MLFLOW_TRACKING_URI=https://your-mlflow.up.railway.app
MLFLOW_EXPERIMENT_NAME=Self-Driving Cars RL
```

## 7. Verify

Open:

- Backend health: `https://your-backend.up.railway.app/health`
- Backend docs: `https://your-backend.up.railway.app/docs`
- Frontend: `https://your-frontend.up.railway.app`

Then click `Start Training` in the dashboard.

Expected behavior:

- Backend `/train/status` shows `control_mode: redis`
- Trainer worker logs show it received the `start` command
- Dashboard receives simulation frames over WebSocket
- `/experiments` shows the current run

## 8. Common Issues

### Frontend cannot connect to backend

Check that:

```text
REACT_APP_BACKEND=https://your-backend.up.railway.app
REACT_APP_WS_URL=wss://your-backend.up.railway.app/ws
```

These variables must be present during the frontend build.

### Trainer does not start

Check:

- Trainer worker is deployed and running.
- `REDIS_URL` points to Railway Redis.
- Backend `TRAINER_CONTROL_MODE=redis`.
- Backend and trainer use the same Redis service.

### Database migration failure

Check:

- `DATABASE_URL` is present on backend.
- PostgreSQL service is running.
- Backend logs show `alembic upgrade head`.

### MLflow is not logging

Check:

- Trainer has `EXPERIMENT_TRACKER=mlflow`.
- `MLFLOW_TRACKING_URI` points to the MLflow service.
- MLflow service can connect to PostgreSQL.
