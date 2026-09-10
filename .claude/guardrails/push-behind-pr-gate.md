---
name: push-behind-pr-gate
enabled: true
event: bash
pattern: '(^|[;&|]\s*)git(\s+-{1,2}[A-Za-z][A-Za-z-]*(=\S+)?(\s+[^\s-]\S*)?)*\s+push\b'
severity: warn
stacks: [all]
match: argv
surface: agent
---

Pushing puts this branch in front of the team — in this workspace the user decides when work leaves the machine, and they have rejected a background push before. A push is only correct here if the user has just approved it at the `/create-pr` gate, where the branch, destination, commit, title, reviewers and description were shown together.

If that gate has not happened in this session: stop, and run `/create-pr <KEY>` instead. If the user asked for a bare push in their own words, that is their call — proceed.

Also check before you push: the destination is `staging` unless the user chose otherwise (`master` is a release decision), the remote branch has no commits you do not have, and nothing in the diff is a secret. `.claude/hooks/pr-preflight.sh <KEY>` answers all three.

---

**Advisory only.** A `PreToolUse` hook sees the command about to run, not whether an approval gate happened — it cannot verify consent, so it prompts rather than blocks. The real enforcement is the `/create-pr` gate itself and, for the destructive variants, [[protect-default-branch]] (forced pushes) and [[block-commit-to-default-branch]] (a commit or push while standing on trunk), both of which are `block`.

**Surface: `agent` only.** A push is not a commit, so the `pre-commit` surface Lodestar installs cannot see it; the git-layer twin would be a `pre-push` hook. Server-side branch restrictions in Bitbucket are the only version nobody can bypass.
