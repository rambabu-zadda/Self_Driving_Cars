import numpy as np

from env_highway import HighwayEnv


def test_vector_observation_is_normalized():
    env = HighwayEnv(seed=7)
    observation = env.reset(seed=7)

    assert observation.shape == (16,)
    assert observation.dtype == np.float32
    assert np.all(observation >= -1.0)
    assert np.all(observation <= 1.0)


def test_offroad_terminates_episode():
    env = HighwayEnv(seed=7)
    env.reset(seed=7)

    done = False
    info = {}
    while not done:
        _, _, done, info = env.step(0)

    assert info["offroad"] is True
    assert info["reward_breakdown"]["offroad"] < 0


def test_destination_terminates_episode():
    env = HighwayEnv(destination_distance=5.0, seed=7)
    env.reset(seed=7)

    _, _, done, info = env.step(1)

    assert done is True
    assert info["destination_reached"] is True
    assert info["reward_breakdown"]["destination"] > 0
