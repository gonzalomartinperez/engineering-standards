import datetime
import os
import pathlib
import tempfile
import unittest

from helpers import load_module

M = load_module(".github/workflows/vuln-daily.yml", step_id="record")

OSV = {"results": [{"source": {"path": "/github/workspace/package-lock.json"}, "packages": [
    {"package": {"name": "lodash", "version": "4.17.20", "ecosystem": "npm"},
     "vulnerabilities": [{"id": "GHSA-1", "database_specific": {"severity": "HIGH"}},
                         {"id": "GHSA-2", "affected": [{"database_specific": {"severity": "CRITICAL"}}]}]},
    {"package": {"name": "x", "version": "1", "ecosystem": "npm"}, "vulnerabilities": [{"id": "OSV-3"}]}]}]}


class VulnDailyTests(unittest.TestCase):
    def test_parse_osv_orders_by_severity(self):
        rows = M.parse_osv(OSV)
        self.assertEqual([r["id"] for r in rows], ["GHSA-2", "GHSA-1", "OSV-3"])
        self.assertEqual(rows[2]["severity"], "UNKNOWN")

    def test_render_has_counts_and_no_mentions(self):
        now = datetime.datetime(2026, 11, 16, 10, 0, tzinfo=datetime.timezone.utc)
        content, counts = M.render(M.parse_osv(OSV), [], now)
        self.assertEqual(counts, {"CRITICAL": 1, "HIGH": 1, "UNKNOWN": 1})
        self.assertNotIn("@", content)
        self.assertIn("| CRITICAL | `GHSA-2` | `lodash` |", content)

    def test_alias_groups_count_once_and_scoped_names_cannot_mention(self):
        data = {"results": [{"source": {"path": "package-lock.json"}, "packages": [
            {"package": {"name": "@babel/core", "version": "7.0.0", "ecosystem": "npm"},
             "groups": [{"ids": ["GHSA-a", "CVE-1"]}],
             "vulnerabilities": [{"id": "GHSA-a", "database_specific": {"severity": "HIGH"}}, {"id": "CVE-1"}]}]}]}
        rows = M.parse_osv(data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["severity"], "HIGH")
        content, counts = M.render(rows, [], datetime.datetime(2026, 11, 16, tzinfo=datetime.timezone.utc))
        self.assertEqual(counts, {"HIGH": 1})
        self.assertIn("`@babel/core`", content)
        self.assertNotRegex(content.replace("`@babel/core`", ""), r"(?<!`)@\w")

    def test_render_empty(self):
        content, counts = M.render([], [], datetime.datetime(2026, 11, 16, tzinfo=datetime.timezone.utc))
        self.assertIn("Open findings: none.", content)
        self.assertEqual(counts, {})

    def test_summary_only_on_monday_in_buenos_aires(self):
        monday_art = datetime.datetime(2026, 11, 16, 10, 0, tzinfo=datetime.timezone.utc)  # Mon 07:00 ART
        sunday_art = datetime.datetime(2026, 11, 16, 2, 0, tzinfo=datetime.timezone.utc)   # Sun 23:00 ART
        self.assertTrue(M.should_summarize(monday_art, 1, False))
        self.assertFalse(M.should_summarize(sunday_art, 1, False))
        self.assertTrue(M.should_summarize(sunday_art, 1, True))

    def test_compromise_watch(self):
        with tempfile.TemporaryDirectory() as tmp:
            wf = pathlib.Path(tmp, "workflows")
            wf.mkdir()
            (wf / "a.yml").write_text("steps:\n  - uses: tj-actions/changed-files@abc\n  - uses: actions/checkout@def # v7\n"
                                      "  - uses: 'aquasecurity/trivy-action@0.20.0'\n")
            hits = M.compromise_watch(tmp)
        self.assertEqual(len(hits), 2)
        self.assertIn("tj-actions/changed-files", hits[0])

    def test_parse_grype(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "1.json")
            pathlib.Path(path).write_text('{"source": {"target": {"userInput": "ghcr.io/a/b@sha256:1"}}, "matches": '
                                          '[{"vulnerability": {"id": "CVE-1", "severity": "High"}, "artifact": {"name": "openssl", "version": "3"}}]}')
            rows = M.parse_grype([path])
        self.assertEqual(rows[0]["severity"], "HIGH")
        self.assertEqual(rows[0]["source"], "ghcr.io/a/b@sha256:1")


if __name__ == "__main__":
    unittest.main()
