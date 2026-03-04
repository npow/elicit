"""Analysis endpoints — trigger extraction, synthesis, recommendations."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from discovery_engine.database import get_db
from discovery_engine.models.interview import Interview
from discovery_engine.models.extraction import Job, PainPoint, Workaround, Opportunity
from discovery_engine.models.synthesis import CrossInterviewPattern
from discovery_engine.models.recommendation import Recommendation, EvidenceChain
from discovery_engine.models.analysis_job import AnalysisJob
from discovery_engine.engine.extraction import ExtractionEngine
from discovery_engine.engine.synthesis import SynthesisEngine
from discovery_engine.engine.recommender import RecommendationEngine
from discovery_engine.engine.opportunity_tree import OpportunityTreeEngine
from discovery_engine.engine.job_runner import schedule_analysis_job

router = APIRouter()


@router.post("/jobs/extract/{interview_id}")
async def queue_extraction_job(interview_id: str, db: Session = Depends(get_db)):
    """Queue extraction as an async background job."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    if not interview.transcript:
        raise HTTPException(status_code=400, detail="Interview has no transcript")

    job = AnalysisJob(
        job_type="extract",
        status="queued",
        project_id=interview.project_id,
        interview_id=interview.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    schedule_analysis_job(job.id)
    return _job_dict(job)


@router.post("/jobs/synthesize/{project_id}")
async def queue_synthesis_job(project_id: str, db: Session = Depends(get_db)):
    """Queue cross-interview synthesis as an async background job."""
    job = AnalysisJob(
        job_type="synthesize",
        status="queued",
        project_id=project_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    schedule_analysis_job(job.id)
    return _job_dict(job)


@router.post("/jobs/recommend/{project_id}")
async def queue_recommendation_job(project_id: str, db: Session = Depends(get_db)):
    """Queue recommendation generation as an async background job."""
    job = AnalysisJob(
        job_type="recommend",
        status="queued",
        project_id=project_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    schedule_analysis_job(job.id)
    return _job_dict(job)


@router.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get one async analysis job."""
    job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_dict(job)


@router.get("/jobs")
def list_jobs(project_id: str | None = None, limit: int = 20, db: Session = Depends(get_db)):
    """List recent async analysis jobs."""
    q = db.query(AnalysisJob)
    if project_id:
        q = q.filter(AnalysisJob.project_id == project_id)
    jobs = q.order_by(AnalysisJob.created_at.desc()).limit(limit).all()
    return [_job_dict(j) for j in jobs]


@router.post("/extract/{interview_id}")
async def run_extraction(interview_id: str, db: Session = Depends(get_db)):
    """Run JTBD/pain/workaround extraction on an interview."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    if not interview.transcript:
        raise HTTPException(status_code=400, detail="Interview has no transcript")

    engine = ExtractionEngine(db)
    result = await engine.extract_all(interview)

    return {
        "interview_id": interview_id,
        "jobs_count": len(result["jobs"]),
        "pain_points_count": len(result["pain_points"]),
        "workarounds_count": len(result["workarounds"]),
        "opportunities_count": len(result["opportunities"]),
    }


@router.post("/synthesize/{project_id}")
async def run_synthesis(project_id: str, db: Session = Depends(get_db)):
    """Run cross-interview pattern detection."""
    engine = SynthesisEngine(db)
    patterns = await engine.synthesize(project_id)
    return {
        "project_id": project_id,
        "patterns_count": len(patterns),
        "patterns": [
            {
                "id": p.id,
                "pattern_type": p.pattern_type,
                "description": p.description,
                "frequency_count": p.frequency_count,
                "strength": p.strength,
            }
            for p in patterns
        ],
    }


@router.post("/recommend/{project_id}")
async def run_recommendations(project_id: str, db: Session = Depends(get_db)):
    """Generate product recommendations."""
    engine = RecommendationEngine(db)
    try:
        recommendations = await engine.generate(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "project_id": project_id,
        "recommendations_count": len(recommendations),
        "recommendations": [
            {
                "id": r.id,
                "title": r.title,
                "priority_score": r.priority_score,
                "priority_rank": r.priority_rank,
                "category": r.category,
            }
            for r in recommendations
        ],
    }


@router.get("/extractions/{interview_id}")
def get_extractions(interview_id: str, db: Session = Depends(get_db)):
    """Get all extractions for an interview."""
    jobs = db.query(Job).filter(Job.interview_id == interview_id).all()
    pains = db.query(PainPoint).filter(PainPoint.interview_id == interview_id).all()
    workarounds = db.query(Workaround).filter(Workaround.interview_id == interview_id).all()
    opps = db.query(Opportunity).filter(Opportunity.interview_id == interview_id).all()

    return {
        "jobs": [_job_dict(j) for j in jobs],
        "pain_points": [_pain_dict(p) for p in pains],
        "workarounds": [_wa_dict(w) for w in workarounds],
        "opportunities": [_opp_dict(o) for o in opps],
    }


@router.get("/patterns/{project_id}")
def get_patterns(project_id: str, db: Session = Depends(get_db)):
    """Get cross-interview patterns."""
    patterns = (
        db.query(CrossInterviewPattern)
        .filter(CrossInterviewPattern.project_id == project_id)
        .order_by(CrossInterviewPattern.strength.desc())
        .all()
    )
    return [
        {
            "id": p.id,
            "pattern_type": p.pattern_type,
            "description": p.description,
            "frequency_count": p.frequency_count,
            "strength": p.strength,
            "interview_ids": p.interview_ids,
            "supporting_quotes": p.supporting_quotes,
            "confidence": p.confidence,
        }
        for p in patterns
    ]


@router.get("/recommendations/{project_id}")
def get_recommendations(project_id: str, db: Session = Depends(get_db)):
    """Get recommendations with evidence chains."""
    recs = (
        db.query(Recommendation)
        .filter(Recommendation.project_id == project_id)
        .order_by(Recommendation.priority_rank)
        .all()
    )
    result = []
    for r in recs:
        chains = db.query(EvidenceChain).filter(EvidenceChain.recommendation_id == r.id).all()
        result.append({
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "priority_score": r.priority_score,
            "priority_rank": r.priority_rank,
            "category": r.category,
            "confidence": r.confidence,
            "rationale": r.rationale,
            "risks": r.risks,
            "next_steps": r.next_steps,
            "evidence_chains": [
                {
                    "id": c.id,
                    "interview_id": c.interview_id,
                    "evidence_type": c.evidence_type,
                    "quote": c.quote,
                    "relevance_score": c.relevance_score,
                }
                for c in chains
            ],
        })
    return result


@router.get("/opportunity-tree/{project_id}")
def get_opportunity_tree(project_id: str, db: Session = Depends(get_db)):
    """Get the Opportunity Solution Tree."""
    engine = OpportunityTreeEngine(db)
    return engine.build_tree(project_id)


@router.get("/top-opportunities/{project_id}")
def get_top_opportunities(
    project_id: str, limit: int = 10, db: Session = Depends(get_db)
):
    engine = OpportunityTreeEngine(db)
    return engine.get_top_opportunities(project_id, limit=limit)


def _job_dict(j: Job) -> dict:
    return {
        "id": j.id,
        "statement": j.statement,
        "context": j.context,
        "frequency": j.frequency,
        "importance": j.importance,
        "satisfaction": j.satisfaction,
        "supporting_quote": j.supporting_quote,
        "confidence": j.confidence,
    }


def _pain_dict(p: PainPoint) -> dict:
    return {
        "id": p.id,
        "description": p.description,
        "severity": p.severity,
        "frequency": p.frequency,
        "emotional_intensity": p.emotional_intensity,
        "supporting_quote": p.supporting_quote,
        "confidence": p.confidence,
    }


def _wa_dict(w: Workaround) -> dict:
    return {
        "id": w.id,
        "description": w.description,
        "tools_used": w.tools_used,
        "effort_level": w.effort_level,
        "satisfaction_with_workaround": w.satisfaction_with_workaround,
        "supporting_quote": w.supporting_quote,
        "confidence": w.confidence,
    }


def _opp_dict(o: Opportunity) -> dict:
    return {
        "id": o.id,
        "description": o.description,
        "opportunity_score": o.opportunity_score,
        "importance_score": o.importance_score,
        "satisfaction_score": o.satisfaction_score,
        "market_size_indicator": o.market_size_indicator,
        "confidence": o.confidence,
    }


def _iso(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def _job_dict(job: AnalysisJob) -> dict:
    return {
        "id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "project_id": job.project_id,
        "interview_id": job.interview_id,
        "result": job.result or {},
        "error_message": job.error_message or "",
        "created_at": _iso(job.created_at),
        "started_at": _iso(job.started_at),
        "completed_at": _iso(job.completed_at),
    }
