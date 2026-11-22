import contextlib
import io
import json
import tempfile
import unittest

from support import commit, init_repo, lines

from ai_attrib.cli import main


def run(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(argv)
    return code, out.getvalue()


class ReportCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = init_repo(self.tmp.name + "/repo")
        commit(
            self.repo,
            "feat(core): ai commit\n\nCo-authored-by: Claude <noreply@anthropic.com>",
            {"src/core/a.js": lines(5)},
            day="2025-01-02",
        )
        commit(
            self.repo,
            "feat(core): human commit",
            {"src/core/b.js": lines(5)},
            day="2025-01-03",
        )
        commit(
            self.repo,
            "fix(core): another ai commit\n\nCo-authored-by: Copilot <noreply@github.com>",
            {"src/core/a.js": lines(2)},
            day="2025-01-09",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_markdown_has_both_groups(self) -> None:
        code, text = run(["report", self.repo])
        self.assertEqual(code, 0)
        self.assertIn("AI-declared", text)
        self.assertIn("Human-declared", text)
        self.assertIn("declared AI involvement", text)
        self.assertIn("rework within 14d", text)

    def test_json_is_parseable(self) -> None:
        code, text = run(["report", self.repo, "--format", "json"])
        self.assertEqual(code, 0)
        payload = json.loads(text)
        self.assertEqual(payload["total"]["commits"], 3)
        self.assertEqual(payload["groups"]["ai"]["commits"], 2)
        self.assertEqual(payload["groups"]["human"]["commits"], 1)

    def test_baseline_section(self) -> None:
        code, text = run(
            ["report", self.repo, "--baseline", "2025-01-01..2025-01-05"]
        )
        self.assertEqual(code, 0)
        self.assertIn("Baseline window", text)

    def test_non_repo_exits_nonzero(self) -> None:
        code, _ = run(["report", self.tmp.name + "/missing"])
        self.assertEqual(code, 2)

    def test_custom_ai_pattern(self) -> None:
        code, text = run(
            ["report", self.repo, "--ai-pattern", r"human commit", "--format", "json"]
        )
        self.assertEqual(code, 0)
        payload = json.loads(text)
        self.assertEqual(payload["groups"]["ai"]["commits"], 3)


class DemoCommandTest(unittest.TestCase):
    def test_demo_produces_report(self) -> None:
        code, text = run(["demo"])
        self.assertEqual(code, 0)
        self.assertIn("# ai-attrib report", text)
        self.assertIn("<generated demo repo>", text)


if __name__ == "__main__":
    unittest.main()
