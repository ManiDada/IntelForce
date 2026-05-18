"""Canonical data shapes for the pipeline."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Job:
    id: str
    platform: str
    title: str
    description: str = ""
    budget: str = ""
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    budget_type: str = "fixed"
    experience_level: str = ""
    duration: str = ""
    client_rating: Optional[float] = None
    client_spent: str = ""
    client_location: str = ""
    proposals_count: int = 0
    skills: str = ""
    posted_time: str = ""
    url: str = ""
    status: str = "discovered"
    score: Optional[float] = None
    score_breakdown: Optional[dict] = None
    raw_data: Optional[dict] = None

    @classmethod
    def from_dict(cls, d: dict) -> "Job":
        return cls(
            id=d.get("id", ""),
            platform=d.get("platform", "upwork"),
            title=d.get("title", ""),
            description=d.get("description", ""),
            budget=d.get("budget", ""),
            budget_min=d.get("budget_min"),
            budget_max=d.get("budget_max"),
            budget_type=d.get("budget_type", "fixed"),
            experience_level=d.get("experience_level", ""),
            duration=d.get("duration", ""),
            client_rating=d.get("client_rating"),
            client_spent=d.get("client_spent", ""),
            client_location=d.get("client_location", ""),
            proposals_count=int(d.get("proposals_count") or 0),
            skills=d.get("required_skills", d.get("skills", "")),
            posted_time=d.get("posted_time", ""),
            url=d.get("url", ""),
            status=d.get("status", "discovered"),
            score=d.get("score"),
            raw_data=d,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "platform": self.platform,
            "title": self.title,
            "description": self.description,
            "budget": self.budget,
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "budget_type": self.budget_type,
            "experience_level": self.experience_level,
            "duration": self.duration,
            "client_rating": self.client_rating,
            "client_spent": self.client_spent,
            "client_location": self.client_location,
            "proposals_count": self.proposals_count,
            "skills": self.skills,
            "posted_time": self.posted_time,
            "url": self.url,
            "status": self.status,
            "score": self.score,
        }


@dataclass
class ProposalDraft:
    job_id: str
    score: float
    confidence: float
    gate_decision: str
    gate_reason: str
    proposal_text: str
    skill_score: float = 0.0
    win_probability: float = 0.0
    ev: float = 0.0

    @property
    def filename(self) -> str:
        from datetime import date
        safe_id = self.job_id.replace("/", "_").replace(":", "_")
        return f"{date.today().isoformat()}_{safe_id}.md"
