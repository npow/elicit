"""Tests for the bug fixes: confidence, scoring, linking, evidence chains, quality score."""

import pytest

from discovery_engine.engine.extraction import _confidence_or_default, _link_pains_to_jobs, _best_match
from discovery_engine.engine.simulator import SimulatorEngine
from discovery_engine.models.extraction import Job, PainPoint, Opportunity
from discovery_engine.models.interview import Interview
from discovery_engine.models.persona import SyntheticPersona, SyntheticSession
from discovery_engine.models.project import Project
from discovery_engine.models.recommendation import EvidenceChain, Recommendation
from discovery_engine.schemas.extraction import OpportunityExtracted
from discovery_engine.schemas.normalization import text_similarity, to_score_0_1
from discovery_engine.schemas.persona import PersonaExtracted
from discovery_engine.schemas.coaching import InterviewGuideExtracted


# ---------------------------------------------------------------------------
# text_similarity
# ---------------------------------------------------------------------------


def test_text_similarity_identical():
    assert text_similarity("improve dashboard usability", "improve dashboard usability") == 1.0


def test_text_similarity_partial():
    score = text_similarity("improve dashboard reporting", "dashboard reporting tool")
    assert 0.0 < score < 1.0


def test_text_similarity_unrelated():
    score = text_similarity("coffee machine maintenance", "software deployment pipeline")
    assert score < 0.15


def test_text_similarity_empty():
    assert text_similarity("", "something") == 0.0
    assert text_similarity("something", "") == 0.0


# ---------------------------------------------------------------------------
# _confidence_or_default
# ---------------------------------------------------------------------------


def test_confidence_zero_is_kept():
    """confidence=0.0 means 'completely uncertain', not 'missing'."""
    assert _confidence_or_default(0.0, default=0.72) == 0.0


def test_confidence_none_uses_default():
    assert _confidence_or_default(None, default=0.72) == 0.72


def test_confidence_negative_uses_default():
    assert _confidence_or_default(-0.1, default=0.72) == 0.72


def test_confidence_valid_value_kept():
    assert _confidence_or_default(0.85, default=0.72) == 0.85


# ---------------------------------------------------------------------------
# OpportunityExtracted score clamping
# ---------------------------------------------------------------------------


def test_opportunity_score_clamped():
    opp = OpportunityExtracted(
        description="test",
        opportunity_score=25,   # above max 20
        importance_score=15,    # above max 10
        satisfaction_score=-1,  # below min 0
    )
    assert opp.opportunity_score == 20.0
    assert opp.importance_score == 10.0
    assert opp.satisfaction_score == 0.0


def test_opportunity_level_string_mapping():
    opp = OpportunityExtracted(description="x", level="strategic")
    assert opp.level == 0
    opp2 = OpportunityExtracted(description="x", level="tactical")
    assert opp2.level == 1
    opp3 = OpportunityExtracted(description="x", level="quick_win")
    assert opp3.level == 2


def test_opportunity_level_unknown_string_defaults_zero():
    opp = OpportunityExtracted(description="x", level="unknown_level")
    assert opp.level == 0


# ---------------------------------------------------------------------------
# _link_pains_to_jobs
# ---------------------------------------------------------------------------


def test_link_pains_to_jobs_sets_related_job_id(db_session):
    project = Project(name="Link test")
    db_session.add(project)
    db_session.commit()

    interview = Interview(project_id=project.id, transcript="t", status="uploaded")
    db_session.add(interview)
    db_session.commit()

    job = Job(interview_id=interview.id, statement="manage project timelines and deadlines")
    pain = PainPoint(interview_id=interview.id, description="project timelines are hard to track")
    db_session.add(job)
    db_session.add(pain)
    db_session.flush()

    _link_pains_to_jobs([pain], [job])
    assert pain.related_job_id == job.id


def test_link_pains_to_jobs_no_match_leaves_null(db_session):
    project = Project(name="No match")
    db_session.add(project)
    db_session.commit()

    interview = Interview(project_id=project.id, transcript="t", status="uploaded")
    db_session.add(interview)
    db_session.commit()

    job = Job(interview_id=interview.id, statement="bake sourdough bread every morning")
    pain = PainPoint(interview_id=interview.id, description="software crashes constantly")
    db_session.add(job)
    db_session.add(pain)
    db_session.flush()

    _link_pains_to_jobs([pain], [job])
    # Similarity is below threshold so no link
    assert pain.related_job_id is None


