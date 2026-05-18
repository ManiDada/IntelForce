"""Gate decision logic."""
from __future__ import annotations

AUTO_SEND_EV = 82.0
AUTO_SEND_CONFIDENCE = 85.0
REVIEW_EV = 70.0


def gate_decision(
    ev: float, confidence: float, mode: str = "manual"
) -> tuple[str, str]:
    """
    Returns (decision, reason).

    Decisions:
      AUTO_SEND_ELIGIBLE — high EV + high confidence + mode=auto_high_conf
      REVIEW_AND_SEND    — qualified for human review
      HOLD               — below threshold
    """
    if _has_red_flags_in_call_context():
        return "HOLD", "red flags detected"

    if (
        mode == "auto_high_conf"
        and ev >= AUTO_SEND_EV
        and confidence >= AUTO_SEND_CONFIDENCE
    ):
        return "AUTO_SEND_ELIGIBLE", "high EV + high confidence"

    if ev >= REVIEW_EV:
        return "REVIEW_AND_SEND", "qualified for human review"

    return "HOLD", f"EV {ev:.1f} below threshold {REVIEW_EV}"


def _has_red_flags_in_call_context() -> bool:
    return False


def gate_decision_with_job(
    ev: float, confidence: float, job: dict, mode: str = "manual"
) -> tuple[str, str]:
    from .scoring import _has_red_flags
    if _has_red_flags(job):
        return "HOLD", "red flags in job description"
    if job.get("client_spent") in (None, "", "$0"):
        if not job.get("client_verified"):
            return "HOLD", "new unverified client with no spend history"
    return gate_decision(ev, confidence, mode)
