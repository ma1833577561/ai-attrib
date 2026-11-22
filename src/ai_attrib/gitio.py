"""Thin, dependency-free layer over the ``git`` CLI.

Everything here is read-only. No GitLab/GitHub API, no credentials, no network.
"""

from __future__ import annotations

import os
import subprocess
from typing import Dict, Iterator, List, Optional, Tuple

from .model import Commit

RECORD = "\x1e"
FIELD = "\x1f"


class GitError(RuntimeError):
    """Raised when a git invocation fails."""


def git(repo: str, *args: str) -> str:
    """Run a git command inside ``repo`` and return stdout."""
    proc = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True,
        text=True,
        errors="replace",
    )
    if proc.returncode != 0:
        raise GitError(
            f"git {' '.join(args[:4])} failed in {repo}:\n{proc.stderr.strip()}"
        )
    return proc.stdout


def is_repo(path: str) -> bool:
    """True when ``path`` is inside a git work tree."""
    if not os.path.isdir(path):
        return False
    try:
        out = git(path, "rev-parse", "--is-inside-work-tree").strip()
    except GitError:
        return False
    return out == "true"


def head_sha(repo: str) -> str:
    try:
        return git(repo, "rev-parse", "--short", "HEAD").strip()
    except GitError:
        return ""


def _is_numstat(line: str) -> bool:
    parts = line.split("\t")
    if len(parts) != 3:
        return False
    added, deleted = parts[0], parts[1]
    return (added.isdigit() or added == "-") and (deleted.isdigit() or deleted == "-")


def _split_record(chunk: str) -> Tuple[List[str], List[str]]:
    """Split one ``git log`` record into (header lines, numstat lines).

    The commit body may contain newlines, so the split cannot be done forward.
    Numstat lines are already at the tail of the record: walk backwards until a
    line stops looking like one.
    """
    lines = chunk.split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    cut = len(lines)
    while cut > 0 and _is_numstat(lines[cut - 1]):
        cut -= 1
    return lines[:cut], lines[cut:]


def read_commits(
    repo: str,
    rev: str = "HEAD",
    since: Optional[str] = None,
    until: Optional[str] = None,
    merges: bool = False,
) -> List[Commit]:
    """Read commits (default: no merges) with their numstat totals."""
    fmt = RECORD + FIELD.join(["%H", "%ad", "%an", "%s", "%b"])
    args = [
        "log",
        rev,
        "--merges" if merges else "--no-merges",
        "--date=short",
        "--format=" + fmt,
        "--numstat",
    ]
    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")

    commits: List[Commit] = []
    for chunk in git(repo, *args).split(RECORD):
        if not chunk.strip():
            continue
        header_lines, numstat_lines = _split_record(chunk)
        if not header_lines:
            continue
        parts = header_lines[0].split(FIELD)
        if len(parts) < 4:
            continue
        first_body_line = FIELD.join(parts[4:]) if len(parts) > 4 else ""
        body = "\n".join([first_body_line] + header_lines[1:]).rstrip("\n")
        files = 0
        insertions = 0
        deletions = 0
        paths: List[str] = []
        for line in numstat_lines:
            added, deleted, path = line.split("\t")
            files += 1
            paths.append(path)
            if added.isdigit():
                insertions += int(added)
            if deleted.isdigit():
                deletions += int(deleted)
        commits.append(
            Commit(
                sha=parts[0],
                date=parts[1],
                author=parts[2],
                subject=parts[3],
                body=body,
                files=files,
                insertions=insertions,
                deletions=deletions,
                paths=tuple(paths),
            )
        )
    return commits


def iter_added_lines(
    repo: str,
    rev: str = "HEAD",
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> Iterator[Tuple[str, List[str]]]:
    """Yield ``(sha, added_lines)`` for every commit in range.

    Uses ``-U0`` so only genuinely added lines are inspected. This reads the
    full patch stream, so it is opt-in behind ``--signals``.
    """
    args = ["log", rev, "--no-merges", "-p", "-U0", "--format=" + RECORD + "%H"]
    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")

    current: Optional[str] = None
    added: List[str] = []
    for line in git(repo, *args).split("\n"):
        if line.startswith(RECORD):
            if current is not None:
                yield current, added
            current = line[1:].strip()
            added = []
        elif current and line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
    if current is not None:
        yield current, added


def commit_dates(repo: str) -> Tuple[str, str]:
    """Return (first commit date, last commit date) as YYYY-MM-DD."""
    raw = git(repo, "log", "--reverse", "--date=short", "--format=%ad").split()
    if not raw:
        return "", ""
    return raw[0], raw[-1]
