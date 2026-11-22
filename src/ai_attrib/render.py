"""Render a report dict as Markdown or JSON.

The Markdown output is meant to be pasted straight into a README or a PR
comment, so it stays table-only and free of decoration.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Sequence, Tuple

# (label, key, format) — order defines table order.
ROWS: Sequence[Tuple[str, str, str]] = (
    ("commits", "commits", "int"),
    ("share of all commits", "share_pct", "pct"),
    ("authors", "authors", "int"),
    ("files / commit (median)", "files_median", "num"),
    ("files / commit (p90)", "files_p90", "num"),
    ("lines / commit (median)", "lines_median", "num"),
    ("lines / commit (p90)", "lines_p90", "num"),
    ("commits touching >10 files", "large_commit_pct", "pct"),
    ("modules / commit (median)", "modules_median", "num"),
    ("crosses >3 modules", "cross3_module_pct", "pct"),
    ("touches tests", "test_touch_pct", "pct"),
    ("docs only", "docs_only_pct", "pct"),
    ("fix commits", "fix_pct", "pct"),
    ("rework within 14d", "rework_pct", "pct"),
)


def _fmt(value: object, kind: str) -> str:
    if value is None:
        return "–"
    if kind == "pct":
        return f"{float(value):.1f}%"
    if kind == "num":
        number = float(value)
        return f"{number:.0f}" if number.is_integer() else f"{number:.1f}"
    return str(value)


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


LABELS = {"ai": "AI-declared", "human": "Human-declared"}


def _group_table(report: Dict[str, object], groups: Dict[str, Dict[str, object]]) -> str:
    total = report.get("total") or {}
    if not total.get("commits"):
        return "_No commits in this window._"
    columns = ["ai", "human"]
    header = ["metric"] + [LABELS.get(key, key) for key in columns] + ["all"]
    rows: List[List[str]] = []
    for label, key, kind in ROWS:
        row = [label]
        for column in columns:
            row.append(_fmt((groups.get(column) or {}).get(key), kind))
        row.append(_fmt(total.get(key), kind))
        rows.append(row)
    return _table(header, rows)


def render_markdown(report: Dict[str, object]) -> str:
    repo = report.get("repo") or {}
    window = report.get("window") or {}
    groups = report.get("groups") or {}
    total = report.get("total") or {}
    out: List[str] = []

    out.append("# ai-attrib report")
    out.append("")
    out.append(f"- repo: `{repo.get('path', '')}`")
    out.append(f"- revision: `{repo.get('rev', 'HEAD')}` @ `{repo.get('head', '') or 'n/a'}`")
    if window.get("since") or window.get("until"):
        out.append(f"- window: {window.get('since') or '…'} → {window.get('until') or 'now'}")
    out.append(f"- commits analysed: **{total.get('commits', 0)}** (merges excluded)")
    ai = groups.get("ai") or {}
    out.append(
        f"- declared AI involvement: **{ai.get('commits', 0)}** commits "
        f"({_fmt(ai.get('share_pct') or 0.0, 'pct')} of all)"
    )
    out.append("")
    out.append("## AI-declared vs human-declared")
    out.append("")
    out.append(_group_table(report, groups))
    out.append("")

    by_type = report.get("by_type") or []
    if by_type:
        out.append("## Same metric, per commit type")
        out.append("")
        rows = []
        for item in by_type:
            ai_stats = item["ai"]
            human_stats = item["human"]
            rows.append(
                [
                    item["type"],
                    str(ai_stats.get("commits")),
                    _fmt(ai_stats.get("files_median"), "num"),
                    _fmt(ai_stats.get("lines_median"), "num"),
                    _fmt(ai_stats.get("cross3_module_pct"), "pct"),
                    str(human_stats.get("commits")),
                    _fmt(human_stats.get("files_median"), "num"),
                    _fmt(human_stats.get("lines_median"), "num"),
                    _fmt(human_stats.get("cross3_module_pct"), "pct"),
                ]
            )
        header = [
            "type",
            "AI n",
            "AI files",
            "AI lines",
            "AI >3 mod",
            "human n",
            "human files",
            "human lines",
            "human >3 mod",
        ]
        out.append(_table(header, rows))
        out.append("")

    signals = report.get("signals")
    if signals:
        out.append("## Added-line signals (per 1k commits)")
        out.append("")
        per_1k = signals.get("per_1k") or {}
        counts = signals.get("counts") or {}
        rows = [[name, str(counts.get(name, 0)), _fmt(value, "num")] for name, value in per_1k.items()]
        out.append(_table(["signal", "count", "per 1k commits"], rows))
        out.append("")

    baseline = report.get("baseline")
    if baseline:
        base_window = baseline.get("window") or {}
        out.append(
            f"## Baseline window `{base_window.get('since')} → {base_window.get('until')}`"
        )
        out.append("")
        rows = []
        for label, key, kind in ROWS:
            if key in ("share_pct",):
                continue
            before = (baseline.get("total") or {}).get(key)
            after = total.get(key)
            rows.append([label, _fmt(before, kind), _fmt(after, kind)])
        out.append(_table(["metric", "baseline", "current"], rows))
        out.append("")

    warnings = report.get("warnings") or []
    if warnings:
        out.append("## Warnings")
        out.append("")
        for warning in warnings:
            out.append(f"- {warning}")
        out.append("")

    out.append("## How to read this")
    out.append("")
    out.append(
        "- **Declared, not detected.** A commit only counts as AI-declared when its "
        "message carries a trailer such as `Co-authored-by: Claude`. Silent AI use is "
        "invisible, so the AI share is a floor, not an estimate."
    )
    out.append(
        "- **Rework is a proxy.** It counts `fix` commits that are followed by another "
        "`fix` on the same file within 14 days. It cannot tell a regression from an "
        "iterative refinement."
    )
    out.append(
        "- **Small groups are noise.** With fewer than ~20 commits per group, treat "
        "differences as directional only."
    )
    out.append("")
    return "\n".join(out)


def render_json(report: Dict[str, object]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, default=str)


def write_output(text: str, path: Optional[str]) -> None:
    if not path:
        print(text)
        return
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")
    print(f"wrote {path}")
