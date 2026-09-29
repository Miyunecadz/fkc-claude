#!/usr/bin/env python3
"""Tests for commit-msg-oneline.py.

Run: python3 .claude/hooks/tests/test_commit_msg.py
"""

import importlib.util
import json
import os
import subprocess
import unittest

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(HOOKS, "commit-msg-oneline.py")
spec = importlib.util.spec_from_file_location("commit_msg", HOOK)
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)

G = "git " + "commit"


def new_command(cmd):
    out = cm.decide(cmd)
    if not out:
        return cmd
    return out.get("hookSpecificOutput", {}).get("updatedInput", {}).get("command", cmd)


def denied(cmd):
    out = cm.decide(cmd) or {}
    return out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


class Collapse(unittest.TestCase):
    def test_multiline_to_subject(self):
        self.assertEqual(new_command(G + ' -m "feat: a\n\nbody"'), G + " -m 'feat: a'")

    def test_heredoc(self):
        cmd = G + " -m \"$(cat <<'EOF'\nfeat: a\n\nbody\nCo-Authored-By: Claude\nEOF\n)\""
        self.assertEqual(new_command(cmd), G + " -m 'feat: a'")

    def test_git_dash_c(self):
        cmd = "git -C /x/y commit -m \"fix: a\nbody\""
        self.assertEqual(new_command(cmd), "git -C /x/y commit -m 'fix: a'")

    def test_combined_short_flags(self):
        self.assertEqual(new_command(G + ' -am "feat: a\n\nbody"'), G + " -am 'feat: a'")

    def test_attached_value(self):
        self.assertEqual(new_command(G + ' -m"feat: a\nb"'), G + " -m'feat: a'")

    def test_long_option(self):
        self.assertEqual(new_command(G + ' --message "feat: a\n\nb"'), G + " --message 'feat: a'")
        self.assertEqual(new_command(G + ' --message="feat: a\nb"'), G + " --message='feat: a'")

    def test_extra_m_removed(self):
        cmd = G + ' -m "feat: a" -m "Co-Authored-By: Claude <x>"'
        self.assertEqual(new_command(cmd), G + ' -m "feat: a"')

    def test_co_author_trailer_removed(self):
        cmd = G + ' -m "feat: a" --trailer "Co-authored-by: C <c@x>" -q'
        self.assertEqual(new_command(cmd), G + ' -m "feat: a" -q')

    def test_single_line_unchanged(self):
        cmd = G + ' -m "feat(api): add x"'
        self.assertIsNone(cm.decide(cmd))

    def test_escaped_quotes(self):
        cmd = G + ' -m "feat: say \\"hi\\"\nbody"'
        self.assertEqual(new_command(cmd), G + " -m 'feat: say \"hi\"'")

    def test_backslash_only_special_unescaped(self):
        # \\d is not a double-quote escape: bash keeps the backslash.
        self.assertIsNone(cm.decide(G + ' -m "fix: match \\d+ and \\$x"'))
        edits, deny, _ = cm.check(G + ' -m "fix: match \\d+\nbody"')
        self.assertIsNone(deny)
        self.assertEqual(edits[0][2], "'fix: match \\d+'")


class SegmentScope(unittest.TestCase):
    def test_later_dash_m_untouched(self):
        cmd = G + ' -m "feat: x" && python3 -m pytest -q'
        self.assertIsNone(cm.decide(cmd))

    def test_git_log_m(self):
        cmd = "git add x && " + G + ' -m "fix: x" && git log -m --oneline -1'
        self.assertIsNone(cm.decide(cmd))

    def test_pipe_and_semicolon(self):
        cmd = G + ' -m "feat: a" | head -n1; sed -m x'
        self.assertIsNone(cm.decide(cmd))

    def test_other_commands(self):
        for cmd in ("grep -m1 commit file", "git log -m", "echo git commit -m 'x'"):
            self.assertIsNone(cm.decide(cmd), cmd)

    def test_collapse_keeps_rest_byte_for_byte(self):
        cmd = G + ' -m "feat: a\nbody"  &&  echo   "two  spaces"'
        self.assertEqual(new_command(cmd), G + " -m 'feat: a'  &&  echo   \"two  spaces\"")


class Rules(unittest.TestCase):
    def test_non_conventional_denied(self):
        self.assertTrue(denied(G + ' -m "update docs"'))
        self.assertTrue(denied(G + ' -m "Feat: capital type"'))
        self.assertTrue(denied(G + ' -m "feat:no space"'))

    def test_conventional_forms_allowed(self):
        for msg in ("feat: a", "fix(api): b", "chore!: c", "refactor(be)!: d",
                    "docs: e", "test: f", "perf: g", "build: h", "ci: i", "style: j",
                    "revert: k", "fixup! feat: a"):
            self.assertFalse(denied(G + ' -m "%s"' % msg), msg)

    def test_file_flag_denied(self):
        self.assertTrue(denied(G + " -F /tmp/msg.txt"))
        self.assertTrue(denied(G + " --file=/tmp/msg.txt"))
        self.assertTrue(denied(G + " -aF /tmp/msg.txt"))

    def test_variable_message_left_alone(self):
        for cmd in (G + ' -m "$MSG"', G + ' -m "$(git log -1 --format=%s)"', G + " -m `cat f`"):
            out = cm.decide(cmd)
            self.assertIsNotNone(out, cmd)
            self.assertNotIn("hookSpecificOutput", out, cmd)
            self.assertIn("not checked", out["systemMessage"])

    def test_no_message(self):
        self.assertIsNone(cm.decide(G + " --amend --no-edit"))

    def test_unbalanced_quotes_ignored(self):
        self.assertIsNone(cm.decide(G + ' -m "feat: a'))


class HookIO(unittest.TestCase):
    def run_hook(self, payload):
        p = subprocess.run(["python3", HOOK], input=json.dumps(payload).encode(),
                           capture_output=True)
        return p.returncode, p.stdout.decode().strip()

    def test_updated_input_keeps_other_fields(self):
        code, out = self.run_hook({"tool_name": "Bash", "tool_input": {
            "command": G + ' -m "feat: a\nb"', "description": "Commit"}})
        self.assertEqual(code, 0)
        upd = json.loads(out)["hookSpecificOutput"]["updatedInput"]
        self.assertEqual(upd, {"command": G + " -m 'feat: a'", "description": "Commit"})

    def test_bad_input_silent(self):
        p = subprocess.run(["python3", HOOK], input=b"nope", capture_output=True)
        self.assertEqual((p.returncode, p.stdout), (0, b""))


if __name__ == "__main__":
    unittest.main()
