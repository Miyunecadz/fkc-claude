# Worktrees — one isolated checkout per ticket, per repo

The workspace root is not a git repo; each of the three repos is its own. So a ticket that
spans repos gets **one worktree per repo**, all under one ticket directory.

```
.work/<KEY>/fk-admin-panel-be/     branch ticket|feat|fix/<KEY>-<slug>, cut from origin/<base>
.work/<KEY>/fk-admin-panel-fe/
.work/<KEY>/meta/<repo>.env        BASE_REF / BASE_SHA / BRANCH / CREATED
```

Why, rather than branching in place: the user's checkouts keep their branch and their
uncommitted work; two tickets can be in flight at once without stashing; a repo's slice of
a cross-repo change can be built while another repo's slice is being built; and an
unapproved edit cannot reach the code the user is looking at.

## 1. Create — always through the script

```bash
.claude/hooks/ticket-worktree.sh prepare <KEY> <repo> <base> [<branch>]
```

It fetches `origin` first, resolves `<base>` as `origin/<base>` (never the local ref, which
may be days old), cuts the branch there, records what it was cut from, links dependencies
and env files, and prints a fixed metadata block. Re-running it on an existing worktree
reuses it and reprints the block — safe to call on resume.

Do not run `git worktree add` by hand. A relative path passed with `git -C <repo>` resolves
*inside the repo*, which silently creates a worktree in the user's checkout.

Branch name: `<type>/<KEY>-<kebab-summary>` (`feat`, `fix`, `chore`) once the ticket type
is known; the script's default is `ticket/<KEY>`. Pass the real name when you have it.

Other subcommands:

```bash
.claude/hooks/ticket-worktree.sh status <KEY> [repo]   # branch, base, ahead/behind, dirty
.claude/hooks/ticket-worktree.sh list                  # every ticket workspace + state
.claude/hooks/ticket-worktree.sh clean  <KEY> [repo]   # drop build output, keep the code
.claude/hooks/ticket-worktree.sh remove <KEY> [repo] [--force]
```

`remove` refuses while the worktree is dirty or holds unpushed commits, and never deletes
the branch or the sidecar.

`clean` deletes only **untracked** build output (`build`, `dist`, `.next`, `coverage`) from
a worktree that is still in use. A directory git tracks is left alone whatever it is named,
because a tracked `build/` is source. Run it after a build check has been read — the result
lives in the sidecar, not in the directory.

**A worktree is not kept forever.** It costs real disk: `fk-admin-panel-fe`'s `yarn build`
alone leaves ~47M, and a ticket workspace that nobody reaps outlives the ticket by months.
The lifecycle is:

| When | What |
|---|---|
| a build check has been read | `clean <KEY>` — the artifact has done its job |
| the PR is open and the branch is pushed | `/create-pr` offers `remove <KEY>`; the user decides |
| the user declines | it stays — and `list` keeps showing it, so it can be reaped later |

Teardown is still never silent: `remove` is offered, not run unasked, and it refuses
anything dirty or unpushed, so nothing unsaved can be lost by saying yes.

## 2. Choosing the base

`master` and `staging` have **diverged** in `fk-admin-panel-be` — neither contains the
other. `development` is abandoned. Long-lived integration branches exist per work stream
and can be ahead of both for their area. So "does this exist?" has no answer until a branch
is named, and a relationship remembered from a previous ticket is not evidence.

1. The ticket states the affected environment. Map it to a branch from evidence —
   `docs/repo-map.md`, `docs/_shared/env-matrix.md` — then confirm with git.
2. Read current behaviour **in the worktree**, at that base. Never `git checkout` in the
   user's repo to look at another branch.
3. If the ticket depends on something present on another branch but not this base, that is
   a `blocked:` gate, not an implementation detail.

## 3. Dependencies and env files — linked, never installed

`prepare` symlinks `node_modules` and any `.env*` from the main checkout into the worktree,
because a fresh worktree has neither and a React Native install is slow.

- **Never run `yarn install`, `yarn add`, `yarn upgrade` or `npm i` inside a worktree.**
  The link is shared: a write goes into the user's checkout, and two tickets installing at
  once corrupt each other.
- A dependency change is therefore a plan item that says so out loud, executed in the main
  checkout by the user, not a step an agent takes.
- `fk-mobile` has **no** `node_modules` at all, so its `yarn lint` / `yarn test` cannot run
  from a worktree either. Say so; do not promise the check.
- Env files are linked so a build reads the same configuration. Never print their contents.

## 4. Editing rules

- Every edit for a ticket happens under `.work/<KEY>/<repo>/`. An edit under
  `fk-admin-panel-be/`, `fk-admin-panel-fe/` or `fk-mobile/` during ticket work is a
  workflow error, not a shortcut.
- One writer per worktree at a time. Two implementers in the same repo is a race, not
  parallelism.
- Guardrails still apply inside worktrees: the engine fails protective when it cannot
  resolve the repo of a path, so `db/schema.sql`, `.env`, lockfiles and destructive
  commands are blocked here exactly as they are in the main checkout.
- The workspace `docs/<repo>/architecture/` map belongs to the **main checkout's** default
  branch. Never overwrite it from a worktree; a ticket's graph lives in the worktree
  (`FRESHNESS.md` §3).

## 5. Finishing

After review passes, commit **inside the worktree** — one commit per repo, conventional
one-line subject, no body. Do not push and do not open a PR; report the branch and the push
command instead.

That commit is the agent's own step, not the user's. It is allowed here and always was —
the guardrail that used to deny it was resolving "which branch are we on?" against the
invocation cwd (the workspace root, a repo on `main`) instead of the worktree the `git -C`
actually names, so every ticket commit came back denied. Fixed; `block-commit-to-default-branch`
now asks about the directory the command targets. If a commit inside a worktree is denied,
that is a bug to report, not a gate to route around — and never with `--no-verify`.

Then `clean <KEY>` to drop the build output. The worktree itself stays until the PR is
open: it is where the branch is checked out and where a reviewer can still look. `/create-pr`
offers to remove it once the branch is pushed — see §1.
