# backend/models.py
from sqlalchemy import Column, Integer, Float, DateTime, Index, LargeBinary, String, Text
from sqlalchemy import func
from db import Base


class Experiment(Base):
    __tablename__ = "experiments"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    algorithm = Column(String, index=True)
    status = Column(String, index=True)
    hyperparameters_json = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)


class Episode(Base):
    __tablename__ = "episodes"
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(String, index=True, nullable=True)
    episode = Column(Integer, index=True)
    reward = Column(Float)
    crashes = Column(Integer)
    duration = Column(Integer)
    success = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_episodes_experiment_episode", "experiment_id", "episode"),
    )


class Metric(Base):
    __tablename__ = "metrics"
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(String, index=True)
    episode = Column(Integer, index=True)
    step = Column(Integer, index=True)
    reward = Column(Float)
    loss = Column(Float, nullable=True)
    epsilon = Column(Float, nullable=True)
    q_value = Column(Float, nullable=True)
    replay_size = Column(Integer, nullable=True)
    speed = Column(Float, nullable=True)
    progress = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_metrics_experiment_episode_step", "experiment_id", "episode", "step"),
        Index("ix_metrics_experiment_created_at", "experiment_id", "created_at"),
    )


class Checkpoint(Base):
    __tablename__ = "checkpoints"
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(String, index=True)
    episode = Column(Integer, index=True)
    path = Column(String)
    reward = Column(Float, nullable=True)
    epsilon = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_checkpoints_experiment_episode", "experiment_id", "episode"),
    )


class Frame(Base):
    __tablename__ = "frames"
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(String, index=True, nullable=True)
    episode = Column(Integer, index=True)
    step = Column(Integer)
    png = Column(LargeBinary)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_frames_experiment_created_at", "experiment_id", "created_at"),
    )
