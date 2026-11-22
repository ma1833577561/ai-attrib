"""Aggregate metrics over a set of commits.

Everything is computed from ``git log`` output only, so the same code path works
on any repository (GitHub, GitLab, Gerrit, a bare local clone).
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import date
from typing import Dict, Iterable, List, Optional, Sequence

from .model import Commit

TEST_RE = re.compile(r"(^|/)(__tests__|tests?|spec|e2e)/|\.(test|spec)\.[cm]?[jt]sx?$")
DOC_RE = re.compile(r"(^|/)(docs?|documentation)/|\.(md|mdx|rst|adoc|txt)$")
SOURCE_ROOTS = {"src", "lib", "app", "apps", "packages", "internal"}

SIGNAL_PATTERNS: Dict[str, "re.Pattern[str]"] = {
    "console.log": re.compile(r"console\.(log|debug)\("),
    "eslint-disable": re.compile(r"eslint-disable"),
    "ts-ignore": re.compile(r"@ts-(ignore|nocheck|expect-error)"),
    "as-any": re.compile(r"\bas\s+any\b"),
    "empty-catch": re.compile(r"catch\s*(\([^)]*\))?\s*\{\s*\}"),
    "catch-console": re.compile(r"catch\s*(\([^)]*\))?\s*\{\s*console\.(log|error|warn)"),
    "todo-fixme": re.compile(r"\b(TODO|FIXME|XXX)\b"),
    "debugger": re.compile(r"\bdebugger\b"),
    "python-any": re.compile(r":\s*Any\b"),
}


def percentile(values: Sequence[float], q: float) -> float:
    """Nearest-rank percentile (q in 0..1). Returns 0 for an empty input."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1))
    return ordered[rank]


def module_of(path: str, depth: int = 2) -> str:
    """Collapse a file path to a coarse module key.

    ``src/views/finance/detail.tsx`` -> ``src/views/finance`` with depth=3, and
    ``src/views`` with depth=2. Source roots get one extra level so that the
    whole tree does not collapse into a single module.
    """
    parts = path.split("/")
    if len(parts) <= 1:
        return parts[0]
    if parts[0] in SOURCE_ROOTS and len(parts) > depth:
        return "/".join(parts[: depth + 1])
    return "/".join(parts[:depth])


def _pct(count: int, total: int) -> float:
    return round(100.0 * count / total, 1) if total else 0.0


def rework_rate(commits: Sequence[Commit], window_days: int = 14) -> float:
    """Share of ``fix`` commits followed by another ``fix`` on the same file.

    "Followed" means a strictly later fix, within ``window_days``, touching at
    least one of the same paths. It is a proxy for rework, not proof of it.
    """
    fixes = [c for c in commits if c.kind == "fix"]
    if not fixes:
        return 0.0
    per_file: Dict[str, List[tuple]] = defaultdict(list)
    for commit in fixes:
        for path in commit.paths:
            per_file[path].append((commit.date, commit.sha))

    hits = 0
    for commit in fixes:
        current = date.fromisoformat(commit.date)
        reworked = False
        for path in commit.paths:
            for when, sha in per_file[path]:
                if sha == commit.sha:
                    continue
                delta = (date.fromisoformat(when) - current).days
                if 0 < delta <= window_days:
                    reworked = True
                    break
            if reworked:
                break
        hits += int(reworked)
    return _pct(hits, len(fixes))


def summarize(
    commits: Sequence[Commit],
    depth: int = 2,
    total_for_share: Optional[int] = None,
) -> Dict[str, object]:
    """Compute the scalar metric block for a group of commits."""
    n = len(commits)
    if n == 0:
        return {"commits": 0}

    files = [c.files for c in commits]
    lines = [c.lines for c in commits]
    modules = [len({module_of(p, depth) for p in c.paths}) for c in commits]
    kinds = Counter(c.kind for c in commits)

    return {
        "commits": n,
        "share_pct": _pct(n, total_for_share or n),
        "authors": len({c.author for c in commits}),
        "files_median": percentile(files, 0.5),
        "files_p90": percentile(files, 0.9),
        "files_max": max(files),
        "lines_median": percentile(lines, 0.5),
        "lines_p90": percentile(lines, 0.9),
        "large_commit_pct": _pct(sum(1 for f in files if f > 10), n),
        "modules_median": percentile(modules, 0.5),
        "cross3_module_pct": _pct(sum(1 for m in modules if m > 3), n),
        "test_touch_pct": _pct(
            sum(1 for c in commits if any(TEST_RE.search(p) for p in c.paths)), n
        ),
        "docs_only_pct": _pct(
            sum(1 for c in commits if c.paths and all(DOC_RE.search(p) for p in c.paths)), n
        ),
        "feat_pct": _pct(kinds.get("feat", 0), n),
        "fix_pct": _pct(kinds.get("fix", 0), n),
        "test_pct": _pct(kinds.get("test", 0), n),
        "rework_pct": rework_rate(commits),
        "types": dict(kinds.most_common()),
    }


def split_groups(
    commits: Sequence[Commit],
) -> Dict[str, List[Commit]]:
    """Partition commits into the AI-declared and human-declared groups."""
    groups: Dict[str, List[Commit]] = {"ai": [], "human": []}
    for commit in commits:
        groups["ai" if commit.is_ai else "human"].append(commit)
    return groups


def compare_by_type(
    commits: Sequence[Commit], depth: int = 2
) -> List[Dict[str, object]]:
    """Per commit-type comparison, AI group vs human group.

    Only types present in both groups are kept: a type with two commits on the
    AI side says nothing about radius.
    """
    buckets: Dict[str, Dict[str, List[Commit]]] = defaultdict(lambda: {"ai": [], "human": []})
    for commit in commits:
        buckets[commit.kind]["ai" if commit.is_ai else "human"].append(commit)

    rows: List[Dict[str, object]] = []
    for kind, group in sorted(buckets.items(), key=lambda kv: -sum(len(v) for v in kv[1].values())):
        if not group["ai"] or not group["human"]:
            continue
        rows.append(
            {
                "type": kind,
                "ai": summarize(group["ai"], depth),
                "human": summarize(group["human"], depth),
            }
        )
    return rows


def signal_counts(added_lines: Iterable[str]) -> Counter:
    """Count suspicious-but-common added lines."""
    counter: Counter = Counter()
    for line in added_lines:
        for name, pattern in SIGNAL_PATTERNS.items():
            if pattern.search(line):
                counter[name] += 1
    return counter


def signals_per_1k(counter: Counter, commits: int) -> Dict[str, float]:
    if not commits:
        return {}
    return {name: round(1000.0 * value / commits, 1) for name, value in counter.items()}
