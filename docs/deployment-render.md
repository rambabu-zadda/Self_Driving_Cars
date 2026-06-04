# Render Deployment Guide

Render is a good Railway alternative for this project. The repository includes
`render.yaml`, which creates:

- PostgreSQL database
- Redis-compatible Key Value instance
- FastAPI backend web service
- Trainer worker service
- React frontend web service

MLflow is intentionally not included in the Render blueprint to keep the service
count and cost lower. Use `EXPERIMENT_TRACKER=none` first.

## 1. Create Blueprint

1. Open Render.
2. Choose **New +**.
3. Choose **Blueprint**.
4. Connect GitHub repository:

```text
rambabu-zadda/Self_Driving_Cars
```

5. Select branch:

```text
main
```

6. Render will detect `render.yaml`.

## 2. Fill Frontend Build Variables

Render cannot know the backend public URL until the backend service exists, so
the frontend variables are marked `sync: false`.

After Render creates `self-driving-rl-backend`, copy its public URL. It will look
like:

```text
https://self-driving-rl-backend.onrender.com
```

Set these variables on `self-driving-rl-frontend`:

```text
REACT_APP_BACKEND=https://self-driving-rl-backend.onrender.com
REACT_APP_WS_URL=wss://self-driving-rl-backend.onrender.com/ws
```

Then redeploy the frontend.

## 3. Verify Backend

Open:

```text
https://self-driving-rl-backend.onrender.com/health
```

Expected:

```json
{"status":"ok"}
```

Then open:

```text
https://self-driving-rl-backend.onrender.com/docs
```

## 4. Verify Trainer

Open backend status:

```text
https://self-driving-rl-backend.onrender.com/train/status
```

Expected:

```json
{
  "control_mode": "redis"
}
```

Click **Start Training** in the frontend. Then check:

```text
https://self-driving-rl-backend.onrender.com/experiments
```

You should see experiment records after training starts.

## 5. Important Notes

- Render workers are not public web services.
- Backend and trainer communicate privately through Render service host/port and
  Redis.
- Frontend must use the backend public URL because browser requests happen from
  the user's machine.
- If the frontend was deployed before backend URL variables were set, redeploy
  the frontend after adding them.

## 6. Common Problems

### Frontend loads but WebSocket is disconnected

Check:

```text
REACT_APP_BACKEND=https://self-driving-rl-backend.onrender.com
REACT_APP_WS_URL=wss://self-driving-rl-backend.onrender.com/ws
```

Then redeploy the frontend.

### Trainer does not receive Start Training

Check:

- `TRAINER_CONTROL_MODE=redis` on backend.
- `REDIS_URL` exists on both backend and trainer.
- Trainer logs show `Trainer worker listening on trainer.commands`.

### Backend migration fails

Check:

- `DATABASE_URL` is present on backend.
- PostgreSQL is healthy.
- Backend logs include `alembic upgrade head`.