# ---------------------------------------------------------------------------
# Fallback recommendation prioritization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fallback_recommendations_priority_not_floored(db_session, monkeypatch):
    """Fallback recs should have differentiated priority, not all floored to 0.45."""
    from discovery_engine.engine.recommender import RecommendationEngine

    project = Project(name="Priority test")
    db_session.add(project)
    db_session.commit()

    interview = Interview(project_id=project.id, transcript="t", status="analyzed")
    db_session.add(interview)
    db_session.commit()

    # Low-score opportunity (score=4/20 → normalized=0.2)
    low_opp = Opportunity(
        interview_id=interview.id,
        description="minor improvement A",
        opportunity_score=4.0,
    )
    # High-score opportunity (score=16/20 → normalized=0.8)
    high_opp = Opportunity(
        interview_id=interview.id,
        description="critical improvement B",
        opportunity_score=16.0,
    )
    db_session.add(low_opp)
    db_session.add(high_opp)
    db_session.commit()

    async def fake_complete(*args, **kwargs):
        return "[]"  # Force fallback path

    monkeypatch.setattr("discovery_engine.engine.recommender.complete", fake_complete)

    engine = RecommendationEngine(db_session)
    recs = await engine.generate(project.id)

    scores = [r.priority_score for r in recs]
    # High-opp rec should come before low-opp rec (higher score)
    assert max(scores) > 0.5
    # Scores should be differentiated, not all the same
    assert max(scores) - min(scores) > 0.1


# ---------------------------------------------------------------------------
# Evidence chains use real similarity scores
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evidence_chains_use_similarity_scores(db_session, monkeypatch):
    """Evidence chain relevance_score should reflect actual text similarity, not hardcoded 0.7."""
    from discovery_engine.engine.recommender import RecommendationEngine

    project = Project(name="Evidence test")
    db_session.add(project)
    db_session.commit()

    interview = Interview(project_id=project.id, transcript="t", status="analyzed")
    db_session.add(interview)
    db_session.commit()

    # Pain with HIGH overlap with recommendation text
    matching_pain = PainPoint(
        interview_id=interview.id,
        description="users struggle to export reports from dashboard",
        supporting_quote="I have to manually export every single report",
    )
    # Pain with LOW overlap
    irrelevant_pain = PainPoint(
        interview_id=interview.id,
        description="coffee machine in office is broken",
        supporting_quote="the coffee is terrible",
    )
    db_session.add(matching_pain)
    db_session.add(irrelevant_pain)
    db_session.commit()

    llm_response = """[{
        "title": "One-click dashboard report export",
        "description": "Allow users to export dashboard reports with a single click",
        "priority_score": 0.85,
        "category": "must_have",
        "confidence": 0.8,
        "rationale": "High demand for export",
        "risks": "Format compatibility",
        "next_steps": "Ship export button"
    }]"""

    async def fake_complete(*args, **kwargs):
        return llm_response

    monkeypatch.setattr("discovery_engine.engine.recommender.complete", fake_complete)

    engine = RecommendationEngine(db_session)
    recs = await engine.generate(project.id)
    assert len(recs) == 1

    chains = db_session.query(EvidenceChain).filter(
        EvidenceChain.recommendation_id == recs[0].id
    ).all()

    # The matching pain should be in evidence; the irrelevant one should not
    evidence_quotes = {c.quote for c in chains}
    assert any("export" in q.lower() for q in evidence_quotes), "Matching pain not found in evidence"
    assert not any("coffee" in q.lower() for q in evidence_quotes), "Irrelevant pain incorrectly included"

    # Relevance scores should be actual computed values, not hardcoded
    for c in chains:
        assert 0.0 < c.relevance_score < 1.0


