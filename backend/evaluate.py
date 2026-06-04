"""Evaluate a trained checkpoint without exploration."""

from __future__ import annotations

import argparse
import json
from statistics import mean

from agent import DQNAgent
from env_highway import HighwayEnv


def evaluate(checkpoint: str, episodes: int, seed: int):
    env = HighwayEnv(seed=seed)
    agent = DQNAgent(env.observation_shape, n_actions=len(env.ACTIONS))
    metadata = agent.load(checkpoint, load_optimizer=False)
    results = []

    for episode in range(episodes):
        observation = env.reset(seed=seed + episode)
        done = False
        total_reward = 0.0
        final_info = {}
        while not done:
            action = agent.act(observation, evaluation=True)
            observation, reward, done, final_info = env.step(action)
            total_reward += reward
        results.append(
            {
                "episode": episode + 1,
                "reward": total_reward,
                "collision": bool(final_info.get("crash")),
                "success": bool(final_info.get("destination_reached")),
                "steps": env.steps,
            }
        )

    summary = {
        "checkpoint": checkpoint,
        "checkpoint_metadata": metadata,
        "episodes": episodes,
        "average_reward": mean(row["reward"] for row in results),
        "collision_rate": mean(row["collision"] for row in results),
        "success_rate": mean(row["success"] for row in results),
        "average_steps": mean(row["steps"] for row in results),
        "results": results,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint")
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1000)
    args = parser.parse_args()
    evaluate(args.checkpoint, args.episodes, args.seed)
