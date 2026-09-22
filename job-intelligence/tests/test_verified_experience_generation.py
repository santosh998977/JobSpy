from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ai.resume_orchestrator import (
    GenerationEvent,
    GenerationMode,
    OrchestrationRequest,
    OrchestrationResult,
    _messages,
)
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


def test_generation_uses_verified_notes_and_changes_source_hash(monkeypatch):
    session = make_session()
    repository = JobRepository(session)
    profile = repository.list_resume_lab_profiles()[1]
    repository.save_resume_lab_resume(
        profile.id,
        resume_text="Java engineer with Spring Boot, APIs, and SQL. " * 3,
        resume_filename="java.txt",
        expected_source_version=0,
        only_if_empty=False,
        verified_experience_notes="- Built Kafka consumers for order processing.",
    )
    session.commit()
    resume_hash = profile.resume_sha256
    calls = []

    def fake_orchestrate(request, settings):
        calls.append(request)
        return OrchestrationResult(
            status="REVIEWED",
            resume_text="Generated Java resume with Kafka. " * 3,
            ats_score=90,
            events=[
                GenerationEvent(
                    "ATS_TARGET_REACHED",
                    "info",
                    "ats",
                    "openrouter",
                    "test-model",
                    1,
                    datetime.now(UTC).isoformat(),
                    "90",
                )
            ],
        )

    monkeypatch.setattr("api.main.orchestrate_resume", fake_orchestrate)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        response = TestClient(app).post(
            "/resume-lab/generate",
            json={
                "profile_id": profile.id,
                "source_version": 1,
                "mode": "IMPORTANT",
                "job_description": "Senior Java role requiring Spring Boot, Kafka, APIs, and SQL. " * 2,
                "target_title": "Senior Java Developer",
                "company_name": "Example",
                "idempotency_key": "verified-notes-test-0001",
            },
        )
        assert response.status_code == 200
        assert "USER-VERIFIED EXPERIENCE NOTES" in calls[0].source_resume
        assert "Built Kafka consumers" in calls[0].source_resume
        run = repository.get_resume_lab_run(response.json()["run_id"])
        assert run.source_hash != resume_hash
    finally:
        app.dependency_overrides.clear()


def test_writer_integrates_notes_without_outputting_notes_section():
    request = OrchestrationRequest(
        source_resume=(
            "Java engineer with Spring Boot.\n\n"
            "USER-VERIFIED EXPERIENCE NOTES (source facts only):\n"
            "- Built Kafka consumers for order processing."
        ),
        job_description="Senior Java role requiring Spring Boot and Kafka experience.",
        target_title="Senior Java Developer",
        company_name="Example",
        mode=GenerationMode.IMPORTANT,
    )

    prompt = _messages(request)[-1]["content"].lower()

    assert "integrate relevant user-verified notes" in prompt
    assert "do not output a separate verified-notes" in prompt
