# backend/env_sim.py
import math
import numpy as np
from PIL import Image, ImageDraw


class UpgradedCarEnv:
    """
    FULL REAL-TIME MOVING CAR ENVIRONMENT
    - Thick road
    - Dashed lane line
    - Smooth driving physics
    - Car triangle drawn correctly
    - Real motion visible in each frame
    """

    def __init__(self, render_size=(640, 480)):
        self.W, self.H = render_size

        # TRACK GEOMETRY
        self.track = self._create_track()
        self.road_width = 60

        # CAR PARAMS
        self.car_length = 14
        self.car_width = 9
        self.max_speed = 4.5
        self.max_steer = 0.22
        self.friction = 0.96

        self.reset()

    # -------------------------------------------------------
    # Track: smooth looping curve
    # -------------------------------------------------------
    def _create_track(self):
        cx, cy = self.W // 2, self.H // 2
        pts = []
        for t in np.linspace(0, 2 * math.pi, 240):
            r = 180 + 40 * math.sin(3 * t)
            x = cx + r * math.cos(t)
            y = cy + r * math.sin(t)
            pts.append((x, y))
        return pts

    # -------------------------------------------------------
    # Reset
    # -------------------------------------------------------
    def reset(self):
        x0, y0 = self.track[0]
        self.x = x0
        self.y = y0
        self.angle = 0.0
        self.v = 1.2
        self.steps = 0
        self.done = False
        return self._obs_image()

    # -------------------------------------------------------
    # Step
    # -------------------------------------------------------
    def step(self, action):
        """
        ACTIONS:
        0 = steer left
        1 = straight
        2 = steer right
        3 = accelerate
        4 = brake
        """

        # Steering
        if action == 0:
            self.angle -= self.max_steer
        elif action == 2:
            self.angle += self.max_steer

        # Acceleration
        if action == 3:
            self.v += 0.12
        elif action == 4:
            self.v -= 0.2

        # Friction
        self.v *= self.friction
        self.v = max(min(self.v, self.max_speed), 0.2)

        # Move car
        dx = math.cos(self.angle) * self.v
        dy = math.sin(self.angle) * self.v
        self.x += dx
        self.y += dy

        self.steps += 1

        crashed = self._check_offroad()
        reward = -5.0 if crashed else 0.1

        if crashed or self.steps > 1600:
            self.done = True

        return self._obs_image(), reward, self.done, {"crash": crashed}

    # -------------------------------------------------------
    # Crash detection — distance from centerline
    # -------------------------------------------------------
    def _check_offroad(self):
        cx, cy = self._closest_centerline()
        dist = math.dist((self.x, self.y), (cx, cy))
        return dist > (self.road_width / 1.35)

    def _closest_centerline(self):
        track = np.array(self.track)
        dists = np.hypot(track[:, 0] - self.x, track[:, 1] - self.y)
        idx = np.argmin(dists)
        return track[idx]

    # -------------------------------------------------------
    # OBSERVATION for RL (84x84 grayscale)
    # -------------------------------------------------------
    def _obs_image(self):
        img = self._render_full()
        img_small = img.resize((84, 84))
        img_gray = img_small.convert("L")
        arr = np.array(img_gray)
        return arr.reshape(84, 84, 1).astype(np.uint8)

    # -------------------------------------------------------
    # RENDERING — this shows the actual environment UI frame
    # -------------------------------------------------------
    def _render_full(self):
        img = Image.new("RGB", (self.W, self.H), (0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw road surface
        for x, y in self.track:
            draw.ellipse(
                (x - self.road_width, y - self.road_width,
                 x + self.road_width, y + self.road_width),
                fill=(20, 20, 20),
                outline=None
            )

        # Lane center dashed line
        for i, (x, y) in enumerate(self.track):
            if i % 6 == 0:
                draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(60, 180, 255))

        # Car
        self._draw_car(draw)

        return img

    # -------------------------------------------------------
    # Draw triangular car
    # -------------------------------------------------------
    def _draw_car(self, draw):
        L = self.car_length
        W = self.car_width

        # Tip of the car
        x1 = self.x + math.cos(self.angle) * L
        y1 = self.y + math.sin(self.angle) * L

        # Left rear
        x2 = self.x + math.cos(self.angle + 2.4) * W
        y2 = self.y + math.sin(self.angle + 2.4) * W

        # Right rear
        x3 = self.x + math.cos(self.angle - 2.4) * W
        y3 = self.y + math.sin(self.angle - 2.4) * W

        draw.polygon([(x1, y1), (x2, y2), (x3, y3)], fill=(255, 40, 40))
