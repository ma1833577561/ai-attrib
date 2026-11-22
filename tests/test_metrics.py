import unittest

from support import SRC  # noqa: F401  (adds src/ to sys.path)

from ai_attrib.metrics import (
    compare_by_type,
    module_of,
    percentile,
    rework_rate,
    signal_counts,
    split_groups,
    summarize,
)
from ai_attrib.model import Commit, commit_type


def make(sha: str, day: str, subject: str, paths, ai: bool = False, lines: int = 10) -> Commit:
    return Commit(
        sha=sha,
        date=day,
        author="tester",
        subject=subject,
        files=len(paths),
        paths=tuple(paths),
        insertions=lines,
        deletions=0,
        is_ai=ai,
    )


class PercentileTest(unittest.TestCase):
    def test_nearest_rank(self) -> None:
        values = list(range(1, 11))
        self.assertEqual(percentile(values, 0.5), 5)
        self.assertEqual(percentile(values, 0.9), 9)
        self.assertEqual(percentile([], 0.9), 0)

    def test_single_value(self) -> None:
        self.assertEqual(percentile([7], 0.9), 7)


class ModuleTest(unittest.TestCase):
    def test_source_root_gets_extra_segment(self) -> None:
        self.assertEqual(module_of("src/views/finance/detail.tsx", 2), "src/views/finance")
        self.assertEqual(module_of("src/index.ts", 2), "src/index.ts")

    def test_other_paths_use_depth(self) -> None:
        self.assertEqual(module_of("docs/guide/intro.md", 2), "docs/guide")
        self.assertEqual(module_of("README.md", 2), "README.md")


class ReworkTest(unittest.TestCase):
    def test_same_file_fix_within_window(self) -> None:
        commits = [
            make("a", "2025-01-01", "fix: first", ["src/x.js"]),
            make("b", "2025-01-05", "fix: second", ["src/x.js"]),
        ]
        self.assertEqual(rework_rate(commits, window_days=14), 50.0)

    def test_fix_outside_window_is_not_rework(self) -> None:
        commits = [
            make("a", "2025-01-01", "fix: first", ["src/x.js"]),
            make("b", "2025-03-01", "fix: second", ["src/x.js"]),
        ]
        self.assertEqual(rework_rate(commits, window_days=14), 0.0)

    def test_different_files_are_not_rework(self) -> None:
        commits = [
            make("a", "2025-01-01", "fix: first", ["src/x.js"]),
            make("b", "2025-01-02", "fix: second", ["src/y.js"]),
        ]
        self.assertEqual(rework_rate(commits, window_days=14), 0.0)

    def test_no_fix_commits(self) -> None:
        self.assertEqual(rework_rate([make("a", "2025-01-01", "feat: x", ["x.js"])]), 0.0)


class SummarizeTest(unittest.TestCase):
    def test_counts_and_shares(self) -> None:
        commits = [
            make("a", "2025-01-01", "feat: one", ["src/a/1.js", "src/a/2.js"], ai=True),
            make("b", "2025-01-02", "docs: two", ["docs/x.md"]),
            make("c", "2025-01-03", "fix: three", ["src/b/1.js", "src/c/1.js", "src/d/1.js", "src/e/1.js"]),
        ]
        stats = summarize(commits, depth=2, total_for_share=len(commits))
        self.assertEqual(stats["commits"], 3)
        self.assertAlmostEqual(stats["large_commit_pct"], 0.0)
        self.assertAlmostEqual(stats["docs_only_pct"], 33.3)
        self.assertAlmostEqual(stats["cross3_module_pct"], 33.3)
        self.assertAlmostEqual(stats["feat_pct"], 33.3)
        self.assertEqual(stats["files_max"], 4)

    def test_empty_group(self) -> None:
        self.assertEqual(summarize([]), {"commits": 0})


class GroupingTest(unittest.TestCase):
    def test_split_and_compare(self) -> None:
        commits = [
            make("a", "2025-01-01", "feat: ai one", ["src/a/1.js"], ai=True),
            make("b", "2025-01-02", "feat: human one", ["src/b/1.js"]),
            make("c", "2025-01-03", "feat: ai two", ["src/c/1.js"], ai=True),
        ]
        groups = split_groups(commits)
        self.assertEqual(len(groups["ai"]), 2)
        self.assertEqual(len(groups["human"]), 1)

        rows = compare_by_type(commits)
        self.assertEqual([row["type"] for row in rows], ["feat"])
        self.assertEqual(rows[0]["ai"]["commits"], 2)

    def test_type_absent_from_one_group_is_dropped(self) -> None:
        commits = [
            make("a", "2025-01-01", "feat: ai", ["src/a.js"], ai=True),
            make("b", "2025-01-02", "fix: human", ["src/b.js"]),
        ]
        self.assertEqual(compare_by_type(commits), [])


class SignalTest(unittest.TestCase):
    def test_counts_suspicious_lines(self) -> None:
        counter = signal_counts(
            [
                "console.log('x')",
                "const a = b as any;",
                "// TODO: later",
                "const ok = 1",
            ]
        )
        self.assertEqual(counter["console.log"], 1)
        self.assertEqual(counter["as-any"], 1)
        self.assertEqual(counter["todo-fixme"], 1)


class CommitTypeTest(unittest.TestCase):
    def test_conventional_types(self) -> None:
        self.assertEqual(commit_type("feat(api): add"), "feat")
        self.assertEqual(commit_type("fix!: urgent"), "fix")
        self.assertEqual(commit_type("docs: readme"), "docs")
        self.assertEqual(commit_type("随手改一下"), "other")


if __name__ == "__main__":
    unittest.main()
