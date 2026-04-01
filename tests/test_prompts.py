"""Tests for prompts module — build_* functions with dynamic specialists."""

from agent_design.prompts import build_feedback_start, build_impl_start, build_review_start

SPECIALISTS = ["architect", "developer", "qa_engineer", "tdd_focused_engineer"]


def test_build_impl_start_includes_specialists() -> None:
    msg = build_impl_start("Add search feature", SPECIALISTS)
    assert "architect, developer, qa_engineer, tdd_focused_engineer" in msg
    assert "Add search feature" in msg


def test_build_impl_start_resume_includes_specialists() -> None:
    msg = build_impl_start("Add search feature", SPECIALISTS, is_resume=True)
    assert "architect, developer, qa_engineer, tdd_focused_engineer" in msg
    assert "resume" in msg.lower()


def test_build_review_start_includes_specialists() -> None:
    msg = build_review_start("Add search feature", SPECIALISTS)
    assert "architect, developer, qa_engineer, tdd_focused_engineer" in msg
    assert "Add search feature" in msg


def test_build_feedback_start_includes_specialists() -> None:
    msg = build_feedback_start(2, SPECIALISTS, "Add search feature")
    assert "architect, developer, qa_engineer, tdd_focused_engineer" in msg
    assert "round 2" in msg.lower()


def test_build_impl_start_empty_specialists() -> None:
    msg = build_impl_start("Feature X", [])
    assert "none discovered" in msg


def test_build_review_start_empty_specialists() -> None:
    msg = build_review_start("Feature X", [])
    assert "none discovered" in msg


def test_build_feedback_start_empty_specialists() -> None:
    msg = build_feedback_start(1, [], "Feature X")
    assert "none discovered" in msg
