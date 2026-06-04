"""Optional experiment tracking integrations."""

from __future__ import annotations

import os
from typing import Dict, Optional


TRACKER_MODE = os.getenv("EXPERIMENT_TRACKER", "none").lower()
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
MLFLOW_EXPERIMENT_NAME = os.getenv(
    "MLFLOW_EXPERIMENT_NAME",
    "Self-Driving Cars RL",
)


class NoOpExperimentTracker:
    enabled = False

    def start_run(self, experiment_id: str, run_name: str, params: Dict) -> None:
        pass

    def log_metrics(self, metrics: Dict[str, Optional[float]], step: int) -> None:
        pass

    def log_artifact(self, path: str) -> None:
        pass

    def end_run(self, status: str = "FINISHED") -> None:
        pass


class MLflowExperimentTracker(NoOpExperimentTracker):
    enabled = True

    def __init__(
        self,
        tracking_uri: str = MLFLOW_TRACKING_URI,
        experiment_name: str = MLFLOW_EXPERIMENT_NAME,
    ):
        import mlflow

        self.mlflow = mlflow
        self.mlflow.set_tracking_uri(tracking_uri)
        self.mlflow.set_experiment(experiment_name)
        self.active = False

    def start_run(self, experiment_id: str, run_name: str, params: Dict) -> None:
        self.mlflow.start_run(run_name=run_name)
        self.active = True
        self.mlflow.set_tag("experiment_id", experiment_id)
        self.mlflow.set_tag("project", "self-driving-cars-rl")
        flat_params = _flatten_params(params)
        if flat_params:
            self.mlflow.log_params(flat_params)

    def log_metrics(self, metrics: Dict[str, Optional[float]], step: int) -> None:
        if not self.active:
            return
        clean = {
            key: float(value)
            for key, value in metrics.items()
            if isinstance(value, (int, float)) and value is not None
        }
        if clean:
            self.mlflow.log_metrics(clean, step=step)

    def log_artifact(self, path: str) -> None:
        if self.active and path and os.path.exists(path):
            self.mlflow.log_artifact(path, artifact_path="checkpoints")

    def end_run(self, status: str = "FINISHED") -> None:
        if not self.active:
            return
        self.mlflow.end_run(status=status)
        self.active = False


def create_experiment_tracker():
    if TRACKER_MODE == "mlflow":
        return MLflowExperimentTracker()
    return NoOpExperimentTracker()


def _flatten_params(params: Dict, prefix: str = "") -> Dict[str, str]:
    flattened = {}
    for key, value in params.items():
        name = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            flattened.update(_flatten_params(value, name))
        else:
            flattened[name] = str(value)
    return flattened
