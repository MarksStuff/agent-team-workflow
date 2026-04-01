"""Tests for launcher module — discover_agents() and session helpers."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from agent_design.launcher import _EM_AGENT, discover_agents


def _make_agents_dir(names: list[str]) -> Path:
    """Create a temp agents dir with the given .md file stems."""
    d = Path(tempfile.mkdtemp())
    for name in names:
        (d / f"{name}.md").touch()
    return d


def test_discover_agents_returns_sorted_names() -> None:
    agents_dir = _make_agents_dir(["qa_engineer", "architect", "developer", "tdd_focused_engineer"])
    with patch("agent_design.launcher._AGENTS_DIR", agents_dir):
        result = discover_agents()
    assert result == ["architect", "developer", "qa_engineer", "tdd_focused_engineer"]


def test_discover_agents_excludes_eng_manager() -> None:
    agents_dir = _make_agents_dir(["eng_manager", "architect", "developer"])
    with patch("agent_design.launcher._AGENTS_DIR", agents_dir):
        result = discover_agents()
    assert _EM_AGENT not in result
    assert "architect" in result
    assert "developer" in result


def test_discover_agents_missing_dir_returns_empty() -> None:
    nonexistent = Path("/tmp/does-not-exist-agents-xyz")
    with patch("agent_design.launcher._AGENTS_DIR", nonexistent):
        result = discover_agents()
    assert result == []


def test_discover_agents_ignores_non_md_files() -> None:
    agents_dir = _make_agents_dir(["architect"])
    (agents_dir / "README.txt").touch()
    (agents_dir / "config.json").touch()
    with patch("agent_design.launcher._AGENTS_DIR", agents_dir):
        result = discover_agents()
    assert result == ["architect"]
