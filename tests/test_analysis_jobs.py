"""Tests for async analysis job execution."""

import pytest

from discovery_engine.engine import job_runner
from discovery_engine.models.analysis_job import AnalysisJob
from discovery_engine.models.interview import Interview
from discovery_engine.models.project import Project


@pytest.mark.asyncio
async def test_run_extract_job_completes(db_session, monkeypatch):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()

    interview = Interview(project_id=project.id, transcript="hello", status="uploaded")
    db_session.add(interview)
    db_session.commit()

    job = AnalysisJob(
        job_type="extract",
        status="queued",
        project_id=project.id,
        interview_id=interview.id,
    )
    db_session.add(job)
    db_session.commit()
    job_id = job.id

    async def fake_extract_all(self, _interview):
        return {
            "jobs": [1, 2],
            "pain_points": [1],
            "workarounds": [],
            "opportunities": [1],
        }

    monkeypatch.setattr(job_runner, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(
        "discovery_engine.engine.extraction.ExtractionEngine.extract_all",
        fake_extract_all,
    )

    await job_runner._run_analysis_job(job_id)

    refreshed = db_session.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    assert refreshed is not None
    assert refreshed.status == "completed"
    assert refreshed.result["jobs_count"] == 2
    assert refreshed.result["pain_points_count"] == 1


@pytest.mark.asyncio
async def test_run_job_failure_sets_failed_status(db_session, monkeypatch):
    job = AnalysisJob(job_type="unknown", status="queued")
    db_session.add(job)
    db_session.commit()
    job_id = job.id

    monkeypatch.setattr(job_runner, "SessionLocal", lambda: db_session)

    await job_runner._run_analysis_job(job_id)

    refreshed = db_session.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    assert refreshed is not None
    assert refreshed.status == "failed"
    assert "Unsupported job_type" in refreshed.error_message
