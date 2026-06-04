import numpy as np

from agent import DQNAgent, DQNConfig, ReplayBuffer


def test_replay_buffer_tracks_capacity():
    buffer = ReplayBuffer(3)
    for action in range(5):
        state = np.full((4,), action, dtype=np.float32)
        buffer.push(state, action, 1.0, state + 1, False)

    assert len(buffer) == 3


def test_agent_updates_and_checkpoints(tmp_path):
    config = DQNConfig(
        buffer_size=100,
        min_replay_size=4,
        hidden_sizes=(32,),
        target_sync_interval=1,
        device="cpu",
    )
    agent = DQNAgent((4,), n_actions=2, config=config)
    for _ in range(8):
        state = np.random.rand(4).astype(np.float32)
        agent.push(state, 0, 1.0, state, False)

    metrics = agent.update(batch_size=4)
    assert metrics is not None
    assert metrics["loss"] >= 0

    path = tmp_path / "agent.pt"
    agent.save(str(path), metadata={"episode": 3})
    restored = DQNAgent((4,), n_actions=2, config=config)
    metadata = restored.load(str(path))
    assert metadata["episode"] == 3
