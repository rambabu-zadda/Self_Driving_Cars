"""Deep Q-learning agent used by the autonomous-driving trainer."""

from __future__ import annotations

import os
import random
from collections import deque
from dataclasses import asdict, dataclass
from typing import Deque, Dict, Iterable, Optional, Tuple

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F


@dataclass
class DQNConfig:
    gamma: float = 0.99
    learning_rate: float = 1e-4
    buffer_size: int = 100_000
    min_replay_size: int = 1_000
    target_sync_interval: int = 1_000
    hidden_sizes: Tuple[int, ...] = (256, 256)
    dueling: bool = True
    double_dqn: bool = True
    gradient_clip: float = 10.0
    device: str = "auto"


class ReplayBuffer:
    def __init__(self, capacity: int):
        self.capacity = int(capacity)
        self.memory: Deque[Tuple[np.ndarray, int, float, np.ndarray, bool]] = deque(
            maxlen=self.capacity
        )

    def __len__(self) -> int:
        return len(self.memory)

    def push(self, state, action, reward, next_state, done) -> None:
        self.memory.append(
            (
                np.asarray(state, dtype=np.float32),
                int(action),
                float(reward),
                np.asarray(next_state, dtype=np.float32),
                bool(done),
            )
        )

    def sample(self, batch_size: int, device: torch.device):
        batch = random.sample(self.memory, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            torch.as_tensor(np.stack(states), dtype=torch.float32, device=device),
            torch.as_tensor(actions, dtype=torch.long, device=device).unsqueeze(1),
            torch.as_tensor(rewards, dtype=torch.float32, device=device).unsqueeze(1),
            torch.as_tensor(np.stack(next_states), dtype=torch.float32, device=device),
            torch.as_tensor(dones, dtype=torch.float32, device=device).unsqueeze(1),
        )


class QNetwork(nn.Module):
    def __init__(
        self,
        obs_shape: Iterable[int],
        n_actions: int,
        hidden_sizes: Tuple[int, ...],
        dueling: bool,
    ):
        super().__init__()
        self.obs_shape = tuple(obs_shape)
        self.image_input = len(self.obs_shape) == 3
        self.dueling = dueling

        if self.image_input:
            channels = self.obs_shape[-1]
            self.features = nn.Sequential(
                nn.Conv2d(channels, 32, kernel_size=8, stride=4),
                nn.ReLU(),
                nn.Conv2d(32, 64, kernel_size=4, stride=2),
                nn.ReLU(),
                nn.Conv2d(64, 64, kernel_size=3, stride=1),
                nn.ReLU(),
                nn.Flatten(),
            )
            with torch.no_grad():
                sample = torch.zeros(1, channels, self.obs_shape[0], self.obs_shape[1])
                feature_size = self.features(sample).shape[1]
        else:
            self.features = nn.Identity()
            feature_size = int(np.prod(self.obs_shape))

        layers = []
        input_size = feature_size
        for hidden_size in hidden_sizes:
            layers.extend((nn.Linear(input_size, hidden_size), nn.ReLU()))
            input_size = hidden_size
        self.trunk = nn.Sequential(*layers)

        if dueling:
            self.value_head = nn.Linear(input_size, 1)
            self.advantage_head = nn.Linear(input_size, n_actions)
        else:
            self.q_head = nn.Linear(input_size, n_actions)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.image_input:
            x = x.permute(0, 3, 1, 2) / 255.0
        else:
            x = x.flatten(start_dim=1)
        x = self.trunk(self.features(x))
        if not self.dueling:
            return self.q_head(x)
        value = self.value_head(x)
        advantage = self.advantage_head(x)
        return value + advantage - advantage.mean(dim=1, keepdim=True)


