import tempfile
import unittest

from support import commit, init_repo, lines

from ai_attrib.gitio import is_repo, iter_added_lines, read_commits


class ReadCommitsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = init_repo(self.tmp.name + "/repo")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_subject_body_and_numstat(self) -> None:
        commit(
            self.repo,
            "feat(core): add retry\n\nSecond paragraph.\n\nCo-authored-by: Claude <noreply@anthropic.com>",
            {"src/core/a.js": lines(3)},
        )
        commits = read_commits(self.repo)
        self.assertEqual(len(commits), 1)
        only = commits[0]
        self.assertEqual(only.subject, "feat(core): add retry")
        self.assertIn("Second paragraph.", only.body)
        self.assertIn("Co-authored-by", only.body)
        self.assertEqual(only.files, 1)
        self.assertEqual(only.insertions, 3)
        self.assertEqual(only.paths, ("src/core/a.js",))

    def test_multiple_commits_are_split_correctly(self) -> None:
        commit(self.repo, "feat: one", {"a.js": lines(1)}, day="2025-01-01")
        commit(self.repo, "fix: two", {"a.js": lines(1)}, day="2025-01-02")
        commits = read_commits(self.repo)
        self.assertEqual([c.subject for c in commits], ["fix: two", "feat: one"])
        self.assertEqual(commits[0].files, 1)

    def test_window_filters_commits(self) -> None:
        commit(self.repo, "feat: old", {"a.js": lines(1)}, day="2024-01-01")
        commit(self.repo, "feat: new", {"b.js": lines(1)}, day="2025-01-01")
        commits = read_commits(self.repo, since="2024-06-01")
        self.assertEqual([c.subject for c in commits], ["feat: new"])

    def test_added_lines_exclude_context_and_deletions(self) -> None:
        sha = commit(self.repo, "feat: signal", {"a.js": "console.log('x')\n"})
        added = dict(iter_added_lines(self.repo))
        self.assertEqual(len(added), 1)
        (parsed_sha, only_lines), = added.items()
        self.assertEqual(parsed_sha, sha)
        self.assertIn("console.log('x')", only_lines)
        self.assertTrue(all(not line.startswith("+") for line in only_lines))

    def test_non_repository_is_rejected(self) -> None:
        self.assertFalse(is_repo(self.tmp.name + "/not-a-repo"))


if __name__ == "__main__":
    unittest.main()
