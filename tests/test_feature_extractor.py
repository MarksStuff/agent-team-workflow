"""Tests for feature_extractor — section parsing and validation.

The extract_feature_from_doc() function (which calls Claude) is not tested here
since it requires a live API key. Only the pure parsing logic is unit tested.
"""

import tempfile
from pathlib import Path

import pytest

from agent_design.feature_extractor import extract_section

SAMPLE_DOC = """\
# Project Overview

Some intro text.

## Phase 1 — Foundation

This is phase 1 content.
It has multiple lines.

## Phase 2 — Build

This is phase 2 content.

### Sub-section

Sub-section content.

## Phase 3 — Deploy

Phase 3 content.
"""


def _write_doc(content: str) -> Path:
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as tmp:
        tmp.write(content)
        return Path(tmp.name)


def test_extract_section_basic() -> None:
    doc = _write_doc(SAMPLE_DOC)
    result = extract_section(doc, "Phase 1 — Foundation")
    assert "This is phase 1 content." in result
    assert "It has multiple lines." in result
    # Should not bleed into Phase 2
    assert "Phase 2" not in result


def test_extract_section_includes_subsections() -> None:
    """Content under sub-headings is included until a same-level heading."""
    doc = _write_doc(SAMPLE_DOC)
    result = extract_section(doc, "Phase 2 — Build")
    assert "This is phase 2 content." in result
    assert "Sub-section" in result
    assert "Sub-section content." in result
    # Should stop at Phase 3
    assert "Phase 3" not in result


def test_extract_section_last_section() -> None:
    """Last section in doc has no following heading — should include all remaining content."""
    doc = _write_doc(SAMPLE_DOC)
    result = extract_section(doc, "Phase 3 — Deploy")
    assert "Phase 3 content." in result


def test_extract_section_not_found() -> None:
    doc = _write_doc(SAMPLE_DOC)
    with pytest.raises(ValueError, match="not found"):
        extract_section(doc, "Phase 99 — Missing")


def test_extract_section_case_sensitive() -> None:
    doc = _write_doc(SAMPLE_DOC)
    with pytest.raises(ValueError, match="not found"):
        extract_section(doc, "phase 1 — foundation")  # lowercase


def test_extract_section_top_level_heading() -> None:
    """A # heading includes all ## subsections until the next # heading."""
    doc = _write_doc(SAMPLE_DOC)
    result = extract_section(doc, "Project Overview")
    assert "Some intro text." in result
    # ## headings are sub-sections of #, so they're included
    assert "Phase 1" in result


def test_extract_section_strips_output() -> None:
    doc = _write_doc(SAMPLE_DOC)
    result = extract_section(doc, "Phase 1 — Foundation")
    assert not result.startswith("\n")
    assert not result.endswith("\n")
