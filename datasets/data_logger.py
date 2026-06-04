import os
import json
from datetime import datetime
import numpy as np
from PIL import Image

class DataLogger:
    def __init__(self, base_dir="datasets"):
        self.base_dir = base_dir
        self.logs_dir = os.path.join(base_dir, "episode_logs")
        self.frames_dir = os.path.join(base_dir, "frames")
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.frames_dir, exist_ok=True)
        self.episode_data = []
        self.episode_id = None

    def start_episode(self, episode_number):
        self.episode_data = []
        self.episode_id = f"episode_{episode_number:03d}"
        print(f"[DataLogger] Started logging {self.episode_id}")

    def record_step(self, step_num, state, action, reward, done, frame=None):
        step_info = {
            "step": step_num,
            "state": state.tolist() if hasattr(state, "tolist") else state,
            "action": int(action),
            "reward": float(reward),
            "done": bool(done)
        }
        self.episode_data.append(step_info)
        if frame is not None:
            frame_img = Image.fromarray(frame)
            frame_path = os.path.join(self.frames_dir, f"{self.episode_id}_frame{step_num:04d}.png")
            frame_img.save(frame_path)

    def end_episode(self):
        if not self.episode_data:
            return
        log_path = os.path.join(self.logs_dir, f"{self.episode_id}.json")
        with open(log_path, "w") as f:
            json.dump({
                "episode": self.episode_id,
                "timestamp": datetime.now().isoformat(),
                "steps": self.episode_data
            }, f, indent=2)
        print(f"[DataLogger] Saved {log_path}")
        self.episode_data = []
        self.episode_id = None
