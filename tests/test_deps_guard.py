import datetime
import unittest

from helpers import load_module

M = load_module(".github/workflows/deps-weekly-guard.yml", step_id="guard")
NOW = datetime.datetime(2026, 11, 16, 13, 30, tzinfo=datetime.timezone.utc)


def pr(number, created, login="dependabot[bot]", labels=(), ref=None, title=None):
    ref = ref if ref is not None else f"dependabot/develop/weekly-{number:04x}abc"
    return {"number": number, "created_at": created, "title": title or f"deps {number}", "user": {"login": login},
            "head": {"sha": f"sha{number}", "ref": ref}, "base": {"ref": "develop"},
            "labels": [{"name": n} for n in labels]}


class FakeApi:
    def __init__(self, pulls, behind=0, runs=None, issues=None):
        self.pulls, self.behind, self.runs, self.issues = pulls, behind, runs, issues or []
        self.calls = []

    def call(self, method, path, body=None):
        self.calls.append((method, path, body))
        if method == "GET" and path.startswith("/pulls?"):
            return self.pulls
        if method == "GET" and path.startswith("/compare/"):
            return {"behind_by": self.behind}
        if method == "GET" and "/check-runs" in path:
            return {"check_runs": self.runs or []}
        if method == "GET" and path.startswith("/issues?"):
            return self.issues
        if method == "POST" and path == "/issues":
            return {"number": 99, "body": body["body"]}
        return {}

    def writes(self):
        return [(m, p) for m, p, _ in self.calls if m != "GET"]


class GuardTests(unittest.TestCase):
    def test_closes_older_dependabot_prs(self):
        api = FakeApi([pr(3, "2026-11-09T12:00:00Z"), pr(8, "2026-11-16T12:00:00Z"), pr(5, "2026-11-10T00:00:00Z", login="me")])
        actions, _, survivor = M.guard(api, "pull_request", "ci-gate", False, NOW)
        self.assertEqual(survivor["number"], 8)
        self.assertEqual(api.writes(), [("POST", "/issues/3/comments"), ("PATCH", "/pulls/3")])
        self.assertIn("superseded by #8", actions[0])

    def test_security_or_other_dependabot_prs_are_never_closed(self):
        api = FakeApi([pr(3, "2026-11-09T12:00:00Z", ref="dependabot/npm_and_yarn/lodash-4.17.21"),
                       pr(8, "2026-11-16T12:00:00Z")])
        _, notes, survivor = M.guard(api, "pull_request", "ci-gate", False, NOW)
        self.assertEqual(survivor["number"], 8)
        self.assertEqual(api.writes(), [])
        self.assertTrue(any("#3" in n for n in notes))

    def test_check_name_with_spaces_is_encoded(self):
        api = FakeApi([pr(8, "2026-11-16T12:00:00Z")], runs=[{"status": "completed", "conclusion": "success"}])
        M.guard(api, "schedule", "ci / ci-gate", False, NOW)
        path = [p for _, p, _ in api.calls if "/check-runs" in p][0]
        self.assertNotIn(" ", path)
        self.assertIn("check_name=ci+%2F+ci-gate", path)

    def test_cancelled_or_skipped_gate_is_neither_red_nor_green(self):
        for conclusion in ("cancelled", "skipped", "neutral", "stale"):
            api = FakeApi([pr(8, "2026-11-16T12:00:00Z", labels=["needs-fix"])],
                          runs=[{"status": "completed", "conclusion": conclusion}])
            _, notes, _ = M.guard(api, "schedule", "ci-gate", False, NOW)
            with self.subTest(conclusion=conclusion):
                self.assertEqual(api.writes(), [])
                self.assertTrue(any("no green result" in n for n in notes))

    def test_titles_cannot_mention(self):
        api = FakeApi([pr(8, "2026-11-16T12:00:00Z", title="bump @babel/core | x")])
        _, notes, _ = M.guard(api, "pull_request", "ci-gate", False, NOW)
        self.assertIn("`bump @babel/core x`", notes[0])

    def test_single_pr_on_pull_request_event_only_dedupes(self):
        api = FakeApi([pr(8, "2026-11-16T12:00:00Z")])
        M.guard(api, "pull_request", "ci-gate", False, NOW)
        self.assertEqual(api.writes(), [])
        self.assertFalse(any("/check-runs" in p for _, p, _ in api.calls))

    def test_red_gate_labels_needs_fix(self):
        api = FakeApi([pr(8, "2026-11-16T12:00:00Z")], runs=[{"status": "completed", "conclusion": "failure"}])
        actions, _, _ = M.guard(api, "schedule", "ci-gate", False, NOW)
        self.assertIn(("POST", "/issues/8/labels"), api.writes())
        self.assertIn("labelled #8 needs-fix", actions)

    def test_green_gate_removes_needs_fix(self):
        api = FakeApi([pr(8, "2026-11-16T12:00:00Z", labels=["needs-fix"])],
                      runs=[{"status": "completed", "conclusion": "success"}])
        M.guard(api, "schedule", "ci-gate", False, NOW)
        self.assertIn(("DELETE", "/issues/8/labels/needs-fix"), api.writes())

    def test_pending_gate_changes_nothing(self):
        api = FakeApi([pr(8, "2026-11-16T12:00:00Z")], runs=[{"status": "in_progress", "conclusion": None}])
        _, notes, _ = M.guard(api, "schedule", "ci-gate", False, NOW)
        self.assertEqual(api.writes(), [])
        self.assertTrue(any("no green result" in n for n in notes))

    def test_behind_never_comments_unless_opted_in(self):
        api = FakeApi([pr(8, "2026-11-16T12:00:00Z")], behind=2, runs=[{"status": "completed", "conclusion": "success"}])
        M.guard(api, "schedule", "ci-gate", False, NOW)
        self.assertEqual(api.writes(), [])
        api = FakeApi([pr(8, "2026-11-16T12:00:00Z")], behind=2, runs=[{"status": "completed", "conclusion": "success"}])
        M.guard(api, "schedule", "ci-gate", True, NOW)
        self.assertIn(("POST", "/issues/8/comments"), api.writes())

    def test_no_dependabot_pr(self):
        api = FakeApi([pr(5, "2026-11-10T00:00:00Z", login="me")])
        _, notes, survivor = M.guard(api, "schedule", "ci-gate", False, NOW)
        self.assertIsNone(survivor)
        self.assertEqual(api.writes(), [])


