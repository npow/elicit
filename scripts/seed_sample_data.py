"""Seed the database with sample data for development."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from discovery_engine.database import init_db, SessionLocal
from discovery_engine.models.project import Project
from discovery_engine.models.interview import Interview

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"
WEB_FIXTURES_DIR = Path(__file__).parent / "fixtures"


def seed():
    init_db()
    db = SessionLocal()

    # Create sample project
    project = Project(
        name="Elicit Validation",
        description="Validating the idea of an AI-powered customer discovery platform for startup PMs",
        hypothesis="Product managers at early/mid-stage startups struggle to systematically analyze customer interviews and often miss critical patterns across conversations.",
        target_customer="Product managers at Series A-C startups with 20-500 employees",
    )
    db.add(project)
    db.commit()

    # Add sample interviews
    for i, name in enumerate(["sample_transcript_1.txt", "sample_transcript_2.txt"], 1):
        path = FIXTURES_DIR / name
        if path.exists():
            transcript = path.read_text()
            interview = Interview(
                project_id=project.id,
                title=f"Sample Interview {i}",
                interviewee_name="Sarah Chen" if i == 1 else "Marcus Johnson",
                interviewee_role="Product Manager" if i == 1 else "Head of Product",
                transcript=transcript,
                source_type="text",
                status="uploaded",
            )
            db.add(interview)

    # Create project with web-derived (paraphrased) interview examples
    web_project = Project(
        name="Web Interview Examples",
        description="Paraphrased interview examples grounded in public JTBD interviews from jobstobedone.org",
        hypothesis="Teams need traceable, evidence-backed synthesis from real interview narratives.",
        target_customer="Product teams validating early product direction",
    )
    db.add(web_project)
    db.commit()

    web_interviews = [
        {
            "file": "web_interview_smartphone.txt",
            "title": "Smartphone Purchase Interview (Web Example)",
            "name": "Consumer Upgrade Buyer",
            "role": "Knowledge Worker",
        },
        {
            "file": "web_interview_camera.txt",
            "title": "Camera Purchase Interview (Web Example)",
            "name": "Creator Buyer",
            "role": "Frequent Traveler",
        },
        {
            "file": "web_interview_mattress.txt",
            "title": "Mattress Purchase Interview (Web Example)",
            "name": "Sleep Improvement Buyer",
            "role": "Working Professional",
        },
    ]

    for item in web_interviews:
        path = WEB_FIXTURES_DIR / item["file"]
        if not path.exists():
            continue
        transcript = path.read_text()
        interview = Interview(
            project_id=web_project.id,
            title=item["title"],
            interviewee_name=item["name"],
            interviewee_role=item["role"],
            transcript=transcript,
            source_type="text",
            status="uploaded",
        )
        db.add(interview)

    db.commit()
    print(f"Seeded project: {project.name} (ID: {project.id})")
    print(f"Seeded project: {web_project.name} (ID: {web_project.id})")
    print(f"Seeded {db.query(Interview).count()} interviews total")
    db.close()


if __name__ == "__main__":
    seed()
