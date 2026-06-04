"""Standalone trainer worker.

Run this process separately from FastAPI when `TRAINER_CONTROL_MODE=redis`.
It listens for trainer control commands on Redis and publishes telemetry back to
the FastAPI `/publish` endpoint.
"""

from __future__ import annotations

import os
import signal

from event_bus import HttpTelemetryPublisher, RedisCommandListener
from trainer_manager import TrainerManager


def main() -> None:
    listener = RedisCommandListener()
    trainer = TrainerManager(event_publisher=HttpTelemetryPublisher())
    stopping = False

    def request_stop(_signum, _frame):
        nonlocal stopping
        stopping = True
        trainer.reset()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    print(
        "Trainer worker listening on",
        os.getenv("TRAINER_COMMAND_CHANNEL", "trainer.commands"),
    )
    for message in listener.listen():
        if stopping:
            break
        command = message.get("command")
        if command == "start":
            trainer.start()
        elif command == "pause":
            trainer.pause()
        elif command == "resume":
            trainer.resume()
        elif command == "reset":
            trainer.reset()
        elif command == "stop_worker":
            trainer.reset()
            break
        else:
            print("Unknown trainer command:", message)


if __name__ == "__main__":
    main()
