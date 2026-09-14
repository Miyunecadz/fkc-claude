# Where a ticket's code lives — two modes, chosen by the user

A ticket's branch is checked out in one of two places, and `/implement-ticket` **asks which
before preparing anything**. Neither is a default the workflow may pick on its own: only the
user knows whether a second ticket is about to start.

| | in-place | worktree |
|---|---|---|
| branch checked out in | the user's own `<repo>/` | `.work/<KEY>/<repo>/` |
| `.work/<KEY>/` holds | sidecar, meta, logs — no source | those **and** the checkout |
| graphify map | the repo's own, **labelled** | extracted per worktree, then labelled |
| user's branch + dirty work | taken over (clean tree required) | untouched |
| two tickets at once | no — one ticket holds the repo | yes |
| cross-repo built in parallel | no | yes |
| disk | none | a full checkout + build output (~47M for fe) |

Pick in-place when one ticket is in flight and the user is happy to work on that branch.
Pick a worktree when anything else is true. When in doubt the worktree is the answer that
cannot cost the user their working state.

**Never assemble the tree path yourself.** `.work/<KEY>/<repo>` is only correct in one mode:

```bash
tree=$(.claude/hooks/ticket-worktree.sh tree <KEY> <repo>)
```

Everything downstream — status, freshness, validation, review, the PR — takes the path from
there. The mode is recorded as `MODE=` in `.work/<KEY>/meta/<repo>.env` at prepare time, and
a ticket keeps the mode it was prepared with: switching mid-ticket would move the branch out
from under work already in progress.

## Worktree mode — one isolated checkout per ticket, per repo

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
.claude/hooks/ticket-worktree.sh prepare <KEY> <repo> <base> [<branch>] [--in-place]
```

It fetches `origin` first, resolves `<base>` as `origin/<base>` (never the local ref, which
may be days old), cuts the branch there, records what it was cut from, links dependencies
and env files, and prints a fixed metadata block. Re-running it on an existing worktree
reuses it and reprints the block — safe to call on resume.

With `--in-place` it checks the branch out in the repo's own checkout instead, and **refuses**
in two cases rather than warning about them:

- the checkout is dirty — switching branches would move the user's uncommitted work;
- another ticket already holds that repo in-place.

Both refusals are correct answers, not obstacles. Relay them and ask; a worktree is always
available and costs the user nothing. In-place also records `PREV_BRANCH`, so the branch the
user was on before can be handed back to them at the end.

Do not run `git worktree add` by hand. A relative path passed with `git -C <repo>` resolves
*inside the repo*, which silently creates a worktree in the user's checkout.

Branch name: `<type>/<KEY>-<kebab-summary>` (`feat`, `fix`, `chore`) once the ticket type
is known; the script's default is `ticket/<KEY>`. Pass the real name when you have it.

Other subcommands:

```bash
.claude/hooks/ticket-worktree.sh tree   <KEY> <repo>   # where this ticket's code lives
.claude/hooks/ticket-worktree.sh status <KEY> [repo]   # mode, branch, base, ahead/behind, dirty
.claude/hooks/ticket-worktree.sh list                  # every ticket workspace + state + mode
.claude/hooks/ticket-worktree.sh clean  <KEY> [repo]   # drop build output, keep the code
.claude/hooks/ticket-worktree.sh remove <KEY> [repo] [--force]
```

In-place changes what the last three mean, because the tree belongs to the user:

- `status` first reports whether the ticket's branch is still the one checked out. It may
  not be — the user is free to switch away, and then nothing in that repo is this ticket's.
- `clean` skips in-place repos: the build output there predates the ticket and is theirs.
- `remove` has nothing to tear down. It prints the `git checkout <PREV_BRANCH>` that hands
  the user their own branch back, and runs nothing.

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
because a fresh worktree has neither and a React Native install is slow. In-place there is
nothing to link — the dependencies and env files are already the real ones — but the rule
below is unchanged, and matters more there: a write goes straight into the user's tree.

- **Never run `yarn install`, `yarn add`, `yarn upgrade` or `npm i` inside a worktree.**
  The link is shared: a write goes into the user's checkout, and two tickets installing at
  once corrupt each other.
- A dependency change is therefore a plan item that says so out loud, executed in the main
  checkout by the user, not a step an agent takes.
- `fk-mobile` has **no** `node_modules` at all, so its `yarn lint` / `yarn test` cannot run
  from a worktree either. Say so; do not promise the check.
- Env files are linked so a build reads the same configuration. Never print their contents.

## 4. Editing rules

- Every edit for a ticket happens under the tree `ticket-worktree.sh tree` names, and
  nowhere else. In worktree mode an edit under `fk-admin-panel-be/`, `fk-admin-panel-fe/` or
  `fk-mobile/` is a workflow error, not a shortcut. In-place one of those *is* the tree for
  one repo — the other two are still out of bounds, and so is any file in that repo that the
  approved plan does not name.
- One writer per tree at a time. Two implementers in the same repo is a race, not
  parallelism. In-place the user is a second writer: they are reading and often tweaking the
  code, which is exactly why `/implement-ticket` stops at `IMPLEMENTED`.
- Guardrails still apply inside worktrees: the engine fails protective when it cannot
  resolve the repo of a path, so `db/schema.sql`, `.env`, lockfiles and destructive
  commands are blocked here exactly as they are in the main checkout.
- In worktree mode the workspace `docs/<repo>/architecture/` map belongs to the **main
  checkout's** default branch: never overwrite it from a worktree; the ticket's graph lives
  in the worktree (`FRESHNESS.md` §3). In-place that map *is* the ticket's map and tracks
  whatever branch the checkout is on — which is the ticket branch while the ticket runs, and
  the user's branch again once they switch back. That is expected, and `graph.sh` rebuilds it
  on the next query either way. It does mean another session querying that repo mid-ticket
  gets answers about the ticket branch — a real cost of in-place, and the reason a second
  ticket has to use a worktree.

## 5. Finishing

After review passes, commit **inside the tree** — one commit per repo, conventional
one-line subject, no body. Do not push and do not open a PR; report the branch and the push
command instead.

In-place, check what is being committed before committing it. The tree is the user's, so
`git status` can show changes that are theirs and not this ticket's; stage the ticket's files
by path rather than with `git add -A`, and if anything unexpected is there, stop and ask.

That commit is the agent's own step, not the user's. It is allowed here and always was —
the guardrail that used to deny it was resolving "which branch are we on?" against the
invocation cwd (the workspace root, a repo on `main`) instead of the worktree the `git -C`
actually names, so every ticket commit came back denied. Fixed; `block-commit-to-default-branch`
now asks about the directory the command targets. If a commit inside a worktree is denied,
that is a bug to report, not a gate to route around — and never with `--no-verify`.

Then `clean <KEY>` to drop the build output. The worktree itself stays until the PR is
open: it is where the branch is checked out and where a reviewer can still look. `/create-pr`
offers to remove it once the branch is pushed — see §1.

In-place there is no worktree to reap and no build output of ours to clean. What the user
gets back instead is their branch: once the PR is open, offer them the `git checkout
<PREV_BRANCH>` that `remove` prints, and leave the running of it to them.
