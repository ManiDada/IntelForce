"""Tests for the gate decision logic."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.approval import gate_decision, gate_decision_with_job


def test_review_and_send_at_ev70():
    decision, reason = gate_decision(70.0, 75.0, "manual")
    assert decision == "REVIEW_AND_SEND"


def test_hold_below_ev70():
    decision, reason = gate_decision(65.0, 80.0, "manual")
    assert decision == "HOLD"


def test_auto_send_requires_auto_mode():
    # In manual mode, even high EV+confidence = REVIEW_AND_SEND, not AUTO
    decision, reason = gate_decision(90.0, 90.0, "manual")
    assert decision == "REVIEW_AND_SEND"


def test_auto_send_eligible_in_auto_mode():
    decision, reason = gate_decision(85.0, 90.0, "auto_high_conf")
    assert decision == "AUTO_SEND_ELIGIBLE"


def test_auto_send_requires_high_confidence():
    decision, reason = gate_decision(85.0, 80.0, "auto_high_conf")
    assert decision == "REVIEW_AND_SEND"


def test_auto_send_requires_high_ev():
    decision, reason = gate_decision(80.0, 90.0, "auto_high_conf")
    assert decision == "REVIEW_AND_SEND"


def test_red_flag_job_always_hold():
    job = {
        "title": "Cheapest option needed",
        "description": "cheapest developer ASAP",
        "required_skills": "python",
        "proposals_count": 30,
    }
    decision, reason = gate_decision_with_job(85.0, 90.0, job, "auto_high_conf")
    assert decision == "HOLD"
    assert "red flags" in reason.lower()


def test_gate_returns_tuple():
    result = gate_decision(72.0, 75.0)
    assert isinstance(result, tuple)
    assert len(result) == 2
