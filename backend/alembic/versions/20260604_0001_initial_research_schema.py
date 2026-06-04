"""initial research schema

Revision ID: 20260604_0001
Revises:
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "experiments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("algorithm", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("hyperparameters_json", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiments_algorithm", "experiments", ["algorithm"])
    op.create_index("ix_experiments_id", "experiments", ["id"])
    op.create_index("ix_experiments_name", "experiments", ["name"])
    op.create_index("ix_experiments_status", "experiments", ["status"])

    op.create_table(
        "episodes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.String(), nullable=True),
        sa.Column("episode", sa.Integer(), nullable=True),
        sa.Column("reward", sa.Float(), nullable=True),
        sa.Column("crashes", sa.Integer(), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("success", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_episodes_created_at", "episodes", ["created_at"])
    op.create_index("ix_episodes_episode", "episodes", ["episode"])
    op.create_index("ix_episodes_experiment_episode", "episodes", ["experiment_id", "episode"])
    op.create_index("ix_episodes_experiment_id", "episodes", ["experiment_id"])
    op.create_index("ix_episodes_id", "episodes", ["id"])

    op.create_table(
        "metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.String(), nullable=True),
        sa.Column("episode", sa.Integer(), nullable=True),
        sa.Column("step", sa.Integer(), nullable=True),
        sa.Column("reward", sa.Float(), nullable=True),
        sa.Column("loss", sa.Float(), nullable=True),
        sa.Column("epsilon", sa.Float(), nullable=True),
        sa.Column("q_value", sa.Float(), nullable=True),
        sa.Column("replay_size", sa.Integer(), nullable=True),
        sa.Column("speed", sa.Float(), nullable=True),
        sa.Column("progress", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metrics_episode", "metrics", ["episode"])
    op.create_index("ix_metrics_experiment_created_at", "metrics", ["experiment_id", "created_at"])
    op.create_index("ix_metrics_experiment_episode_step", "metrics", ["experiment_id", "episode", "step"])
    op.create_index("ix_metrics_experiment_id", "metrics", ["experiment_id"])
    op.create_index("ix_metrics_id", "metrics", ["id"])
    op.create_index("ix_metrics_step", "metrics", ["step"])

    op.create_table(
        "checkpoints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.String(), nullable=True),
        sa.Column("episode", sa.Integer(), nullable=True),
        sa.Column("path", sa.String(), nullable=True),
        sa.Column("reward", sa.Float(), nullable=True),
        sa.Column("epsilon", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_checkpoints_episode", "checkpoints", ["episode"])
    op.create_index("ix_checkpoints_experiment_episode", "checkpoints", ["experiment_id", "episode"])
    op.create_index("ix_checkpoints_experiment_id", "checkpoints", ["experiment_id"])
    op.create_index("ix_checkpoints_id", "checkpoints", ["id"])

    op.create_table(
        "frames",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.String(), nullable=True),
        sa.Column("episode", sa.Integer(), nullable=True),
        sa.Column("step", sa.Integer(), nullable=True),
        sa.Column("png", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_frames_episode", "frames", ["episode"])
    op.create_index("ix_frames_experiment_created_at", "frames", ["experiment_id", "created_at"])
    op.create_index("ix_frames_experiment_id", "frames", ["experiment_id"])
    op.create_index("ix_frames_id", "frames", ["id"])


def downgrade() -> None:
    op.drop_table("frames")
    op.drop_table("checkpoints")
    op.drop_table("metrics")
    op.drop_table("episodes")
    op.drop_table("experiments")
