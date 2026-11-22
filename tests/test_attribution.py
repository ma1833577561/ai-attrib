import unittest

from support import SRC  # noqa: F401

from ai_attrib.attribution import compile_patterns, is_ai_commit, mark
from ai_attrib.model import Commit


def make(body: str, subject: str = "feat: x") -> Commit:
    return Commit(sha="abc", date="2025-01-01", author="t", subject=subject, body=body)


class AttributionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.patterns = compile_patterns()

    def test_claude_coauthor_is_ai(self) -> None:
        commit = make("Co-authored-by: Claude <noreply@anthropic.com>")
        self.assertTrue(is_ai_commit(commit, self.patterns))

    def test_copilot_generated_by_trailer(self) -> None:
        commit = make("Generated-by: Copilot")
        self.assertTrue(is_ai_commit(commit, self.patterns))

    def test_human_coauthor_is_not_ai(self) -> None:
        commit = make("Co-authored-by: Jane Doe <jane@example.com>")
        self.assertFalse(is_ai_commit(commit, self.patterns))

    def test_marker_in_subject(self) -> None:
        commit = make("", subject="feat: add cache [ai-assisted]")
        self.assertTrue(is_ai_commit(commit, self.patterns))

    def test_no_trailer_is_not_ai(self) -> None:
        self.assertFalse(is_ai_commit(make(""), self.patterns))

    def test_custom_pattern(self) -> None:
        patterns = compile_patterns([r"pair-programmed-with:\s*acme-bot"])
        commit = make("Pair-programmed-with: acme-bot")
        self.assertTrue(is_ai_commit(commit, patterns))

    def test_mark_sets_flag_on_all_commits(self) -> None:
        commits = [make("Co-authored-by: Codex <x@y.z>"), make("plain body")]
        marked = mark(commits, self.patterns)
        self.assertEqual([c.is_ai for c in marked], [True, False])


if __name__ == "__main__":
    unittest.main()
