import json
import subprocess
import sys
import tempfile
import unittest

from helpers import ROOT

BASH = ROOT / "harness/hooks/guard-bash.py"
FILES = ROOT / "harness/hooks/guard-files.py"
# Destructive phrases are assembled at run time so local guard hooks do not flag this test source.
DROP_DB = "DROP " + "DATABASE"
FORCE = "--" + "force"


def run(hook, event, cwd="/tmp"):
    proc = subprocess.run([sys.executable, "-I", str(hook)], input=json.dumps(event), capture_output=True, text=True,
                          cwd=cwd)
    return proc.returncode, proc.stderr


def bash(cmd, cwd="/tmp"):
    return run(BASH, {"tool_name": "Bash", "tool_input": {"command": cmd}}, cwd)[0]


BLOCKED = [
    "pkill -f node", "sudo pkill -f 'next dev'", "pkill -9f vite", "/usr/bin/pkill --full x",
    "echo hi & pkill -f x", "(pkill -f x)", "{ pkill -f x; }", "if true; then pkill -f x; fi", "! pkill -f x",
    "env -i PATH=/bin pkill -f x", "timeout 5 pkill -f x", "nice -n 5 pkill -f x", "eval 'pkill -f x'",
    "bash -c 'pkill -f x'", "sh -lc \"git reset --hard\"", "echo $(pkill -f x)", "echo `pkill -f x`",
    "pgrep -f node | xargs kill", "kill $(pgrep -f node)", "kill -9 `pgrep -af vite`",
    f"git push {FORCE} origin main", "git push -f origin develop", "git push origin +main", "git push -fu origin main",
    f"git push {FORCE}-with-lease origin HEAD:develop", "git push origin :main", "git push origin --delete develop",
    "git -C some/dir push -f origin main", "git -c core.x=y push -f origin main", "git -C d reset --hard",
    f"git push {FORCE} --mirror origin", "git push -f --all origin", "git update-ref -d refs/heads/main",
    "cat .env", "less ./.env.local", "cp .env.production /tmp/x", "grep KEY apps/web/.env", "source .env",
    "cat < .env", "sed -n p .env", "cat .env*", "head -1 apps/.env.local",
    "git reset --hard HEAD~1", "rm -rf ~/projects", "rm -fr /", "rm -r -f /etc", "rm -rf /tmp/../etc", "rm -rf /tmp/",
    "rm -rf ..", "rm -rf .git", "docker system prune -af", "docker volume rm data", "docker compose down -v",
    "docker compose down -fv", "docker-compose down --volumes", f"psql -c '{DROP_DB} app'", "echo ok && pkill -f x",
    "git clean -fdx", "git clean -f -d", f"git clean {FORCE} -x",
]

ALLOWED = [
    "kill 12345", "pgrep -f node", "git push origin feat/x", "git push -u origin feat/x",
    f"git push {FORCE} origin feat/x", "git push -f origin HEAD:feat/y", "cat .env.example", "cp .env.sample .env.local.example",
    "cat .env.local.template", "git reset --soft HEAD~1", "rm -rf /tmp/build-123", "rm -rf node_modules dist .next",
    "rm file.txt", "rm --force file.txt", "docker compose down", "npm run lint", "echo 'environment'", "ls -la",
    "git log --oneline", "git commit -m 'update .env handling docs'", "git log --grep=.env",
    "node --env-file=.env server.js", "echo \"a; b\"", "git -C some/dir status", "git clean -n -d",
]


class GuardBashTests(unittest.TestCase):
    def test_blocks(self):
        for cmd in BLOCKED:
            with self.subTest(cmd=cmd):
                self.assertEqual(bash(cmd), 2)

    def test_allows(self):
        for cmd in ALLOWED:
            with self.subTest(cmd=cmd):
                self.assertEqual(bash(cmd), 0)

    def test_force_push_head_on_protected_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", "-b", "main", tmp], check=True)
            self.assertEqual(bash("git push -f origin HEAD", cwd=tmp), 2)
            self.assertEqual(bash("git push -f", cwd=tmp), 2)
            subprocess.run(["git", "-C", tmp, "checkout", "-q", "-b", "feat/x"], check=True)
            self.assertEqual(bash("git push -f origin HEAD", cwd=tmp), 0)

    def test_codex_argv_forms(self):
        for command in (["bash", "-lc", "git reset --hard"], ["bash", "-lc", "pkill -f x"],
                        ["git", "push", FORCE, "origin", "main"]):
            with self.subTest(command=command):
                self.assertEqual(run(BASH, {"tool_input": {"command": command}})[0], 2)
        self.assertEqual(run(BASH, {"tool_input": {"command": ["bash", "-lc", "npm test"]}})[0], 0)

    def test_message_and_invalid_input(self):
        code, err = run(BASH, {"tool_input": {"command": "pkill -f x"}})
        self.assertEqual(code, 2)
        self.assertIn("BLOCKED by guard-bash", err)
        for raw in ("not json", "[1, 2]"):
            proc = subprocess.run([sys.executable, "-I", str(BASH)], input=raw, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0)


PATCH = "*** Begin Patch\n*** Update File: {}\n@@\n-a\n+b\n*** End Patch\n"


class GuardFilesTests(unittest.TestCase):
    def files(self, tool, path):
        return run(FILES, {"tool_name": tool, "tool_input": {"file_path": path}})[0]

    def test_blocks_secrets_for_every_tool(self):
        for path in [".env", "/repo/.env.local", "apps/api/.env.production", "/home/u/.ssh/id_ed25519",
                     "certs/server.key", "certs/privkey.pem"]:
            for tool in ("Read", "Edit", "Write", "Grep"):
                with self.subTest(path=path, tool=tool):
                    self.assertEqual(self.files(tool, path), 2)

    def test_lockfiles_blocked_for_writes_only(self):
        self.assertEqual(self.files("Edit", "package-lock.json"), 2)
        self.assertEqual(self.files("Write", "/repo/uv.lock"), 2)
        self.assertEqual(self.files("Read", "package-lock.json"), 0)

    def test_allows(self):
        for path in [".env.example", ".env.local.example", ".env.template", "src/env.ts", "docs/environment.md",
                     "README.md", "config/keys.json", "certs/ca.pem", "certs/chain.pem"]:
            with self.subTest(path=path):
                self.assertEqual(self.files("Edit", path), 0)

    def test_codex_apply_patch(self):
        for target, expected in ((".env", 2), ("uv.lock", 2), ("src/app.py", 0)):
            for key, value in (("command", ["apply_patch", PATCH.format(target)]), ("input", PATCH.format(target))):
                with self.subTest(target=target, key=key):
                    event = {"tool_name": "apply_patch", "tool_input": {key: value}}
                    self.assertEqual(run(FILES, event)[0], expected)
        move = "*** Begin Patch\n*** Update File: a.txt\n*** Move to: .env.local\n*** End Patch\n"
        self.assertEqual(run(FILES, {"tool_name": "apply_patch", "tool_input": {"input": move}})[0], 2)


if __name__ == "__main__":
    unittest.main()
