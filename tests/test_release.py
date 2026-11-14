import re
import unittest

from helpers import ROOT


class ReleaseMetadataTests(unittest.TestCase):
    def test_version_has_changelog_section(self):
        version = (ROOT / "VERSION").read_text().strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        changelog = (ROOT / "CHANGELOG.md").read_text()
        self.assertIn("## [Unreleased]", changelog)
        if version != "0.1.0":  # bootstrap version predates the first release section
            self.assertRegex(changelog, rf"(?m)^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$")


if __name__ == "__main__":
    unittest.main()
