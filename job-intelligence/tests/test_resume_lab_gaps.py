from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import app
from storage.database import get_session
from storage.models import Base
from storage.repository import JobRepository


def make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_gap_endpoint_excludes_keywords_supported_by_verified_notes():
    session = make_session()
    repository = JobRepository(session)
    profile = repository.list_resume_lab_profiles()[1]
    repository.save_resume_lab_resume(
        profile.id,
        resume_text="Java engineer with Spring Boot, REST APIs, and SQL. " * 3,
        resume_filename="java.txt",
        expected_source_version=0,
        only_if_empty=False,
        verified_experience_notes="- Built Kafka consumers for order processing.",
    )
    session.commit()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.post(
            "/resume-lab/gaps",
            json={
                "profile_id": profile.id,
                "source_version": 1,
                "job_description": (
                    "Senior Java role requiring Spring Boot, Kafka, Kubernetes, "
                    "Oracle, REST APIs, and SQL experience."
                ),
                "target_title": "Senior Java Developer",
            },
        )

        assert response.status_code == 200
        missing = response.json()["missing_keywords"]
        assert "Kafka" not in missing
        assert "Kubernetes" in missing
        assert "Oracle" in missing
        assert len(missing) <= 10

        stale = client.post(
            "/resume-lab/gaps",
            json={
                "profile_id": profile.id,
                "source_version": 0,
                "job_description": (
                    "Senior Java role requiring Spring Boot, Kafka, Kubernetes, "
                    "Oracle, REST APIs, and SQL experience."
                ),
                "target_title": "Senior Java Developer",
            },
        )
        assert stale.status_code == 409
    finally:
        app.dependency_overrides.clear()
