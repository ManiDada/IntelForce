"""Tests for the scoring model."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.scoring import score_job_dict, score_root, _has_red_flags


def test_high_skill_match_boosts_ev():
    job = {
        "title": "Python API integration",
        "required_skills": "python, api integration, automation",
        "proposals_count": 10,
        "budget_min": 500,
        "client_spent": "$5K+",
    }
    result = score_job_dict(job)
    assert result["ev"] >= 60
    assert result["skill_score"] >= 80


def test_low_competition_boosts_speed_score():
    job = {"required_skills": "python", "proposals_count": 3}
    result = score_job_dict(job)
    assert result["speed_score"] == 90.0
    assert result["win_probability"] > 90


def test_high_competition_reduces_win_probability():
    # At 80 proposals: 95 - min(80, 80*1.2=96) = 95 - 80 = 15 → max(10, 15) = 15.0
    job = {"required_skills": "python", "proposals_count": 80}
    result = score_job_dict(job)
    assert result["win_probability"] == 15.0
    # Floor of 10 only kicks in at extreme competition (>71 proposals reaching 80 cap)
    job2 = {"required_skills": "python", "proposals_count": 5}
    assert score_job_dict(job2)["win_probability"] > result["win_probability"]


def test_red_flag_cheapest_detected():
    job = {
        "title": "Simple task - cheapest option needed",
        "description": "Need cheapest developer ASAP",
        "required_skills": "python",
        "proposals_count": 30,
    }
    result = score_job_dict(job)
    assert result["red_flags"] is True


def test_no_red_flags_on_clean_job():
    job = {
        "title": "Build n8n workflow for CRM sync",
        "description": "Professional automation project with clear requirements.",
        "required_skills": "n8n, api",
        "proposals_count": 5,
    }
    result = score_job_dict(job)
    assert result["red_flags"] is False


def test_root_scorer_budget_component():
    job_high = {"required_skills": "python", "budget_min": 1500, "proposals_count": 5}
    job_low = {"required_skills": "python", "budget_min": 150, "proposals_count": 5}
    score_high, _ = score_root(job_high)
    score_low, _ = score_root(job_low)
    assert score_high > score_low


def test_ev_formula_components():
    job = {
        "required_skills": "python, api integration",
        "proposals_count": 8,
        "budget_min": 600,
        "client_spent": "$10K+",
    }
    r = score_job_dict(job)
    expected_ev = round(0.5 * r["job_score"] + 0.3 * r["win_probability"] + 0.2 * r["speed_score"], 1)
    # Allow for bonuses
    assert r["ev"] >= expected_ev - 5


def test_all_result_fields_present():
    job = {"required_skills": "python", "proposals_count": 10}
    result = score_job_dict(job)
    for key in ["skill_score", "job_score", "win_probability", "speed_score", "ev", "red_flags"]:
        assert key in result
