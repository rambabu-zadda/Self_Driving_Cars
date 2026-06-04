"""Vector-state highway environment with a renderable research dashboard view."""

from __future__ import annotations

import random
from typing import Dict, List, Optional

import numpy as np
from PIL import Image, ImageDraw


class HighwayEnv:
    ACTIONS = ("left", "maintain", "right", "accelerate", "brake")

    def __init__(
        self,
        render_size=(640, 480),
        num_lanes: int = 3,
        max_steps: int = 1_500,
        destination_distance: float = 8_000.0,
        traffic_count: int = 8,
        seed: Optional[int] = None,
    ):
        self.W, self.H = render_size
        self.num_lanes = num_lanes
        self.lane_width = 80
        self.road_width = self.num_lanes * self.lane_width
        self.road_x = (self.W - self.road_width) // 2
        self.lane_centers = [
            self.road_x + self.lane_width * 0.5 + i * self.lane_width
            for i in range(self.num_lanes)
        ]
        self.max_steps = max_steps
        self.destination_distance = destination_distance
        self.traffic_count = traffic_count
        self.rng = random.Random(seed)

        self.min_speed = 2.0
        self.max_speed = 12.0
        self.accel = 0.3
        self.brake_force = 0.5
        self.lateral_speed = 5.0
        self.safe_following_distance = 90.0
        self.collision_x = 28.0
        self.collision_y = 48.0
        self.traffic: List[Dict[str, float]] = []
        self.reset()

    @property
    def observation_shape(self):
        return self._obs().shape

    def reset(self, seed: Optional[int] = None):
        if seed is not None:
            self.rng.seed(seed)
        self.x = float(self.lane_centers[self.num_lanes // 2])
        self.speed = 6.0
        self.progress = 0.0
        self.steps = 0
        self.done = False
        self.traffic = []
        for _ in range(self.traffic_count):
            self._spawn_traffic()
        return self._obs()

    def step(self, action: int):
        if self.done:
            raise RuntimeError("step() called after episode termination; call reset()")
        if action < 0 or action >= len(self.ACTIONS):
            raise ValueError(f"invalid action {action}")

        previous_lane = self._nearest_lane_index()
        if action == 0:
            self.x -= self.lateral_speed
        elif action == 2:
            self.x += self.lateral_speed
        elif action == 3:
            self.speed += self.accel
        elif action == 4:
            self.speed -= self.brake_force

        self.speed = float(np.clip(self.speed, self.min_speed, self.max_speed))
        self.progress += self.speed
        self.steps += 1

        for vehicle in self.traffic:
            vehicle["distance"] += vehicle["speed"] - self.speed
        self._refresh_traffic()

        collision = self._check_collision()
        offroad = self._is_offroad()
        destination_reached = self.progress >= self.destination_distance
        timeout = self.steps >= self.max_steps
        unsafe_distance = self._nearest_ahead_distance() < self.safe_following_distance
        lane_changed = self._nearest_lane_index() != previous_lane

        rewards = {
            "progress": 0.04 * self.speed,
            "lane_keeping": 0.25 * self._lane_center_score(),
            "safe_distance": -0.35 if unsafe_distance else 0.05,
            "lane_change": -0.08 if lane_changed else 0.0,
            "collision": -20.0 if collision else 0.0,
            "offroad": -12.0 if offroad else 0.0,
            "destination": 25.0 if destination_reached else 0.0,
        }
        reward = float(sum(rewards.values()))
        self.done = collision or offroad or destination_reached or timeout

        info = {
            "crash": collision,
            "offroad": offroad,
            "destination_reached": destination_reached,
            "timeout": timeout,
            "unsafe_distance": unsafe_distance,
            "reward_breakdown": rewards,
            "progress": self.progress,
            "lane": self._nearest_lane_index(),
            "action": self.ACTIONS[action],
        }
        return self._obs(), reward, self.done, info

    def _spawn_traffic(self) -> None:
        lane = self.rng.randrange(self.num_lanes)
        distance = self.rng.uniform(120.0, 900.0)
        if self.rng.random() < 0.2:
            distance *= -1
        speed = self.rng.uniform(3.0, 10.0)
        self.traffic.append({"lane": float(lane), "distance": distance, "speed": speed})

    def _refresh_traffic(self) -> None:
        self.traffic = [
            vehicle
            for vehicle in self.traffic
            if -250.0 < vehicle["distance"] < 1_000.0
        ]
        while len(self.traffic) < self.traffic_count:
            self._spawn_traffic()

    def _nearest_lane_index(self) -> int:
        return int(np.argmin([abs(self.x - center) for center in self.lane_centers]))

    def _lane_center_score(self) -> float:
        lane = self._nearest_lane_index()
        offset = abs(self.x - self.lane_centers[lane])
        return float(np.clip(1.0 - offset / (self.lane_width / 2), -1.0, 1.0))

    def _is_offroad(self) -> bool:
        return self.x < self.road_x + 12 or self.x > self.road_x + self.road_width - 12

    def _check_collision(self) -> bool:
        for vehicle in self.traffic:
            lane_x = self.lane_centers[int(vehicle["lane"])]
            if abs(self.x - lane_x) < self.collision_x and abs(vehicle["distance"]) < self.collision_y:
                return True
        return False

    def _nearest_ahead_distance(self) -> float:
        lane = self._nearest_lane_index()
        ahead = [
            vehicle["distance"]
            for vehicle in self.traffic
            if int(vehicle["lane"]) == lane and vehicle["distance"] >= 0
        ]
        return min(ahead, default=1_000.0)

    def _obs(self) -> np.ndarray:
        lane = self._nearest_lane_index()
        lane_offset = (self.x - self.lane_centers[lane]) / (self.lane_width / 2)
        state = [
            lane / max(1, self.num_lanes - 1),
            float(np.clip(lane_offset, -1.0, 1.0)),
            self.speed / self.max_speed,
            min(1.0, self.progress / self.destination_distance),
        ]

        for lane_index in range(self.num_lanes):
            vehicles = [v for v in self.traffic if int(v["lane"]) == lane_index]
            ahead = [v for v in vehicles if v["distance"] >= 0]
            behind = [v for v in vehicles if v["distance"] < 0]
            nearest_ahead = min(ahead, key=lambda v: v["distance"], default=None)
            nearest_behind = max(behind, key=lambda v: v["distance"], default=None)
            state.extend(self._vehicle_features(nearest_ahead, ahead=True))
            state.extend(self._vehicle_features(nearest_behind, ahead=False))

        return np.asarray(state, dtype=np.float32)

    def _vehicle_features(self, vehicle, ahead: bool):
        if vehicle is None:
            return [1.0, 0.0]
        distance = abs(vehicle["distance"])
        signed_distance = min(distance / 500.0, 1.0)
        if not ahead:
            signed_distance *= -1.0
        relative_speed = (vehicle["speed"] - self.speed) / self.max_speed
        return [signed_distance, float(np.clip(relative_speed, -1.0, 1.0))]

    def _render_full(self) -> Image.Image:
        img = Image.new("RGB", (self.W, self.H), (5, 5, 8))
        draw = ImageDraw.Draw(img)
        draw.rectangle(
            [self.road_x, 0, self.road_x + self.road_width, self.H],
            fill=(25, 25, 30),
        )
        for i in range(self.num_lanes + 1):
            x = self.road_x + i * self.lane_width
            color = (255, 220, 50) if i in (0, self.num_lanes) else (180, 180, 190)
            for y in range(0, self.H, 32):
                draw.line([(x, y), (x, y + 16)], fill=color, width=3)

        ego_y = self.H - 100
        for vehicle in self.traffic:
            y = ego_y - vehicle["distance"] * 0.45
            if -60 <= y <= self.H + 60:
                x = self.lane_centers[int(vehicle["lane"])]
                draw.rounded_rectangle(
                    [x - 15, y - 28, x + 15, y + 28],
                    radius=5,
                    fill=(70, 170, 255),
                )
        self._draw_ego_car(draw, ego_y)
        return img

    def _draw_ego_car(self, draw: ImageDraw.ImageDraw, y: float) -> None:
        x = int(self.x)
        y = int(y)
        draw.rounded_rectangle(
            [x - 17, y - 29, x + 17, y + 29],
            radius=8,
            fill=(20, 20, 22),
            outline=(255, 255, 255),
            width=2,
        )
        draw.rectangle([x - 11, y - 20, x + 11, y - 5], fill=(60, 130, 200))
        draw.rectangle([x - 11, y + 2, x + 11, y + 16], fill=(50, 110, 180))
