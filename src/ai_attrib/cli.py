"""Command line interface."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from typing import Dict, List, Optional, Sequence, Tuple

from . import __version__
from .attribution import compile_patterns, mark
from .gitio import GitError, head_sha, is_repo, iter_added_lines, read_commits
from .metrics import compare_by_type, signal_counts, signals_per_1k, split_groups, summarize
from .render import render_json, render_markdown, write_output


def _parse_window(value: Optional[str]) -> Optional[Tuple[str, str]]:
    if not value:
        return None
    if ".." not in value:
        raise argparse.ArgumentTypeError("expected SINCE..UNTIL, e.g. 2025-01-01..2025-06-30")
    start, end = value.split("..", 1)
    if not start.strip() or not end.strip():
        raise argparse.ArgumentTypeError("both ends of SINCE..UNTIL are required")
    return start.strip(), end.strip()


def build_report(
    repo: str,
    rev: str = "HEAD",
    since: Optional[str] = None,
    until: Optional[str] = None,
    baseline: Optional[Tuple[str, str]] = None,
    signals: bool = False,
    patterns: Optional[Sequence[str]] = None,
    depth: int = 2,
) -> Dict[str, object]:
    """Collect commits and compute the full report structure."""
    if not is_repo(repo):
        raise GitError(f"{repo} is not inside a git work tree")

    compiled = compile_patterns(patterns or ())
    commits = mark(read_commits(repo, rev, since, until), compiled)
    total = summarize(commits, depth, total_for_share=len(commits))
    groups = split_groups(commits)
    group_summaries = {
        name: summarize(items, depth, total_for_share=len(commits))
        for name, items in groups.items()
    }

    report: Dict[str, object] = {
        "tool": {"name": "ai-attrib", "version": __version__},
        "repo": {"path": os.path.abspath(repo), "rev": rev, "head": head_sha(repo)},
        "window": {"since": since, "until": until},
        "total": total,
        "groups": group_summaries,
        "by_type": compare_by_type(commits, depth),
        "baseline": None,
        "signals": None,
        "warnings": [],
    }

    warnings: List[str] = []
    ai_count = (group_summaries.get("ai") or {}).get("commits", 0)
    if not ai_count:
        warnings.append(
            "No commit declares AI involvement. Check the trailer format your team uses "
            "and pass --ai-pattern '...' if it differs."
        )
    elif ai_count < 20:
        warnings.append(
            f"Only {ai_count} AI-declared commits: the comparison is directional, not significant."
        )
    if len(commits) < 50:
        warnings.append(f"Only {len(commits)} commits in the window: small-sample caveat applies.")
    report["warnings"] = warnings

    if signals:
        counter = signal_counts(line for _, lines in iter_added_lines(repo, rev, since, until) for line in lines)
        report["signals"] = {
            "counts": dict(counter.most_common()),
            "per_1k": signals_per_1k(counter, len(commits)),
        }

    if baseline:
        base_since, base_until = baseline
        base_commits = mark(read_commits(repo, rev, base_since, base_until), compiled)
        base_groups = split_groups(base_commits)
        report["baseline"] = {
            "window": {"since": base_since, "until": base_until},
            "total": summarize(base_commits, depth, total_for_share=len(base_commits)),
            "groups": {
                name: summarize(items, depth, total_for_share=len(base_commits))
                for name, items in base_groups.items()
            },
        }

    return report


def _cmd_report(args: argparse.Namespace) -> int:
    try:
        report = build_report(
            repo=args.repo,
            rev=args.rev,
            since=args.since,
            until=args.until,
            baseline=_parse_window(args.baseline),
            signals=args.signals,
            patterns=args.ai_pattern,
            depth=args.module_depth,
        )
    except GitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    text = render_json(report) if args.format == "json" else render_markdown(report)
    write_output(text, args.out)
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    from .demo import build_demo_repo, demo_windows

    base_since, base_until, since, until = demo_windows()
    with tempfile.TemporaryDirectory(prefix="ai-attrib-demo-") as tmp:
        repo = build_demo_repo(os.path.join(tmp, "demo-repo"))
        report = build_report(
            repo=repo,
            since=since,
            until=until,
            baseline=(base_since, base_until),
            signals=True,
            depth=args.module_depth,
        )
        report["repo"]["path"] = "<generated demo repo>"
        report["repo"]["head"] = "synthetic"
        text = render_json(report) if args.format == "json" else render_markdown(report)
        write_output(text, args.out)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-attrib",
        description="Measure declared AI involvement in a git repository. Read-only, no network.",
    )
    parser.add_argument("--version", action="version", version=f"ai-attrib {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    report = sub.add_parser("report", help="analyse a repository")
    report.add_argument("repo", help="path to the repository (any subdirectory works)")
    report.add_argument("--rev", default="HEAD", help="revision to walk (default: HEAD)")
    report.add_argument("--since", help="start date, YYYY-MM-DD")
    report.add_argument("--until", help="end date, YYYY-MM-DD")
    report.add_argument("--baseline", help="second window to compare against, SINCE..UNTIL")
    report.add_argument("--signals", action="store_true", help="also scan added lines (slower)")
    report.add_argument(
        "--ai-pattern",
        action="append",
        default=[],
        help="extra regex marking a commit as AI-declared (repeatable)",
    )
    report.add_argument("--module-depth", type=int, default=2, help="path segments per module")
    report.add_argument("--format", choices=["md", "json"], default="md")
    report.add_argument("-o", "--out", help="write to a file instead of stdout")
    report.set_defaults(func=_cmd_report)

    demo = sub.add_parser("demo", help="build a synthetic repo and report on it")
    demo.add_argument("--module-depth", type=int, default=2)
    demo.add_argument("--format", choices=["md", "json"], default="md")
    demo.add_argument("-o", "--out", help="write to a file instead of stdout")
    demo.set_defaults(func=_cmd_demo)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
