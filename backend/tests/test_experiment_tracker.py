from experiment_tracker import NoOpExperimentTracker, _flatten_params


def test_noop_tracker_accepts_lifecycle_calls(tmp_path):
    tracker = NoOpExperimentTracker()
    checkpoint = tmp_path / "checkpoint.pt"
    checkpoint.write_text("fake", encoding="utf-8")

    tracker.start_run("exp-test", "test run", {"learning_rate": 0.001})
    tracker.log_metrics({"reward": 1.0, "loss": None}, step=1)
    tracker.log_artifact(str(checkpoint))
    tracker.end_run("FINISHED")

    assert tracker.enabled is False


def test_flatten_params_handles_nested_values():
    assert _flatten_params({"agent": {"gamma": 0.99}, "device": "cpu"}) == {
        "agent.gamma": "0.99",
        "device": "cpu",
    }
