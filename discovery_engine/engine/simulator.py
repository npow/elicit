"""Synthetic interview simulator — persona generation and chat."""

import json

from sqlalchemy.orm import Session

from discovery_engine.llm.client import complete, chat, render_prompt
from discovery_engine.llm.parsers import parse_llm_list, parse_llm_output
from discovery_engine.models.project import Project
from discovery_engine.models.persona import SyntheticPersona, SyntheticSession
from discovery_engine.schemas.persona import PersonaExtracted
from discovery_engine.config import settings


class SimulatorEngine:
    """Generate synthetic personas and run simulated interviews."""

    def __init__(self, db: Session):
        self.db = db

    async def generate_personas(
        self,
        project_id: str,
        count: int = 3,
        is_adversarial: bool = False,
    ) -> list[SyntheticPersona]:
        """Generate synthetic personas for a project."""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Gather existing insights for context
        existing_insights = ""
        from discovery_engine.models.extraction import Job, PainPoint
        from discovery_engine.models.interview import Interview

        interviews = self.db.query(Interview).filter(Interview.project_id == project_id).all()
        if interviews:
            interview_ids = [i.id for i in interviews]
            jobs = self.db.query(Job).filter(Job.interview_id.in_(interview_ids)).all()
            pains = self.db.query(PainPoint).filter(PainPoint.interview_id.in_(interview_ids)).all()
            existing_insights = json.dumps({
                "jobs": [j.statement for j in jobs[:10]],
                "pains": [p.description for p in pains[:10]],
            })

        prompt = render_prompt(
            "synthetic_persona_generation.txt",
            project_description=project.description,
            target_customer=project.target_customer,
            existing_insights=existing_insights,
            count=count,
        )
        raw = await complete(prompt, tier="primary", task_type="simulation")
        parsed = parse_llm_list(raw, PersonaExtracted)

        personas = []
        for item in parsed:
            persona = SyntheticPersona(
                project_id=project_id,
                name=item.name,
                role=item.role,
                company_type=item.company_type,
                background=item.background,
                goals=item.goals,
                frustrations=item.frustrations,
                current_tools=item.current_tools,
                behavioral_traits=item.behavioral_traits,
                is_adversarial=is_adversarial,
                adversarial_traits=[] if not is_adversarial else ["skeptical", "evasive", "challenging"],
                model_used=settings.primary_model,
            )
            self.db.add(persona)
            personas.append(persona)

        self.db.commit()
        return personas

    async def start_session(self, persona_id: str) -> SyntheticSession:
        """Start a new synthetic interview session."""
        persona = self.db.query(SyntheticPersona).filter(SyntheticPersona.id == persona_id).first()
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")

        session = SyntheticSession(
            persona_id=persona_id,
            messages=[],
            status="active",
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    async def send_message(self, session_id: str, user_message: str) -> dict:
        """Send a message in a synthetic interview and get a response.

        Also validates the user's question against Mom Test rules.
        """
        session = self.db.query(SyntheticSession).filter(SyntheticSession.id == session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")
        if session.status != "active":
            raise ValueError("Session is not active")

        persona = self.db.query(SyntheticPersona).filter(SyntheticPersona.id == session.persona_id).first()
        if not persona:
            raise ValueError(f"Persona {session.persona_id} not found")

        # Build system prompt
        template = "adversarial_persona_system.txt" if persona.is_adversarial else "synthetic_interview_system.txt"
        persona_data = {
            "name": persona.name,
            "role": persona.role,
            "company_type": persona.company_type,
            "background": persona.background,
            "goals": persona.goals,
            "frustrations": persona.frustrations,
            "current_tools": persona.current_tools,
            "behavioral_traits": persona.behavioral_traits,
        }
        system_prompt = render_prompt(template, persona=json.dumps(persona_data, indent=2))

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        for msg in session.messages:
            messages.append(msg)
        messages.append({"role": "user", "content": user_message})

        # Get persona response
        response = await chat(messages, tier="primary", task_type="simulation")

        # Validate question against Mom Test
        mom_test_result = await self._validate_mom_test(user_message)

        # Update session
        updated_messages = list(session.messages) if session.messages else []
        updated_messages.append({"role": "user", "content": user_message})
        updated_messages.append({"role": "assistant", "content": response})
        session.messages = updated_messages

        if mom_test_result and not mom_test_result.get("is_valid", True):
            violations = list(session.mom_test_violations or [])
            violations.append({
                "question": user_message,
                "violations": mom_test_result.get("violations", []),
                "improved_version": mom_test_result.get("improved_version", ""),
            })
            session.mom_test_violations = violations

        self.db.commit()

        return {
            "response": response,
            "mom_test_validation": mom_test_result,
        }

    async def end_session(self, session_id: str) -> SyntheticSession:
        """End a session, compute quality score, and persist."""
        session = self.db.query(SyntheticSession).filter(SyntheticSession.id == session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        messages = session.messages or []
        user_turns = [m for m in messages if m.get("role") == "user"]
        violations = session.mom_test_violations or []

        turn_count = len(user_turns)
        violation_count = len(violations)

        if turn_count == 0:
            session.session_quality_score = 0.0
        else:
            # Engagement: more turns (up to 10) is better practice.
            engagement = min(1.0, turn_count / 10.0)
            # Compliance: fewer violations per question is better.
            violation_rate = violation_count / turn_count
            compliance = max(0.0, 1.0 - violation_rate)
            session.session_quality_score = round(0.35 * engagement + 0.65 * compliance, 2)
        session.status = "completed"
        self.db.commit()
        return session

    async def _validate_mom_test(self, question: str) -> dict:
        """Validate a question against Mom Test rules."""
        prompt = render_prompt(
            "mom_test_validator.txt",
            question=question,
            context="synthetic interview",
        )
        try:
            raw = await complete(prompt, tier="cheap", task_type="coaching")
            from pydantic import BaseModel

            class MomTestResult(BaseModel):
                is_valid: bool = True
                violations: list = []
                improved_version: str = ""
                explanation: str = ""

            return parse_llm_output(raw, MomTestResult).model_dump()
        except Exception:
            return {"is_valid": True, "violations": [], "improved_version": "", "explanation": ""}