# ---------------------------------------------------------------------------
# Session quality score
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_quality_score_computed(db_session):
    project = Project(name="Sim test")
    db_session.add(project)
    db_session.commit()

    persona = SyntheticPersona(
        project_id=project.id,
        name="Alice",
        role="PM",
        company_type="SaaS",
        background="5 years product",
        goals=["ship fast"],
        frustrations=["slow processes"],
        current_tools=["Jira"],
        behavioral_traits=["analytical"],
    )
    db_session.add(persona)
    db_session.commit()

    session = SyntheticSession(
        persona_id=persona.id,
        status="active",
        messages=[
            {"role": "user", "content": "Tell me about the last time you struggled with reporting."},
            {"role": "assistant", "content": "It was painful, the export took forever."},
            {"role": "user", "content": "What did you do to work around it?"},
            {"role": "assistant", "content": "I used a spreadsheet."},
        ],
        mom_test_violations=[],  # No violations
    )
    db_session.add(session)
    db_session.commit()

    engine = SimulatorEngine(db_session)
    result = await engine.end_session(session.id)

    assert result.status == "completed"
    assert result.session_quality_score is not None
    assert 0.0 <= result.session_quality_score <= 1.0


# ---------------------------------------------------------------------------
# Recommendation schema: risks/next_steps accept arrays
# ---------------------------------------------------------------------------


def test_recommendation_risks_list_to_string():
    from discovery_engine.schemas.recommendation import RecommendationExtracted

    rec = RecommendationExtracted(
        title="Ship it",
        risks=["Risk A", "Risk B"],
        next_steps=["Step 1", "Step 2", "Step 3"],
    )
    assert rec.risks == "Risk A\nRisk B"
    assert rec.next_steps == "Step 1\nStep 2\nStep 3"


def test_recommendation_risks_plain_string_unchanged():
    from discovery_engine.schemas.recommendation import RecommendationExtracted

    rec = RecommendationExtracted(title="Ship it", risks="Single risk", next_steps="Do the thing")
    assert rec.risks == "Single risk"
    assert rec.next_steps == "Do the thing"


def test_recommendation_risks_empty_list():
    from discovery_engine.schemas.recommendation import RecommendationExtracted

    rec = RecommendationExtracted(title="Ship it", risks=[], next_steps=[])
    assert rec.risks == ""
    assert rec.next_steps == ""


# ---------------------------------------------------------------------------
# API: _job_dict collision (extractions endpoint should return Job fields)
# ---------------------------------------------------------------------------


def test_extraction_api_returns_job_fields(db_session):
    """_job_dict for Job and _analysis_job_dict for AnalysisJob must be different functions."""
    from discovery_engine.api.analysis import _job_dict, _analysis_job_dict
    from discovery_engine.models.extraction import Job
    from discovery_engine.models.analysis_job import AnalysisJob
    from discovery_engine.models.project import Project
    from discovery_engine.models.interview import Interview

    project = Project(name="API test")
    db_session.add(project)
    db_session.commit()

    interview = Interview(project_id=project.id, transcript="t", status="uploaded")
    db_session.add(interview)
    db_session.commit()

    job = Job(interview_id=interview.id, statement="do something important", supporting_quote="yes")
    db_session.add(job)
    db_session.commit()

    result = _job_dict(job)
    assert "statement" in result, "_job_dict should return Job fields"
    assert "job_type" not in result, "_job_dict should NOT return AnalysisJob fields"

    analysis_job = AnalysisJob(job_type="extract", status="queued", project_id=project.id)
    db_session.add(analysis_job)
    db_session.commit()

    a_result = _analysis_job_dict(analysis_job)
    assert "job_type" in a_result, "_analysis_job_dict should return AnalysisJob fields"
    assert "statement" not in a_result, "_analysis_job_dict should NOT return Job fields"


# ---------------------------------------------------------------------------
# Session quality score: zero turns
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_quality_score_zero_turns(db_session):
    """A session with no turns should score 0, not 0.65."""
    project = Project(name="Zero turn test")
    db_session.add(project)
    db_session.commit()

    persona = SyntheticPersona(
        project_id=project.id,
        name="Charlie",
        role="Engineer",
        company_type="Tech",
        background="Backend dev",
        goals=["ship features"],
        frustrations=["slow CI"],
        current_tools=["GitHub"],
        behavioral_traits=["pragmatic"],
    )
    db_session.add(persona)
    db_session.commit()

    session = SyntheticSession(
        persona_id=persona.id,
        status="active",
        messages=[],  # No turns at all
        mom_test_violations=[],
    )
    db_session.add(session)
    db_session.commit()

    engine = SimulatorEngine(db_session)
    result = await engine.end_session(session.id)

    assert result.session_quality_score == 0.0


