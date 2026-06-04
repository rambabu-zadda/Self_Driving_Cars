from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
from models import Checkpoint, Episode, Experiment, Frame, Metric


def test_research_schema_creates_on_sqlite_memory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    experiment = Experiment(
        id="exp-test",
        name="Test",
        algorithm="DQN",
        status="running",
    )
    session.add(experiment)
    session.add(Episode(experiment_id="exp-test", episode=1, reward=1.0, crashes=0, duration=10, success=1))
    session.add(Metric(experiment_id="exp-test", episode=1, step=5, reward=0.5, epsilon=0.9))
    session.add(Checkpoint(experiment_id="exp-test", episode=1, path="checkpoints/test.pt"))
    session.add(Frame(experiment_id="exp-test", episode=1, step=5, png=b"png"))
    session.commit()

    assert session.query(Experiment).count() == 1
    assert session.query(Episode).filter_by(experiment_id="exp-test").count() == 1
    assert session.query(Metric).filter_by(experiment_id="exp-test").count() == 1
    session.close()
