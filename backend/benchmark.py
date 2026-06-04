"""Benchmark policies on fixed highway scenarios.

Use this script before making resume or report claims. It compares a random
baseline with any supplied DQN checkpoints and prints measured metrics only.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from statistics import mean
from typing import Callable, Dict, List

from agent import DQNAgent
from env_highway import HighwayEnv


Policy = Callable[[object, HighwayEnv], int]


def random_policy(_observation, env: HighwayEnv) -> int:
    return random.randrange(len(env.ACTIONS))


def dqn_policy(checkpoint_path: str) -> Policy:
    env = HighwayEnv(seed=0)
    agent = DQNAgent(env.observation_shape, n_actions=len(env.ACTIONS))
    agent.load(checkpoint_path, load_optimizer=False)

    def policy(observation, _env: HighwayEnv) -> int:
        return agent.act(observation, evaluation=True)

    return policy


def run_policy(name: str, policy: Policy, episodes: int, seed: int) -> Dict:
    results: List[Dict] = []
    actions = Counter()

    for episode in range(episodes):
        env = HighwayEnv(seed=seed + episode)
        observation = env.reset(seed=seed + episode)
        done = False
        total_reward = 0.0
        final_info = {}

        while not done:
            action = policy(observation, env)
            actions[env.ACTIONS[action]] += 1
            observation, reward, done, final_info = env.step(action)
            total_reward += reward

        results.append(
            {
                "episode": episode + 1,
                "reward": total_reward,
                "collision": bool(final_info.get("crash")),
                "success": bool(final_info.get("destination_reached")),
                "offroad": bool(final_info.get("offroad")),
                "steps": env.steps,
            }
        )

    return {
        "policy": name,
        "episodes": episodes,
        "average_reward": mean(row["reward"] for row in results),
        "collision_rate": mean(row["collision"] for row in results),
        "success_rate": mean(row["success"] for row in results),
        "offroad_rate": mean(row["offroad"] for row in results),
        "average_steps": mean(row["steps"] for row in results),
        "action_distribution": dict(actions),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--checkpoint", action="append", default=[])
    args = parser.parse_args()

    reports = [run_policy("random", random_policy, args.episodes, args.seed)]
    for checkpoint in args.checkpoint:
        reports.append(
            run_policy(f"dqn:{checkpoint}", dqn_policy(checkpoint), args.episodes, args.seed)
        )

    print(json.dumps({"seed": args.seed, "reports": reports}, indent=2))


if __name__ == "__main__":
    main()