@pytest.mark.asyncio
async def test_session_quality_score_penalizes_violations(db_session):
    project = Project(name="Violation test")
    db_session.add(project)
    db_session.commit()

    persona = SyntheticPersona(
        project_id=project.id,
        name="Bob",
        role="Designer",
        company_type="Agency",
        background="UX background",
        goals=["good UX"],
        frustrations=["unclear requirements"],
        current_tools=["Figma"],
        behavioral_traits=["creative"],
    )
    db_session.add(persona)
    db_session.commit()

    # 2 user turns but 2 violations = 100% violation rate
    session_bad = SyntheticSession(
        persona_id=persona.id,
        status="active",
        messages=[
            {"role": "user", "content": "Would you pay $99/month for this?"},
            {"role": "assistant", "content": "Maybe."},
            {"role": "user", "content": "Don't you think dashboards are important?"},
            {"role": "assistant", "content": "I guess so."},
        ],
        mom_test_violations=[
            {"question": "Would you pay $99/month for this?", "violations": ["hypothetical", "pitching"]},
            {"question": "Don't you think dashboards are important?", "violations": ["leading"]},
        ],
    )
    db_session.add(session_bad)
    db_session.commit()

    engine = SimulatorEngine(db_session)
    result = await engine.end_session(session_bad.id)

    assert result.session_quality_score < 0.5  # Should be penalized


# ---------------------------------------------------------------------------
# to_score_0_1: text enum handling
# ---------------------------------------------------------------------------


def test_to_score_0_1_high():
    assert to_score_0_1("high") == 0.8


def test_to_score_0_1_medium():
    assert to_score_0_1("medium") == 0.5


def test_to_score_0_1_low():
    assert to_score_0_1("low") == 0.2


def test_to_score_0_1_HIGH_uppercase():
    assert to_score_0_1("HIGH") == 0.8


def test_to_score_0_1_numeric_unchanged():
    assert to_score_0_1(0.75) == 0.75
    assert to_score_0_1("0.75") == 0.75


def test_to_score_0_1_unknown_text_returns_zero():
    assert to_score_0_1("strong") == 0.0


# ---------------------------------------------------------------------------
# PersonaExtracted schema: current_tools and behavioral_traits
# ---------------------------------------------------------------------------


def test_persona_extracted_tools_from_dicts():
    """LLM returns list[{tool, usage, satisfaction}] — should extract tool names."""
    p = PersonaExtracted(
        name="Alice",
        current_tools=[
            {"tool": "Jira", "usage": "sprint planning", "satisfaction": "frustrated"},
            {"tool": "Notion", "usage": "notes", "satisfaction": "satisfied"},
        ],
    )
    assert p.current_tools == ["Jira", "Notion"]


def test_persona_extracted_tools_from_strings():
    """Plain list[str] should pass through unchanged."""
    p = PersonaExtracted(name="Bob", current_tools=["Slack", "GitHub"])
    assert p.current_tools == ["Slack", "GitHub"]


def test_persona_extracted_behavioral_traits_from_dict():
    """LLM returns dict of trait key/values — should flatten to list."""
    p = PersonaExtracted(
        name="Carol",
        behavioral_traits={
            "tech_savviness": "high",
            "change_tolerance": "open",
            "decision_style": "data_driven",
        },
    )
    assert "tech_savviness: high" in p.behavioral_traits
    assert "change_tolerance: open" in p.behavioral_traits
    assert len(p.behavioral_traits) == 3


def test_persona_extracted_behavioral_traits_from_list():
    """list[str] should pass through unchanged."""
    p = PersonaExtracted(name="Dave", behavioral_traits=["analytical", "data-driven"])
    assert p.behavioral_traits == ["analytical", "data-driven"]


# ---------------------------------------------------------------------------
# InterviewGuideExtracted: success_criteria accepts list
# ---------------------------------------------------------------------------


def test_interview_guide_success_criteria_list_joined():
    guide = InterviewGuideExtracted(
        success_criteria=[
            "Learned about their current workflow",
            "Discovered a pain point",
            "Got a specific quote",
        ]
    )
    assert guide.success_criteria == "Learned about their current workflow\nDiscovered a pain point\nGot a specific quote"


def test_interview_guide_success_criteria_string_unchanged():
    guide = InterviewGuideExtracted(success_criteria="Learned something useful")
    assert guide.success_criteria == "Learned something useful"
