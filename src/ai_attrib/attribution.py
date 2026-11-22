"""Decide whether a commit *declares* AI involvement.

The only reliable, git-native signal is what the author chose to write in the
commit message. We therefore measure **declared** attribution, which is a lower
bound: plenty of AI-assisted commits carry no trailer at all.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Pattern, Sequence

from .model import Commit

_VENDORS = (
    "claude|copilot|codex|gpt|cursor|aider|qoder|gemini|windsurf|devin|"
    "cline|continue|multica|chatgpt|llm|agent"
)

DEFAULT_PATTERNS: Sequence[str] = (
    # Co-authored-by: Claude <noreply@anthropic.com>
    rf"co-authored-by:.*\b({_VENDORS})\b",
    # Generated-by: copilot / Assisted-by: claude
    rf"\b(generated|assisted|written|authored)-by:\s*[^\n]*\b({_VENDORS})\b",
    # A trailer that names an agent id, e.g. "Co-authored-by: multica-agent"
    r"co-authored-by:.*\bagent\b",
    # Explicit marker some teams use
    r"\[ai(-assisted|-generated)?\]",
    r"🤖",
)

DEFAULT_AI_AUTHORS: Sequence[str] = (
    "copilot",
    "claude",
    "cursor",
    "aider",
    "devin",
    "codex",
)


def compile_patterns(extra: Iterable[str] = ()) -> List[Pattern[str]]:
    """Compile default patterns plus any user-supplied regexes."""
    patterns: List[Pattern[str]] = []
    for raw in list(DEFAULT_PATTERNS) + list(extra):
        patterns.append(re.compile(raw, re.IGNORECASE))
    return patterns


def is_ai_commit(commit: Commit, patterns: Sequence[Pattern[str]]) -> bool:
    """True when the commit message matches any attribution pattern."""
    text = commit.message
    return any(p.search(text) for p in patterns)


def mark(commits: Sequence[Commit], patterns: Sequence[Pattern[str]]) -> List[Commit]:
    """Set ``is_ai`` on every commit and return the same list."""
    for commit in commits:
        commit.is_ai = is_ai_commit(commit, patterns)
    return list(commits)


def describe_patterns() -> List[str]:
    """Human-readable list used in reports, so the口径 is never implicit."""
    return list(DEFAULT_PATTERNS)
