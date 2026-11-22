"""Shared helpers for the test suite (stdlib unittest only, no fixtures repo)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def git(repo: str, *args: str, env: Optional[Dict[str, str]] = None) -> str:
    proc = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return proc.stdout


def init_repo(root: str) -> str:
    os.makedirs(root, exist_ok=True)
    git(root, "init", "-q", "-b", "main")
    return root


def commit(
    repo: str,
    message: str,
    files: Dict[str, str],
    day: str = "2025-01-01",
    author: str = "tester",
) -> str:
    """Write files, stage everything, and commit with a pinned author date."""
    for path, content in files.items():
        target = os.path.join(repo, path)
        os.makedirs(os.path.dirname(target) or repo, exist_ok=True)
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(content)
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": author,
            "GIT_AUTHOR_EMAIL": "tester@example.com",
            "GIT_COMMITTER_NAME": author,
            "GIT_COMMITTER_EMAIL": "tester@example.com",
            "GIT_AUTHOR_DATE": f"{day}T10:00:00+00:00",
            "GIT_COMMITTER_DATE": f"{day}T10:00:00+00:00",
        }
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-gpg-sign", "-m", message, env=env)
    return git(repo, "rev-parse", "HEAD").strip()


def lines(count: int, prefix: str = "const x") -> str:
    return "".join(f"{prefix}{index} = {index};\n" for index in range(count))
