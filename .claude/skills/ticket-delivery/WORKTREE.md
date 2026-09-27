# Where a ticket's code lives — two modes, chosen by the user

`/implement-ticket` asks which mode before preparing anything. It never picks on its own:
only the user knows whether a second ticket is about to start.

| | in-place | worktree |
|---|---|---|
| branch checked out in | the user's own `<repo>/` | `.work/<KEY>/<repo>/` |
| `.work/<KEY>/` holds | sidecar, meta, logs — no source | those **and** the checkout |
| graph map | `<repo>/graphify-out/` | the worktree's own `graphify-out/` |
| user's branch and dirty work | taken over (clean tree required) | untouched |
| two tickets at once | no — one ticket holds the repo | yes |
| cross-repo built in parallel | no | yes |
| disk | none | a full checkout plus build output (~47M for fe) |

In-place suits one ticket in flight. Anything else, or any doubt: a worktree, which cannot
cost the user their working state. In-place has one more cost: another session querying
that repo mid-ticket gets answers about the ticket branch.

The mode is recorded as `MODE=` in `.work/<KEY>/meta/<repo>.env`, and a ticket keeps it:
switching mid-ticket would move the branch from under the work. Never build the tree path:

```bash
tree=$(.claude/hooks/ticket-worktree.sh tree <KEY> <repo>)
```

## 1. Prepare, branch names, and the other subcommands

```bash
.claude/hooks/ticket-worktree.sh prepare <KEY> <repo> <base> <branch> [--in-place]
```

It fetches, resolves `<base>` as `origin/<base>`, cuts the branch there, records the full
base sha, links dependencies (worktree mode) and prints a fixed block. A re-run reuses what
exists and **warns** if the base, branch or mode given differ from the meta; the recorded
values win.

In-place is **refused** when the checkout is dirty, or when another ticket holds the repo
in-place. A ticket whose state is `PR_OPEN`, or whose meta is `*.env.released`, holds
nothing. Relay a refusal and ask; do not work around it.

Never run `git worktree add` by hand: a relative path with `git -C <repo>` lands inside the
user's checkout.

**Branch name: `<type>/FKC-<trello-number>-<kebab-summary>`** (`feat`, `fix`, `chore`). The
requirement comes from Jira; the branch and commit number come from the **Trello card**.
Never derive the number from the Jira key alone. If the ticket does not link its Trello
card, ask the user for the number. The script's `ticket/<KEY>` default is only a fallback.

```bash
.claude/hooks/ticket-worktree.sh tree    <KEY> <repo>   # where the code lives
.claude/hooks/ticket-worktree.sh status  <KEY> [repo]   # mode, branch, base, ahead/behind, dirty; exit 5 offline
.claude/hooks/ticket-worktree.sh list                   # every ticket workspace, state, mode, blocked
.claude/hooks/ticket-worktree.sh clean   <KEY> [repo]   # drop untracked build output (worktree only)
.claude/hooks/ticket-worktree.sh remove  <KEY> [repo] [--force]   # tear down a worktree, keep the branch
.claude/hooks/ticket-worktree.sh release <KEY> <repo>   # end an in-place hold: meta -> <repo>.env.released
```

- `status` in-place first says whether the ticket branch is still checked out. If not,
  nothing in that repo is this ticket's right now.
- `remove` refuses a dirty worktree or unpushed commits, including a branch with no
  upstream. It never deletes the branch or the sidecar. In-place it only prints the
  `git checkout <PREV_BRANCH>` that gives the user their branch back.
- `release` is for an in-place ticket that is finished with the checkout (for example
  `HANDED_OVER` and waiting). It keeps the meta as `*.env.released` and touches no branch.
- `clean` never deletes anything git tracks, and skips in-place repos.

Lifecycle: `clean` once a build result is recorded; `/create-pr` offers `remove` (worktree)
or the checkout line (in-place) once the PR is open; the user decides.

## 2. Choosing the base

The repos carry `origin/master`, `origin/staging` and `origin/development`, plus feature
branches. The rule:

1. Read the real branches: `git -C <repo> branch -r`. A relationship remembered from an
   earlier ticket is not evidence. In `fk-admin-panel-be`, `master` and `staging` have
   diverged, and `development` is abandoned.
2. Default: cut from `staging`. It is the default PR target.
3. `master` is the release branch. Never cut feature work from it.
4. If the ticket builds on work not yet in `staging`, cut from that feature branch, and say
   so in the plan.
5. Unclear, or inferred rather than stated: ask before `prepare`.

Which tier each branch deploys to: `docs/_shared/env-matrix.md` (confirm against the repo).

Read current behaviour in the tree at that base. Never `git checkout` in a user's repo to
look at another branch. Something the ticket needs that only exists on another branch is a
`blocked:` gate.

## 3. Dependencies and env files — linked, never installed

In worktree mode `prepare` symlinks `node_modules` and any `.env*` from the main checkout.
In-place they are already the real ones. Either way:

- **Never run `yarn install`, `yarn add`, `yarn upgrade` or `npm i` in a tree.** The write
  lands in the user's checkout. A dependency change is a plan item the user does.
- `fk-mobile` has no `node_modules`, so its `yarn lint` and `yarn test` cannot run. Say so.
- Never print env file contents.

## 4. Editing rules

- Edit only under the tree `ticket-worktree.sh tree` names, only for repos in scope, and
  only files the approved plan names. In worktree mode the user's `<repo>/` checkouts are
  off limits.
- One writer per tree. In-place the user is a second writer — which is why
  `/implement-ticket` stops at `IMPLEMENTED`.
- Guardrails apply in every tree: `db/schema.sql`, `.env`, lockfiles and destructive
  commands are blocked as in the main checkout.
- Never write a worktree's map into `<repo>/graphify-out/`.

## 5. Finishing

The commit rules are in SKILL §8. After it, `clean <KEY>` drops build output. A worktree
stays until the PR is open, where the branch is checked out. In-place there is nothing to
reap: once the PR is open, offer the user the `git checkout <PREV_BRANCH>` line and let them
run it.
