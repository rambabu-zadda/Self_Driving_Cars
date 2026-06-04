# backend/db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")
AUTO_CREATE_TABLES = os.getenv("AUTO_CREATE_TABLES", "true").lower() == "true"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    from models import Checkpoint, Episode, Experiment, Frame, Metric  # ensure models imported
    if AUTO_CREATE_TABLES and DATABASE_URL.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
        _ensure_sqlite_columns()


def _ensure_sqlite_columns():
    compatibility_columns = {
        "episodes": {
            "experiment_id": "TEXT",
            "success": "INTEGER DEFAULT 0",
        },
        "frames": {
            "experiment_id": "TEXT",
        },
    }
    with engine.begin() as connection:
        for table, columns in compatibility_columns.items():
            existing = {
                row[1]
                for row in connection.exec_driver_sql(f"PRAGMA table_info({table})")
            }
            for column, ddl in columns.items():
                if column not in existing:
                    connection.exec_driver_sql(
                        f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"
                    )
