"""Extract a feature description from a section of a specification document.

Supports two operations:
  extract_section()          — parse a markdown doc and return the raw text
                               under a given heading
  extract_feature_from_doc() — use Claude to turn that section into a concise
                               feature description suitable for agent-design init
"""

import os
import re
import subprocess
from pathlib import Path


def extract_section(doc_path: Path, section_header: str) -> str:
    """Extract raw content under a markdown heading.

    Finds the first heading whose text matches section_header (case-sensitive,
    any heading level #–######). Returns all content up to the next heading
    at the same or higher level.

    Args:
        doc_path: Path to the markdown document.
        section_header: Exact heading text to find (without the # prefix).

    Returns:
        Raw markdown text of the section body (stripped).

    Raises:
        ValueError: If the section header is not found in the document.
    """
    content = doc_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Match any heading level whose text equals section_header
    header_re = re.compile(r"^(#{1,6})\s+" + re.escape(section_header) + r"\s*$")

    start_idx: int | None = None
    header_level: int = 0

    for i, line in enumerate(lines):
        m = header_re.match(line)
        if m:
            start_idx = i + 1
            header_level = len(m.group(1))
            break

    if start_idx is None:
        raise ValueError(
            f"Section '{section_header}' not found in {doc_path}.\n"
            f"Check that the heading text matches exactly (case-sensitive, no leading #)."
        )

    # Collect lines until the next heading at the same or higher level
    section_lines: list[str] = []
    for line in lines[start_idx:]:
        m = re.match(r"^(#{1,6})\s+", line)
        if m and len(m.group(1)) <= header_level:
            break
        section_lines.append(line)

    return "\n".join(section_lines).strip()


_EXTRACTION_PROMPT = """\
The following is a section from a specification document.

Extract a concise feature description (3–6 sentences) suitable for use as an
engineering feature request. Cover: what needs to be built, key requirements,
and success criteria. Write in plain, direct language — no markdown formatting,
no bullet points, no headers. Just prose.

Document: {doc_name}
Section: {section_header}

---
{section_content}
---

Write only the feature description. No preamble, no explanation.
"""


def extract_feature_from_doc(doc_path: Path, section_header: str) -> str:
    """Use Claude to extract a concise feature description from a doc section.

    Makes a single non-interactive claude --print call. Reads the Anthropic
    API key from the ANTHROPIC_API_KEY environment variable or ~/.anthropic_api_key.

    Args:
        doc_path: Path to the markdown specification document.
        section_header: Heading text identifying the section to extract from.

    Returns:
        A concise feature description string.

    Raises:
        ValueError: If the section is not found.
        RuntimeError: If Claude exits non-zero.
    """
    section_content = extract_section(doc_path, section_header)

    prompt = _EXTRACTION_PROMPT.format(
        doc_name=doc_path.name,
        section_header=section_header,
        section_content=section_content,
    )

    env = os.environ.copy()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        key_file = Path.home() / ".anthropic_api_key"
        if key_file.exists():
            api_key = key_file.read_text().strip()
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    # If no key found, proceed without setting it — claude may be authenticated
    # via `claude login` (OAuth session in ~/.claude.json).

    result = subprocess.run(
        [
            "claude",
            "--print",
            "--dangerously-skip-permissions",
            "--strict-mcp-config",
            "--mcp-config",
            '{"mcpServers":{}}',
        ],
        input=prompt.encode(),
        capture_output=True,
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Claude exited with code {result.returncode}.\nstderr: {result.stderr.decode().strip()}")

    return result.stdout.decode().strip()