class TrackerTests(unittest.TestCase):
    def test_replace_section_with_end_before_start_appends(self):
        body = M.replace_section("<!-- s:end --> text <!-- s:start -->", "s", "new")
        self.assertTrue(body.endswith("<!-- s:end -->\n"))
        self.assertIn("text", body)

    def test_ensure_tracker_reuses_renamed_issue_with_marker_only(self):
        api = FakeApi([], issues=[{"number": 5, "title": "CVE report from a human", "body": "details"},
                                  {"number": 6, "title": "renamed by owner", "body": "<!-- tracking-issue -->\nx"}])
        self.assertEqual(M.ensure_tracker(api, "Dependency and vulnerability tracker", "vuln")["number"], 6)
        api = FakeApi([], issues=[{"number": 5, "title": "CVE report from a human", "body": "details"}])
        self.assertEqual(M.ensure_tracker(api, "Dependency and vulnerability tracker", "vuln")["number"], 99)

    def test_replace_section_appends_then_replaces(self):
        body = M.replace_section("intro", "deps-weekly-guard", "one")
        self.assertIn("intro", body)
        body = M.replace_section(body + "\n<!-- vuln-daily:start -->\nv\n<!-- vuln-daily:end -->", "deps-weekly-guard", "two")
        self.assertIn("two", body)
        self.assertNotIn("one", body)
        self.assertIn("vuln-daily:start", body)

    def test_ensure_tracker_reuses_existing_issue(self):
        api = FakeApi([], issues=[{"number": 4, "title": "Dependency and vulnerability tracker", "body": ""}])
        self.assertEqual(M.ensure_tracker(api, "Dependency and vulnerability tracker", "vuln")["number"], 4)
        self.assertEqual(api.writes(), [])

    def test_ensure_tracker_creates_one_issue_without_mentions(self):
        api = FakeApi([])
        issue = M.ensure_tracker(api, "Dependency and vulnerability tracker", "vuln")
        self.assertEqual(issue["number"], 99)
        created = [b for m, p, b in api.calls if m == "POST" and p == "/issues"][0]
        self.assertNotIn("@", created["body"])


if __name__ == "__main__":
    unittest.main()
