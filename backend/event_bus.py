"""Trainer command and telemetry transport adapters."""

from __future__ import annotations

import json
import os
from typing import Dict, Iterator, Optional

import requests


BACKEND_INTERNAL_HOSTPORT = os.getenv("BACKEND_INTERNAL_HOSTPORT")
BACKEND_URL = os.getenv(
    "BACKEND_URL",
    f"http://{BACKEND_INTERNAL_HOSTPORT}" if BACKEND_INTERNAL_HOSTPORT else "http://127.0.0.1:8000",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
TRAINER_COMMAND_CHANNEL = os.getenv("TRAINER_COMMAND_CHANNEL", "trainer.commands")


class HttpTelemetryPublisher:
    def __init__(self, backend_url: str = BACKEND_URL):
        self.backend_url = backend_url.rstrip("/")

    def publish(self, payload: Dict) -> None:
        requests.post(f"{self.backend_url}/publish", json=payload, timeout=5)


class RedisCommandPublisher:
    def __init__(
        self,
        redis_url: str = REDIS_URL,
        channel: str = TRAINER_COMMAND_CHANNEL,
    ):
        self.redis_url = redis_url
        self.channel = channel
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import redis

            self._client = redis.Redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    def publish(self, command: str, payload: Optional[Dict] = None) -> int:
        message = {"command": command, "payload": payload or {}}
        return int(self.client.publish(self.channel, json.dumps(message)))


class RedisCommandListener:
    def __init__(
        self,
        redis_url: str = REDIS_URL,
        channel: str = TRAINER_COMMAND_CHANNEL,
    ):
        self.redis_url = redis_url
        self.channel = channel

    def listen(self) -> Iterator[Dict]:
        import redis

        client = redis.Redis.from_url(self.redis_url, decode_responses=True)
        pubsub = client.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(self.channel)
        for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            try:
                yield json.loads(message.get("data") or "{}")
            except json.JSONDecodeError:
                yield {"command": "invalid", "payload": {"raw": message.get("data")}}
