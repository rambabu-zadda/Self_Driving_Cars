# Render Single-Service Deployment

Use this when you want one full-stack web app instead of separate backend,
frontend, worker, Redis, and PostgreSQL services.

This mode packages:

- React dashboard
- FastAPI API
- WebSocket endpoint
- local in-process trainer
- SQLite demo database

into one Docker web service.

## Create One Render Web Service

1. Open Render.
2. Click **New +**.
3. Select **Web Service**.
4. Connect this repository:

```text
rambabu-zadda/Self_Driving_Cars
```

5. Select branch:

```text
main
```

6. Use these settings:

```text
Runtime: Docker
Root Directory: leave empty
Dockerfile Path: Dockerfile.single
```

7. Add environment variables:

```text
TRAINER_CONTROL_MODE=local
DATABASE_URL=sqlite:///./data.db
AUTO_CREATE_TABLES=true
EXPERIMENT_TRACKER=none
CHECKPOINT_DIR=/app/checkpoints
FRAME_STORE_STEP_INTERVAL=50
MAX_STORED_FRAMES=500
```

8. Deploy.

## Verify

Open your Render URL:

```text
https://your-service.onrender.com
```

The React dashboard should load from the same FastAPI service.

Check backend health:

```text
https://your-service.onrender.com/health
```

Expected:

```json
{"status":"ok"}
```

Click **Start Training** in the dashboard.

Expected:

- WebSocket connects to the same domain.
- Training starts in `local` mode inside the FastAPI process.
- Simulation frames and metrics update.
- `/experiments` shows runs.

## Important Limitations

This is a demo deployment, not the full production architecture.

- SQLite data may be lost on redeploy/restart unless persistent disk is added.
- Training runs inside the web process.
- No Redis worker queue.
- No PostgreSQL.
- No MLflow.

For production/research deployment, use the multi-service Railway or Render
guides instead.
