"""Regression tests for engine behaviors that affect product reliability."""

import pytest

from discovery_engine.engine.extraction import ExtractionEngine
from discovery_engine.engine.recommender import RecommendationEngine
from discovery_engine.models.extraction import Job, Opportunity, PainPoint, Workaround
from discovery_engine.models.interview import Interview
from discovery_engine.models.project import Project
from discovery_engine.models.recommendation import EvidenceChain, Recommendation


@pytest.mark.asyncio
async def test_extraction_rerun_replaces_previous_results(db_session):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()

    interview = Interview(project_id=project.id, transcript="sample", status="uploaded")
    db_session.add(interview)
    db_session.commit()

    engine = ExtractionEngine(db_session)

    async def fake_extract_jobs(_interview):
        job = Job(interview_id=interview.id, statement="job-1")
        db_session.add(job)
        return [job]

    async def fake_extract_pains(_interview):
        pain = PainPoint(interview_id=interview.id, description="pain-1")
        db_session.add(pain)
        return [pain]

    async def fake_extract_workarounds(_interview):
        wa = Workaround(interview_id=interview.id, description="wa-1")
        db_session.add(wa)
        return [wa]

    async def fake_map_opportunities(_interview, _jobs, _pains, _was):
        opp = Opportunity(interview_id=interview.id, description="opp-1")
        db_session.add(opp)
        return [opp]

    engine.extract_jobs = fake_extract_jobs
    engine.extract_pain_points = fake_extract_pains
    engine.extract_workarounds = fake_extract_workarounds
    engine._map_opportunities = fake_map_opportunities

    await engine.extract_all(interview)
    await engine.extract_all(interview)

    assert db_session.query(Job).filter(Job.interview_id == interview.id).count() == 1
    assert db_session.query(PainPoint).filter(PainPoint.interview_id == interview.id).count() == 1
    assert db_session.query(Workaround).filter(Workaround.interview_id == interview.id).count() == 1
    assert db_session.query(Opportunity).filter(Opportunity.interview_id == interview.id).count() == 1


@pytest.mark.asyncio
async def test_recommendation_refresh_cleans_old_evidence(db_session, monkeypatch):
    project = Project(name="Test")
    db_session.add(project)
    db_session.commit()

    interview = Interview(project_id=project.id, transcript="sample", status="analyzed")
    db_session.add(interview)
    db_session.commit()

    rec = Recommendation(project_id=project.id, title="Old", description="Old rec")
    db_session.add(rec)
    db_session.flush()
    db_session.add(
        EvidenceChain(
            recommendation_id=rec.id,
            interview_id=interview.id,
            evidence_type="pain",
            quote="old quote",
            relevance_score=0.5,
        )
    )
    db_session.commit()

    async def fake_complete(*args, **kwargs):
        return "[]"

    monkeypatch.setattr("discovery_engine.engine.recommender.complete", fake_complete)

    engine = RecommendationEngine(db_session)
    await engine.generate(project.id)

    assert db_session.query(Recommendation).filter(Recommendation.project_id == project.id).count() == 0
    assert db_session.query(EvidenceChain).count() == 0