class DQNAgent:
    def __init__(
        self,
        obs_shape,
        n_actions: int = 5,
        config: Optional[DQNConfig] = None,
    ):
        self.obs_shape = tuple(obs_shape)
        self.n_actions = int(n_actions)
        self.config = config or DQNConfig()
        self.device = self._resolve_device(self.config.device)

        self.online_net = QNetwork(
            self.obs_shape,
            self.n_actions,
            self.config.hidden_sizes,
            self.config.dueling,
        ).to(self.device)
        self.target_net = QNetwork(
            self.obs_shape,
            self.n_actions,
            self.config.hidden_sizes,
            self.config.dueling,
        ).to(self.device)
        self.target_net.load_state_dict(self.online_net.state_dict())
        self.target_net.eval()

        self.optimizer = torch.optim.Adam(
            self.online_net.parameters(), lr=self.config.learning_rate
        )
        self.replay_buffer = ReplayBuffer(self.config.buffer_size)
        self.update_steps = 0

    @staticmethod
    def _resolve_device(name: str) -> torch.device:
        if name == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return torch.device(name)

    def act(self, obs, eps: float = 0.0, evaluation: bool = False) -> int:
        if not evaluation and random.random() < eps:
            return random.randrange(self.n_actions)
        state = torch.as_tensor(
            np.asarray(obs, dtype=np.float32), dtype=torch.float32, device=self.device
        ).unsqueeze(0)
        with torch.no_grad():
            return int(self.online_net(state).argmax(dim=1).item())

    def action_values(self, obs) -> np.ndarray:
        state = torch.as_tensor(
            np.asarray(obs, dtype=np.float32), dtype=torch.float32, device=self.device
        ).unsqueeze(0)
        with torch.no_grad():
            return self.online_net(state).squeeze(0).cpu().numpy()

    def push(self, *transition) -> None:
        self.replay_buffer.push(*transition)

    def update(self, batch_size: int = 64) -> Optional[Dict[str, float]]:
        if len(self.replay_buffer) < max(batch_size, self.config.min_replay_size):
            return None

        states, actions, rewards, next_states, dones = self.replay_buffer.sample(
            batch_size, self.device
        )
        q_values = self.online_net(states).gather(1, actions)

        with torch.no_grad():
            if self.config.double_dqn:
                next_actions = self.online_net(next_states).argmax(dim=1, keepdim=True)
                next_q_values = self.target_net(next_states).gather(1, next_actions)
            else:
                next_q_values = self.target_net(next_states).max(dim=1, keepdim=True).values
            targets = rewards + self.config.gamma * (1.0 - dones) * next_q_values

        loss = F.smooth_l1_loss(q_values, targets)
        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.online_net.parameters(), self.config.gradient_clip)
        self.optimizer.step()

        self.update_steps += 1
        if self.update_steps % self.config.target_sync_interval == 0:
            self.sync_target_network()

        return {
            "loss": float(loss.item()),
            "q_value": float(q_values.mean().item()),
            "replay_size": float(len(self.replay_buffer)),
        }

    def sync_target_network(self) -> None:
        self.target_net.load_state_dict(self.online_net.state_dict())

    def save(self, path: str, metadata: Optional[dict] = None) -> None:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        torch.save(
            {
                "obs_shape": self.obs_shape,
                "n_actions": self.n_actions,
                "config": asdict(self.config),
                "online_net": self.online_net.state_dict(),
                "target_net": self.target_net.state_dict(),
                "optimizer": self.optimizer.state_dict(),
                "update_steps": self.update_steps,
                "metadata": metadata or {},
            },
            path,
        )

    def load(self, path: str, load_optimizer: bool = True) -> dict:
        checkpoint = torch.load(path, map_location=self.device)
        self.online_net.load_state_dict(checkpoint["online_net"])
        self.target_net.load_state_dict(checkpoint.get("target_net", checkpoint["online_net"]))
        if load_optimizer and "optimizer" in checkpoint:
            self.optimizer.load_state_dict(checkpoint["optimizer"])
        self.update_steps = int(checkpoint.get("update_steps", 0))
        return checkpoint.get("metadata", {})
