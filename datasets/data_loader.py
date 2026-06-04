import os
import json

# Defer importing matplotlib until it's needed to avoid static-analysis/import errors
# in environments where matplotlib is not installed.
def _get_matplotlib_pyplot():
    try:
        import matplotlib.pyplot as plt
        return plt
    except Exception:
        return None

class DataLoader:
    def __init__(self, logs_dir="datasets/episode_logs"):
        self.logs_dir = logs_dir

    def list_episodes(self):
        """Return a sorted list of episode file paths (JSON) in the logs directory."""
        if not os.path.isdir(self.logs_dir):
            return []
        files = [
            os.path.join(self.logs_dir, f)
            for f in os.listdir(self.logs_dir)
            if os.path.isfile(os.path.join(self.logs_dir, f)) and f.lower().endswith(".json")
        ]
        files.sort()
        return files

    def load_episode(self, filename):
        """Load and return the JSON content of a single episode file, or [] on error."""
        try:
            with open(filename, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return []

    def plot_rewards(self, filename):
        plt = _get_matplotlib_pyplot()
        if plt is None:
            raise ImportError(
                "matplotlib is not available; install it with 'pip install matplotlib' to use plot_rewards."
            )
        steps = self.load_episode(filename)
        rewards = [step.get("reward", 0) for step in steps]
        plt.plot(rewards)
        plt.title(f"Rewards - {os.path.basename(filename)}")
        plt.xlabel("Step")
        plt.ylabel("Reward")
        plt.show()

    def summary(self):
        files = self.list_episodes()
        print(f"Found {len(files)} episodes:")
        for f in files:
            data = self.load_episode(f)
            total_reward = sum((step.get("reward", 0) for step in data))
            print(f"  {f}: {len(data)} steps, total reward = {total_reward:.2f}")
