"""Test fixtures and configuration."""

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from discovery_engine.models.base import Base


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_transcript_1():
    return (FIXTURES_DIR / "sample_transcript_1.txt").read_text()


@pytest.fixture
def sample_transcript_2():
    return (FIXTURES_DIR / "sample_transcript_2.txt").read_text()
