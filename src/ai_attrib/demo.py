"""Build a small, fully synthetic git repository used by ``ai-attrib demo``.

Nothing here comes from a real project: the point is a reproducible report that
contains no client, employer or personal data.
"""

from __future__ import annotations

import os
import random
import subprocess
from datetime import date, timedelta
from typing import Dict, List, Tuple

BASE_DAY = date(2025, 1, 6)

MODULES: Tuple[str, ...] = ("core", "api", "ui", "store", "auth")
KINDS: Tuple[str, ...] = ("feat", "fix", "fix", "refactor", "test", "docs", "chore")

AI_TRAILER = "Co-authored-by: Claude <noreply@anthropic.com>"
SUSPICIOUS = (
    "console.log('debug', value)",
    "const payload: any = response.body",
    "// TODO: handle the empty case",
    "try { run() } catch (e) {}",
    "setTimeout(() => retry(), 1000)",
)


def _git(repo: str, *args: str, env: Dict[str, str] | None = None) -> None:
    subprocess.run(
        ["git", "-C", repo, *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def _write(repo: str, path: str, content: str) -> None:
    target = os.path.join(repo, path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(content)


def _message(rng: random.Random, kind: str, module: str, ai: bool) -> str:
    subject = {
        "feat": f"feat({module}): add {rng.choice(['retry', 'cache', 'filter', 'batch'])} path",
        "fix": f"fix({module}): guard against empty response",
        "refactor": f"refactor({module}): split responsibility",
        "test": f"test({module}): cover the failure branch",
        "docs": f"docs({module}): describe the contract",
        "chore": f"chore({module}): bump internals",
    }[kind]
    if not ai:
        return subject
    return f"{subject}\n\nGenerated with assistance.\n\n{AI_TRAILER}"


def build_demo_repo(dest: str, seed: int = 42) -> str:
    """Create ``dest`` and fill it with a deterministic commit history."""
    rng = random.Random(seed)
    os.makedirs(dest, exist_ok=True)
    _git(dest, "init", "-q", "-b", "main")

    total = 84
    for index in range(total):
        day = BASE_DAY + timedelta(days=index * 2 + rng.randint(0, 1))
        module = MODULES[rng.randrange(len(MODULES))]
        kind = KINDS[rng.randrange(len(KINDS))]
        # The first third has no AI trailers: it acts as the baseline window.
        ai = index >= total // 3 and rng.random() < 0.55
        if ai:
            touched = 1 if rng.random() < 0.35 else rng.randint(2, 6)
        else:
            touched = 1 if rng.random() < 0.72 else rng.randint(2, 3)
        if kind == "docs":
            touched = 1

        for slot in range(touched):
            name = f"file_{rng.randint(1, 4)}.js"
            if kind == "docs":
                path = "docs/notes.md"
                body = f"- note {index}-{slot}\n"
            elif kind == "test":
                path = f"tests/{module}/case_{index}.test.js"
                body = "expect(true).toBe(true)\n"
            else:
                path = f"src/{module}/{name}"
                body = "".join(
                    f"const value{index}_{slot}_{n} = {rng.randint(1, 99)};\n"
                    for n in range(rng.randint(2, 12))
                )
                if rng.random() < 0.12:
                    body += rng.choice(SUSPICIOUS) + "\n"
            _write(dest, path, body)

        message = _message(rng, kind, module, ai)
        env = os.environ.copy()
        identity = {
            "GIT_AUTHOR_NAME": "demo-agent" if ai else "demo-human",
            "GIT_AUTHOR_EMAIL": "demo@example.com",
            "GIT_COMMITTER_NAME": "demo-agent" if ai else "demo-human",
            "GIT_COMMITTER_EMAIL": "demo@example.com",
            "GIT_AUTHOR_DATE": f"{day.isoformat()}T10:00:00+08:00",
            "GIT_COMMITTER_DATE": f"{day.isoformat()}T10:00:00+08:00",
        }
        env.update(identity)
        _git(dest, "add", "-A")
        _git(dest, "commit", "-q", "--no-gpg-sign", "-m", message, env=env)

    return dest


def demo_windows() -> Tuple[str, str, str, str]:
    """Return ``(baseline_since, baseline_until, since, until)`` for the demo."""
    return (
        (BASE_DAY + timedelta(days=8)).isoformat(),
        (BASE_DAY + timedelta(days=54)).isoformat(),
        (BASE_DAY + timedelta(days=56)).isoformat(),
        (BASE_DAY + timedelta(days=170)).isoformat(),
    )
