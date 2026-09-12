---
name: protect-default-branch
enabled: true
event: bash
pattern: '(^|[;&|]\s*)git(\s+-{1,2}[A-Za-z][A-Za-z-]*(=\S+)?(\s+[^\s-]\S*)?)*\s+push\b[^|;&]*(\s-f\b|--force(?!-with-lease))'
severity: block
stacks: [all]
match: argv
surface: agent
---

A plain `git push --force` (or `-f`) to a shared branch overwrites remote history and can erase teammates' commits. Never force-push to `main`/`master` or any shared branch. If you genuinely need to overwrite your OWN feature branch after a rebase, use `git push --force-with-lease` (which refuses if someone else pushed in the meantime) — never bare `--force`.

---

Scope note: this rule is **force-push-only** — its name once promised more than a regex can deliver. It fires on any branch, since a bare `--force` is wrong on a shared feature branch too, and it deliberately does not try to infer the push destination (a refspec can name any branch; a pattern cannot resolve one). Blocking *ordinary* commits and pushes while you are standing on the default branch is a separate, branch-aware rule: [[block-commit-to-default-branch]]. Enable both for full coverage.

The pattern allows git's own global options between `git` and `push`, so
`git -C <worktree> push -f` is caught the same as a bare `git push -f` — it used to slip
through, and was only ever stopped by [[block-commit-to-default-branch]] firing too
broadly. `match: argv` tests the unquoted words, so an echoed or quoted mention of a
forced push no longer blocks a command that runs nothing.

**Surface: `agent` only.** Force-push happens at push time, not commit time, so the git-layer twin of this rule is a `pre-push` hook rather than the `pre-commit` surface Lodestar installs today. Server-side branch protection (a ruleset that forbids force-push) is the real enforcement for everyone; see `docs/CI.md`.
