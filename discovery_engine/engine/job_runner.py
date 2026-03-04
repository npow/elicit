"""Async analysis job scheduler/executor."""

import asyncio
from datetime import datetime, timezone

from discovery_engine.database import SessionLocal
from discovery_engine.engine.extraction import ExtractionEngine
from discovery_engine.engine.recommender import RecommendationEngine
from discovery_engine.engine.synthesis import SynthesisEngine
from discovery_engine.models.analysis_job import AnalysisJob
from discovery_engine.models.interview import Interview


def schedule_analysis_job(job_id: str) -> None:
    """Fire-and-forget execution on the running event loop."""
    asyncio.create_task(_run_analysis_job(job_id))


async def _run_analysis_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if not job:
            return

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        if job.job_type == "extract":
            interview = db.query(Interview).filter(Interview.id == job.interview_id).first()
            if not interview:
                raise ValueError(f"Interview {job.interview_id} not found")
            if not interview.transcript:
                raise ValueError("Interview has no transcript")
            result = await ExtractionEngine(db).extract_all(interview)
            job.result = {
                "interview_id": interview.id,
                "jobs_count": len(result.get("jobs", [])),
                "pain_points_count": len(result.get("pain_points", [])),
                "workarounds_count": len(result.get("workarounds", [])),
                "opportunities_count": len(result.get("opportunities", [])),
            }
        elif job.job_type == "synthesize":
            patterns = await SynthesisEngine(db).synthesize(job.project_id or "")
            job.result = {
                "project_id": job.project_id,
                "patterns_count": len(patterns),
            }
        elif job.job_type == "recommend":
            recommendations = await RecommendationEngine(db).generate(job.project_id or "")
            job.result = {
                "project_id": job.project_id,
                "recommendations_count": len(recommendations),
            }
        else:
            raise ValueError(f"Unsupported job_type: {job.job_type}")

        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job.error_message = ""
        db.commit()
    except Exception as exc:
        db.rollback()
        try:
            failed_job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
            if failed_job:
                failed_job.status = "failed"
                failed_job.error_message = str(exc)
                failed_job.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass  # Job stuck in unknown state; better than crashing error handler
    finally:
        db.close()
