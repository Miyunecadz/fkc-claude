#!/usr/bin/env python3
"""Regression tests for the workspace's guardrail rule files and the local engine patch.

Covers: destructive commands (incl. `git -C <dir>` forms), destructive SQL, pushes to
master/main and force pushes, shell reads of real `.env` files, edits to applied
migrations in a nested repo, bad hook input, and the presence of the local
`git_target_dirs` patch that a `/lodestar-update` would wipe.

Run: python3 .claude/hooks/tests/test_guardrails_rules.py
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = os.path.abspath(os.path.join(HOOKS, "..", ".."))
HOOK = os.path.join(HOOKS, "lodestar-guardrails.py")

GIT_ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


def run_hook(payload, project=PROJECT, raw=None):
    data = raw if raw is not None else json.dumps(payload)
    proc = subprocess.run(["python3", HOOK], input=data.encode(), capture_output=True,
                          env=dict(os.environ, CLAUDE_PROJECT_DIR=project))
    return proc.returncode, json.loads(proc.stdout.decode() or "{}")


def outcome(out):
    """('block'|'warn'|'allow', [rule names])."""
    hso = out.get("hookSpecificOutput", {})
    if hso.get("permissionDecision") == "deny":
        return "block", re.findall(r"\*\*\[([^\]]+)\]", hso["permissionDecisionReason"])
    if "systemMessage" in out:
        return "warn", re.findall(r"\*\*\[([^\]]+)\]", out["systemMessage"])
    return "allow", []


def bash(command, cwd=PROJECT, project=PROJECT):
    return outcome(run_hook({"tool_name": "Bash", "tool_input": {"command": command},
                             "cwd": cwd}, project)[1])


def edit(path, cwd=PROJECT, project=PROJECT, tool="Edit"):
    return outcome(run_hook({"tool_name": tool, "tool_input": {
        "file_path": path, "old_string": "a", "new_string": "b", "content": "b"},
        "cwd": cwd}, project)[1])


class Destructive(unittest.TestCase):
    RULE = "block-destructive-commands"

    def assertBlocked(self, cmd, rule=None):
        verdict, names = bash(cmd)
        self.assertEqual(verdict, "block", cmd)
        self.assertIn(rule or self.RULE, names, cmd)

    def assertNotBlockedBy(self, cmd, rule=None):
        verdict, names = bash(cmd)
        self.assertNotIn(rule or self.RULE, names if verdict == "block" else [], cmd)

    def test_blocks(self):
        for cmd in [
            "rm -rf node_modules", "rm -fr build", "rm -r -f build", "rm -Rf build",
            "rm --recursive --force build", "git reset --hard",
            "git -C fk-admin-panel-be reset --hard", "git -C fk-admin-panel-be reset --hard HEAD~1",
            "git -C fk-admin-panel-be clean -fd", "git clean --force",
            "git -C fk-admin-panel-be checkout .", "git -C x restore -- .", "git checkout -- .",
            "git branch -D feat/x", "git -C fk-mobile branch -D feat/x",
            "git branch --delete --force feat/x",
            "git worktree remove --force .work/X/fk-mobile", "git -C be worktree remove -f wt",
            "find . -name '*.log' -delete", "dbmate drop", 'bash -c "rm -rf build"',
            "rm -rf /tmp/x /home/someone",
        ]:
            self.assertBlocked(cmd)

    def test_allows(self):
        for cmd in [
            "rm -f notes.txt", "rm notes.txt", "rm -r build", "rm -rf /tmp/foo",
            "echo 'rm -rf x'", "git restore --staged .", "git branch -d feat/x",
            "git rm -r --cached x", "docker run --rm -it -f x", "find . -name x -print",
            "git status", "git reset HEAD file",
        ]:
            self.assertNotBlockedBy(cmd)

    def test_sql(self):
        self.assertBlocked('mysql -e "DROP TABLE users"', "block-destructive-sql")
        self.assertBlocked("mysql -u r -e 'truncate orders'", "block-destructive-sql")
        self.assertNotBlockedBy('mysql -e "SELECT 1"', "block-destructive-sql")


class Push(unittest.TestCase):
    RULE = "protect-default-branch"

    def test_blocks(self):
        for cmd in [
            "git -C fk-admin-panel-be push -f", "git push --force", "git push -uf origin feat/x",
            "git -C fk-admin-panel-be push origin +feat/x", "git push origin master",
            "git -C fk-admin-panel-be push origin HEAD:master", "git -C be push origin :main",
            "git push origin HEAD:refs/heads/main",
        ]:
            verdict, names = bash(cmd)
            self.assertEqual(verdict, "block", cmd)
            self.assertIn(self.RULE, names, cmd)

    def test_allows(self):
        for cmd in [
            "git -C fk-admin-panel-be push -u origin feat/x", "git push origin feat/main-menu",
            "git push --force-with-lease", "git push origin staging",
        ]:
            verdict, names = bash(cmd)
            self.assertNotIn(self.RULE, names if verdict == "block" else [], cmd)


class EnvBash(unittest.TestCase):
    RULE = "block-env-files-bash"

    def test_blocks(self):
        for cmd in [
            "cat .env", "cat fk-admin-panel-be/.env", "grep DB_PASS fk-admin-panel-be/.env",
            "cp fk-admin-panel-be/.env /tmp/x", "head -3 fk-mobile/.env.staging",
            "tail .env.local", "cat .envrc", "sed -n 1p .env.production", "awk 1 .env.test",
            'cat "$BE/.env.development"', "while read l; do echo $l; done < fk-admin-panel-be/.env",
        ]:
            verdict, names = bash(cmd)
            self.assertEqual(verdict, "block", cmd)
            self.assertIn(self.RULE, names, cmd)

    def test_allows(self):
        for cmd in [
            "cat .env.example", "cat fk-mobile/.env.development.example", "cat .env.sample",
            "cat .env.local.example", "ls -la fk-admin-panel-be/.env", "test -f .env",
            "cat docs/environment.md", "grep -r env src/",
        ]:
            verdict, names = bash(cmd)
            self.assertNotIn(self.RULE, names if verdict == "block" else [], cmd)

    def test_file_rule_covers_envrc(self):
        verdict, names = edit(os.path.join(PROJECT, "fk-admin-panel-be/.envrc"))
        self.assertEqual((verdict, names), ("block", ["block-env-files"]))

    def test_settings_deny_read(self):
        with open(os.path.join(PROJECT, ".claude", "settings.json")) as f:
            deny = json.load(f)["permissions"]["deny"]
        for name in (".env.staging", ".env.test", ".envrc"):
            self.assertIn("Read(./**/%s)" % name, deny)


class AppliedMigrations(unittest.TestCase):
    """A root repo that ignores a nested repo, like this workspace."""

    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp()
        shutil.copytree(os.path.join(PROJECT, ".claude", "guardrails"),
                        os.path.join(cls.root, ".claude", "guardrails"))
        cls.git(cls.root, "init", "-q", "-b", "main", ".")
        with open(os.path.join(cls.root, ".gitignore"), "w") as f:
            f.write("/be\n")
        cls.git(cls.root, "add", ".gitignore")
        cls.git(cls.root, "commit", "-qm", "init")
        be = os.path.join(cls.root, "be")
        os.makedirs(os.path.join(be, "db", "migrations"))
        cls.git(be, "init", "-q", "-b", "master", ".")
        cls.old = os.path.join(be, "db", "migrations", "20260101000000_old.sql")
        with open(cls.old, "w") as f:
            f.write("-- migrate:up\n")
        cls.git(be, "add", ".")
        cls.git(be, "commit", "-qm", "m")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    @staticmethod
    def git(cwd, *args):
        subprocess.run(["git", "-C", cwd] + list(args), check=True, env=GIT_ENV,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def test_tracked_migration_blocks(self):
        verdict, names = edit(self.old, cwd=self.root, project=self.root)
        self.assertEqual(verdict, "block")
        self.assertIn("block-edit-applied-migrations", names)

    def test_new_migration_allowed(self):
        new = os.path.join(self.root, "be", "db", "migrations", "20990101000000_new.sql")
        verdict, names = edit(new, cwd=self.root, project=self.root, tool="Write")
        self.assertNotIn("block-edit-applied-migrations", names)

    def test_real_workspace_tracked_migration_blocks(self):
        mig = os.path.join(PROJECT, "fk-admin-panel-be", "db", "migrations")
        if not os.path.isdir(mig):
            self.skipTest("fk-admin-panel-be not checked out")
        out = subprocess.run(["git", "-C", mig, "ls-files", "."], capture_output=True)
        files = [l for l in out.stdout.decode().splitlines() if l.endswith(".sql")]
        if not files:
            self.skipTest("no tracked migrations")
        verdict, names = edit(os.path.join(mig, files[-1]))
        self.assertIn("block-edit-applied-migrations", names)


class Warnings(unittest.TestCase):
    def test_design_guidance_disabled(self):
        verdict, names = edit(os.path.join(PROJECT, "fk-admin-panel-fe/src/App.jsx"))
        self.assertNotIn("design-guidance-on-ui-edits", names)

    def test_verifier_names_real_agent(self):
        with open(os.path.join(PROJECT, ".claude", "guardrails", "verifier-before-commit.md")) as f:
            text = f.read()
        self.assertIn("change-reviewer", text)
        self.assertNotIn("`reviewer`", text)
        self.assertTrue(os.path.exists(os.path.join(PROJECT, ".claude", "agents", "change-reviewer.md")))


class Engine(unittest.TestCase):
    def test_bad_input_is_loud(self):
        for raw in ("not json", "", "[1]"):
            code, out = run_hook(None, raw=raw)
            self.assertEqual(code, 0)
            self.assertIn("NOT ENFORCING", out.get("systemMessage", ""), repr(raw))
            self.assertNotIn("hookSpecificOutput", out)

    def test_local_patch_present(self):
        # The engine is kit-owned. This workspace carries a local patch that resolves
        # `git -C <dir>` targets; a `/lodestar-update` that overwrites the engine would
        # drop it, and every worktree commit would be blocked again.
        with open(HOOK) as f:
            src = f.read()
        self.assertIn("def git_target_dirs(", src,
                      "LOCAL PATCH LOST: lodestar-guardrails.py has no git_target_dirs. "
                      "Re-apply it (see tests/test_guardrails_branch.py).")
        self.assertIn("def command_on_default_branch(", src,
                      "LOCAL PATCH LOST: lodestar-guardrails.py has no command_on_default_branch.")
        self.assertIn("ctx.command_on_default_branch(", src,
                      "LOCAL PATCH LOST: suppressed() no longer calls command_on_default_branch.")


if __name__ == "__main__":
    unittest.main()
