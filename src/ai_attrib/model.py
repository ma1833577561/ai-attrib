"""Data model shared by the collector, the metrics and the renderers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Tuple

# "feat(api): ..." / "fix!: ..." / "docs: ..." -> feat / fix / docs
_TYPE_RE = re.compile(r"^\s*([A-Za-z]+)(\([^)]*\))?(!)?\s*[:：]")


def commit_type(subject: str) -> str:
    """Conventional-commit type, or ``other`` when the subject does not follow it."""
    match = _TYPE_RE.match(subject)
    return match.group(1).lower() if match else "other"


@dataclass
class Commit:
    """One non-merge commit with its numstat totals."""

    sha: str
    date: str  # YYYY-MM-DD, author date
    author: str
    subject: str
    body: str = ""
    files: int = 0
    insertions: int = 0
    deletions: int = 0
    paths: Tuple[str, ...] = ()
    is_ai: bool = False
    signals: Dict[str, int] = field(default_factory=dict)

    @property
    def lines(self) -> int:
        return self.insertions + self.deletions

    @property
    def kind(self) -> str:
        return commit_type(self.subject)

    @property
    def message(self) -> str:
        return f"{self.subject}\n{self.body}"
