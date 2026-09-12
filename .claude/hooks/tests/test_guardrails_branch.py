#!/usr/bin/env python3
"""Regression tests for `only_on_default_branch` and the force-push rule.

The bug these pin down: the engine answered "which branch are we on?" about the hook's
invocation cwd, never about the directory a `git -C <path> …` actually targets. This
workspace root is itself a repo on `main`, so *every* commit and push issued from the
root — including the ticket-worktree commits the delivery workflow is built around — was
denied by `block-commit-to-default-branch`. The agent could not commit its own work.

Fixing that exposed a second defect: `protect-default-branch` matched only a bare
`git push --force`, so `git -C <worktree> push -f` had been slipping past it all along,
stopped only by the over-broad rule above. Both are covered here.

Run: python3 .claude/hooks/tests/test_guardrails_branch.py
"""

import json
import os
import subprocess
import sys
import tempfile

HOOKS = os.path.dirname(os.path.abspath(__file__ + "/.."))
PROJECT = os.path.abspath(os.path.join(HOOKS, "..", ".."))
HOOK = os.path.join(HOOKS, "lodestar-guardrails.py")

GIT_ENV = dict(
    os.environ,
    GIT_AUTHOR_NAME="t",
    GIT_AUTHOR_EMAIL="t@t",
    GIT_COMMITTER_NAME="t",
    GIT_COMMITTER_EMAIL="t@t",
)


def git(cwd, *args):
    subprocess.run(["git", "-C", cwd] + list(args), check=True, env=GIT_ENV,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def build_fixture(root):
    """A workspace root repo on `main`, plus a nested worktree on a feature branch.

    Mirrors the real layout: <root> is a repo on its default branch, <root>/.work/K/repo
    is a worktree of <root>/repo checked out on a feature branch.
    """
    git(root, "init", "-q", "-b", "main", ".")
    # A throwaway repo has no `origin/HEAD`, so the engine would fall through to the
    # machine's global `init.defaultBranch`. Pin it locally so the fixture asserts the
    # rule, not whatever this machine happens to be configured with.
    git(root, "config", "init.defaultBranch", "main")
    open(os.path.join(root, "README"), "w").write("x\n")
    git(root, "add", "README")
    git(root, "commit", "-qm", "init")

    repo = os.path.join(root, "repo")
    os.makedirs(repo)
    git(repo, "init", "-q", "-b", "master", ".")
    git(repo, "config", "init.defaultBranch", "master")
    open(os.path.join(repo, "f"), "w").write("y\n")
    git(repo, "add", "f")
    git(repo, "commit", "-qm", "init")

    wt = os.path.join(root, ".work", "K-1", "repo")
    os.makedirs(os.path.dirname(wt))
    git(repo, "worktree", "add", "-q", "-b", "feat/K-1-x", wt)
    return repo, wt


def decision(command, cwd):
    """(decision, rule-name) the hook returns for this command."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd})
    proc = subprocess.run(["python3", HOOK], input=payload, capture_output=True, text=True,
                          env=dict(os.environ, CLAUDE_PROJECT_DIR=PROJECT))
    out = proc.stdout.strip()
    if not out:
        return "allow", ""
    data = json.loads(out)
    spec = data.get("hookSpecificOutput", {})
    reason = spec.get("permissionDecisionReason", "")
    rule = reason.split("]")[0].lstrip("*[") if reason.startswith("**[") else ""
    return ("deny" if spec.get("permissionDecision") == "deny" else "allow"), rule


def main():
    with tempfile.TemporaryDirectory() as root:
        root = os.path.realpath(root)
        build_fixture(root)

        cases = [
            # The regression: work inside a ticket worktree is on a feature branch, and
            # must be allowed even though the invocation cwd is a repo on its default.
            ("worktree commit, relative path", "git -C .work/K-1/repo commit -m 'feat: x'", "allow", ""),
            ("worktree push, relative path", "git -C .work/K-1/repo push -u origin feat/K-1-x", "allow", ""),
            ("worktree commit, absolute path", "git -C %s/.work/K-1/repo commit -m 'feat: y'" % root, "allow", ""),
            ("worktree commit, quoted path", 'git -C ".work/K-1/repo" commit -m "fix: z"', "allow", ""),
            # Still blocked: the rule must keep catching real trunk commits.
            ("bare commit at root (main)", "git commit -m 'chore: x'", "deny", "block-commit-to-default-branch"),
            ("commit in checkout on master", "git -C repo commit -m 'feat: x'", "deny", "block-commit-to-default-branch"),
            ("push in checkout on master", "git -C repo push origin master", "deny", "block-commit-to-default-branch"),
            # Several targets stays protective: one on trunk is enough to fire.
            ("mixed targets, one on trunk",
             "git -C .work/K-1/repo commit -m a && git -C repo commit -m b", "deny",
             "block-commit-to-default-branch"),
            # Force-push must be caught by its OWN rule, not as a side effect.
            ("force push to a worktree", "git -C .work/K-1/repo push -f origin feat/K-1-x",
             "deny", "protect-default-branch"),
            ("--force to a worktree", "git -C .work/K-1/repo push --force origin feat/K-1-x",
             "deny", "protect-default-branch"),
            ("--force-with-lease is allowed",
             "git -C .work/K-1/repo push --force-with-lease origin feat/K-1-x", "allow", ""),
            # Text that runs nothing is not an invocation.
            ("echoed commit is not a commit", "echo 'run git commit later'", "allow", ""),
        ]

        fails = 0
        for name, cmd, want, want_rule in cases:
            got, rule = decision(cmd, root)
            ok = got == want and (not want_rule or rule == want_rule)
            fails += 0 if ok else 1
            print("%-4s %-34s want=%-5s got=%-5s %s" % ("PASS" if ok else "FAIL", name, want, got, rule))

        print("\n%d failure(s)" % fails)
        return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
