"""Tests for the extraction engine and parsers."""

import json
import pytest

from discovery_engine.llm.parsers import extract_json, parse_llm_output, parse_llm_list
from discovery_engine.schemas.extraction import JobExtracted, PainPointExtracted
from discovery_engine.models.project import Project
from discovery_engine.models.interview import Interview


# --- Parser unit tests (no LLM needed) ---

class TestExtractJson:
    def test_direct_json(self):
        result = extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_fenced_json(self):
        text = 'Here is the output:\n```json\n{"key": "value"}\n```'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_embedded_json(self):
        text = 'Some text before {"key": "value"} and after'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_array_json(self):
        result = extract_json('[{"a": 1}, {"a": 2}]')
        assert result == [{"a": 1}, {"a": 2}]

    def test_nested_json(self):
        text = '{"outer": {"inner": [1, 2, 3]}}'
        result = extract_json(text)
        assert result["outer"]["inner"] == [1, 2, 3]

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError):
            extract_json("not json at all")


class TestParseLlmOutput:
    def test_parse_job(self):
        raw = json.dumps({
            "statement": "When I need to prioritize features, I want clear data, so I can make confident decisions",
            "context": "Quarterly planning",
            "frequency": "quarterly",
            "importance": "critical",
            "satisfaction": "very_unsatisfied",
            "supporting_quote": "I don't really have good data on what customers actually need",
            "confidence": 0.9,
        })
        result = parse_llm_output(raw, JobExtracted)
        assert result.statement.startswith("When I need")
        assert result.confidence == 0.9

    def test_parse_pain_point(self):
        raw = json.dumps({
            "description": "Cannot find patterns across multiple customer interviews",
            "severity": "high",
            "frequency": "quarterly",
            "emotional_intensity": "high",
            "supporting_quote": "trying to find patterns across multiple interviews",
            "confidence": 0.85,
        })
        result = parse_llm_output(raw, PainPointExtracted)
        assert "patterns" in result.description
        assert result.severity == "high"


class TestParseLlmList:
    def test_parse_array(self):
        raw = json.dumps([
            {"statement": "Job 1", "context": "", "frequency": "", "importance": "", "satisfaction": "", "supporting_quote": "", "confidence": 0.8},
            {"statement": "Job 2", "context": "", "frequency": "", "importance": "", "satisfaction": "", "supporting_quote": "", "confidence": 0.7},
        ])
        result = parse_llm_list(raw, JobExtracted)
        assert len(result) == 2
        assert result[0].statement == "Job 1"

    def test_parse_wrapped_array(self):
        raw = json.dumps({
            "jobs": [
                {"statement": "Job 1", "context": "", "frequency": "", "importance": "", "satisfaction": "", "supporting_quote": "", "confidence": 0.8},
            ]
        })
        result = parse_llm_list(raw, JobExtracted)
        assert len(result) == 1


# --- Model creation tests (no LLM needed) ---

class TestModels:
    def test_create_project(self, db_session):
        project = Project(name="Test Project", description="Testing", hypothesis="Users need X")
        db_session.add(project)
        db_session.commit()
        assert project.id is not None
        assert project.name == "Test Project"

    def test_create_interview(self, db_session):
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.commit()

        interview = Interview(
            project_id=project.id,
            title="Interview 1",
            transcript="Some transcript text",
            status="uploaded",
        )
        db_session.add(interview)
        db_session.commit()
        assert interview.id is not None
        assert interview.project_id == project.id

    def test_sample_transcripts_load(self, sample_transcript_1, sample_transcript_2):
        assert len(sample_transcript_1) > 100
        assert len(sample_transcript_2) > 100
        assert "Sarah" in sample_transcript_1
        assert "Marcus" in sample_transcript_2
