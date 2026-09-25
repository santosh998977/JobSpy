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


def test_verified_experience_notes_persist_when_later_save_omits_them():
    session = make_session()
    repository = JobRepository(session)
    profile = repository.list_resume_lab_profiles()[1]
    saved = repository.save_resume_lab_resume(
        profile.id,
        resume_text="Java engineer with Spring Boot and APIs. " * 3,
        resume_filename="java.txt",
        expected_source_version=0,
        only_if_empty=False,
        verified_experience_notes="- Built Kafka consumers for order processing.",
    )

    assert saved.verified_experience_notes == "- Built Kafka consumers for order processing."
    assert saved.source_version == 1

    saved_again = repository.save_resume_lab_resume(
        profile.id,
        resume_text=saved.resume_text,
        resume_filename=saved.resume_filename,
        expected_source_version=1,
        only_if_empty=False,
    )

    assert saved_again.verified_experience_notes == saved.verified_experience_notes
    assert saved_again.source_version == 2


def test_profile_api_saves_notes_and_rejects_oversized_notes():
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        profile = next(
            item
            for item in client.get("/resume-lab/profiles").json()
            if item["name"] == "Java Developer"
        )
        resume_text = "Java engineer with Spring Boot, APIs, and SQL. " * 3
        response = client.put(
            f"/resume-lab/profiles/{profile['id']}/resume",
            json={
                "resume_text": resume_text,
                "resume_filename": "java.txt",
                "expected_source_version": 0,
                "verified_experience_notes": "- Built Kafka consumers.",
            },
        )

        assert response.status_code == 200
        assert response.json()["verified_experience_notes"] == "- Built Kafka consumers."
        assert response.json()["source_version"] == 1

        oversized = client.put(
            f"/resume-lab/profiles/{profile['id']}/resume",
            json={
                "resume_text": resume_text,
                "resume_filename": "java.txt",
                "expected_source_version": 1,
                "verified_experience_notes": "x" * 6001,
            },
        )
        assert oversized.status_code == 422
    finally:
        app.dependency_overrides.clear()
