import datetime
import unittest

from helpers import load_module

M = load_module(".github/workflows/deps-weekly-guard.yml", step_id="guard")
NOW = datetime.datetime(2026, 11, 16, 13, 30, tzinfo=datetime.timezone.utc)


def pr(number, created, login="dependabot[bot]", labels=()):
    return {"number": number, "created_at": created, "title": f"deps {number}", "user": {"login": login},
            "head": {"sha": f"sha{number}"}, "base": {"ref": "develop"}, "labels": [{"name": n} for n in labels]}


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
        self.assertTrue(any("not completed" in n for n in notes))

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
