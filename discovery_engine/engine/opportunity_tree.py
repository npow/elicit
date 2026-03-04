"""Opportunity Solution Tree builder from extractions."""

from sqlalchemy.orm import Session

from discovery_engine.models.extraction import Opportunity, Job, PainPoint, Workaround
from discovery_engine.models.interview import Interview


class OpportunityTreeEngine:
    """Build an Opportunity Solution Tree (OST) from extracted data."""

    def __init__(self, db: Session):
        self.db = db

    def build_tree(self, project_id: str) -> dict:
        """Build a hierarchical OST for a project.

        Structure:
        - Root: Project outcome (derived from hypothesis)
        - Level 1: Major opportunity areas (high-level jobs)
        - Level 2: Specific opportunities (pains/workarounds)
        - Level 3: Solution hypotheses (from recommendations)

        Returns a nested dict for visualization.
        """
        interviews = (
            self.db.query(Interview)
            .filter(Interview.project_id == project_id, Interview.status == "analyzed")
            .all()
        )

        if not interviews:
            return {"name": "No analyzed interviews", "children": []}

        interview_ids = [i.id for i in interviews]

        # Gather all extractions
        jobs = self.db.query(Job).filter(Job.interview_id.in_(interview_ids)).all()
        pains = self.db.query(PainPoint).filter(PainPoint.interview_id.in_(interview_ids)).all()
        workarounds = self.db.query(Workaround).filter(Workaround.interview_id.in_(interview_ids)).all()
        opportunities = self.db.query(Opportunity).filter(Opportunity.interview_id.in_(interview_ids)).all()

        # Build tree from opportunities, grouping by related jobs
        job_groups: dict[str, dict] = {}

        for job in jobs:
            job_groups[job.id] = {
                "name": job.statement,
                "type": "job",
                "importance": job.importance,
                "satisfaction": job.satisfaction,
                "children": [],
            }

        # Attach pains to jobs
        for pain in pains:
            node = {
                "name": pain.description,
                "type": "pain_point",
                "severity": pain.severity,
                "children": [],
            }
            if pain.related_job_id and pain.related_job_id in job_groups:
                job_groups[pain.related_job_id]["children"].append(node)
            else:
                # Unlinked pains go under a catch-all
                job_groups.setdefault("_unlinked", {
                    "name": "Other Findings",
                    "type": "group",
                    "children": [],
                })["children"].append(node)

        # Attach opportunities with scores
        for opp in sorted(opportunities, key=lambda o: o.opportunity_score, reverse=True):
            node = {
                "name": opp.description,
                "type": "opportunity",
                "score": opp.opportunity_score,
                "importance": opp.importance_score,
                "satisfaction": opp.satisfaction_score,
            }
            if opp.related_job_id and opp.related_job_id in job_groups:
                job_groups[opp.related_job_id]["children"].append(node)
            else:
                job_groups.setdefault("_unlinked", {
                    "name": "Other Findings",
                    "type": "group",
                    "children": [],
                })["children"].append(node)

        root = {
            "name": "Opportunity Solution Tree",
            "type": "root",
            "children": list(job_groups.values()),
        }
        return root

    def get_top_opportunities(self, project_id: str, limit: int = 10) -> list[dict]:
        """Get the top-scored opportunities across all interviews in a project."""
        interviews = (
            self.db.query(Interview)
            .filter(Interview.project_id == project_id, Interview.status == "analyzed")
            .all()
        )
        interview_ids = [i.id for i in interviews]

        opportunities = (
            self.db.query(Opportunity)
            .filter(Opportunity.interview_id.in_(interview_ids))
            .order_by(Opportunity.opportunity_score.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": o.id,
                "description": o.description,
                "opportunity_score": o.opportunity_score,
                "importance_score": o.importance_score,
                "satisfaction_score": o.satisfaction_score,
                "market_size_indicator": o.market_size_indicator,
                "interview_id": o.interview_id,
            }
            for o in opportunities
        ]
