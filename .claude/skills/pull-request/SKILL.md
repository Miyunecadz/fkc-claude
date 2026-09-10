---
name: pull-request
description: Use when turning an implemented, validated and reviewed change in this workspace into a pushed branch and a Bitbucket pull request — committing what is not yet committed, choosing the destination branch, writing a short PR title and description, picking reviewers, and verifying the PR that was created. Covers the ticket worktrees, the Bitbucket Cloud mechanism, the approval gate and the safety rules. Does not implement, review or merge anything.
stacks: [all]
---

# Pull request

Take a change that is already implemented, validated and reviewed and get it onto Bitbucket
as a pull request. Entry point: `/create-pr`.

Not this skill: writing tickets (`ticket-writing`), implementing them (`ticket-delivery`),
reviewing them (`change-reviewer`), merging, deploying. It ends at a verified open PR.

Three things this workflow refuses to be wrong about:

1. **Nothing leaves the machine before the user says so.** Pushing is outward-facing. One
   approval gate, and it covers the commit, the push and the PR together.
2. **The destination is proven, never defaulted.** `master` is a release decision here.
3. **The description is short, and its shape is not Claude's job.** A wall of text is not
   thoroughness; it is a reviewer who stops reading. [`DESCRIPTION.md`](./DESCRIPTION.md)
   owns what you write; `.claude/hooks/pr-body.py` owns the shape, deterministically, and
   a hook enforces it at the API call ([`PIPELINE.md`](./PIPELINE.md)).

Mechanism and API paths: [`BITBUCKET.md`](./BITBUCKET.md).

## 1. Where the change lives

A ticket driven through `/implement-ticket` is **committed in its worktree**, not in the
user's checkout:

```
.work/<KEY>/<repo>/          the worktree, branch already committed at Handover
.work/<KEY>/meta/<repo>.env  BASE_REF / BASE_SHA / BRANCH — what it was cut from
.work/<KEY>/work.md          the sidecar; its `state:` says how far it got
```

So the push and the PR happen **from the worktree path**, and `git -C .work/<KEY>/<repo>`
is how every command addresses it. A change in the user's own checkout is the exception,
not the norm — `pr-preflight.sh --checkout <repo>` covers it, and nothing there is staged
or committed without their explicit say-so at the gate.

Never `cd` into a repo and run git relative; always `git -C <path>`.

## 2. Preflight — deterministic, before anything else

```bash
.claude/hooks/pr-preflight.sh <KEY> [repo]              # ticket worktrees
.claude/hooks/pr-preflight.sh --checkout <repo> [dest]  # the user's checkout, no ticket
```

Exit 1 means a human must decide something — relay the `!` lines and stop. It prints, per
repo: the worktree path, branch and HEAD, the destination recorded at cut time, the working
tree split into staged / unstaged / untracked, the commits and changed files the PR would
carry, flags on sensitive files, the remote and platform, the Bitbucket slug, the remote
branch state, and the exact `bb_get` to check for an existing PR.

Then, before staging or pushing anything:

- **Read the diff once**, with the command the script printed — or delegate it to the
  `pr-author` agent, which reads it and returns the draft without putting the diff in
  context. Look for debug output, commented-out code, temporary or generated files,
  dependency changes, migrations, `.env` material, and anything not belonging to this
  ticket.
- **Check for an existing PR** on this source branch. One exists → §8, do not open a second.
- **Unrelated changes**: list them, leave them exactly where they are, stage only this
  ticket's files. If they cannot be separated — same file, mixed hunks — stop and ask.

## 3. Destination — proven, and `staging` by default

| Situation | Destination |
|---|---|
| Ticket worktree | `BASE_REF` from `.work/<KEY>/meta/<repo>.env` — the branch the work was actually cut from. The preflight prints it |
| No recorded base | the preflight lists the branches HEAD provably descends from. If that is not exactly one, **ask** |
| User names one | use it, after confirming `origin/<dest>` exists |

Default and propose **`staging`**. `master` and `staging` have diverged in
`fk-admin-panel-be` and neither contains the other; `development` is abandoned. A PR into
`master` is a release decision, carried by a separate `staging` → `master` PR — say that
plainly at the gate when the ticket's expected result is written as Production behaviour.

**Default to draft.** A PR here is a starting point for discussion, not a finished handoff.
Offer both draft and ready explicitly at the gate rather than assuming.

## 4. Reviewers

No default reviewers are configured server-side, so the API adds none unless you pass them.
Derive the set from the most recent PR into the same destination by the same author
(`BITBUCKET.md`), propose it by name at the gate, and let the user change it. Never invent
a person, and never add someone who appears nowhere in that history.

## 5. Title and description — write the meaning, run the formatter

[`DESCRIPTION.md`](./DESCRIPTION.md) — read it before writing either. In summary: a plain
sentence for the title, no prefix and no ticket key; and four pieces of meaning — `Ticket`,
`What`, `Why`, `Check` — written **once**, inside a budget of 120 words.

Do not hand-shape the Markdown and never re-read your own draft to tidy it. Pipe the
semantic block through the formatter, which owns the shape:

```bash
.claude/hooks/pr-body.py format -f /tmp/pr-draft.txt > /tmp/pr-body.md
```

It orders the sections, normalises spacing, renumbers the checks, drops banned boilerplate
sections and strips any Claude Code attribution. Exit 1 means meaning is missing — supply
it; it will not invent it. A `PreToolUse` hook re-checks the body on the way to Bitbucket
and denies the call if it is not the contract, so a malformed body never reaches a PR.

The posted body is exactly:

```
Ticket: [<card title>](<trello url>)

**What**··
<one short paragraph>

**Why**··
<one short paragraph>

**Check**

1. <verification step>
2. <verification step>
```

`··` is two real spaces — a Markdown hard break. Bitbucket renders the description as
Markdown, so a bare label with the text on the next line collapses into one paragraph and
a numbered list with no blank line above it is swallowed whole. Never hand-type this
shape; the formatter is the only thing that should produce it.

If it will not fit the budget, the PR is too big — say so; do not squeeze the meaning out
to fit. Mechanics and how to change the format: [`PIPELINE.md`](./PIPELINE.md).

## 6. The approval gate — nothing leaves the machine before this

Present, in one message, per repo, and wait:

```
repo         <repo>            worktree <path>
branch       <branch>  →  <destination>          (draft: yes/no)
commit       <existing sha + subject, or the one-line message to be written>
stage        <exact file list, or "already committed">
excluded     <unrelated files being left alone, or "none">
title        <PR title>
reviewers    <names, derived from recent PRs into this destination>
description  <the formatter's output, verbatim — it is short, so show all of it>
validation   <checks that ran, with the decisive line; and what did not run>
```

Run `pr-body.py format` **before** this block, so what the user approves is byte-for-byte
what gets posted. An edit at the gate goes back through the formatter, not into the body by
hand.

No commit, no push, no PR until the user approves. They may edit any field. An approval for
one repo is not an approval for the other.

## 7. Execute, checking each step

In order, per repo: stage by explicit path (only if uncommitted) → commit → push → confirm
the remote branch now carries the commit → create the PR with the approved formatter
output → fetch it back and verify id, repo, source,
destination, title, draft state and the commits it contains. Only then report it as
created.

Never retype or "tidy" the formatter's output on the way into `bb_post` — pass it verbatim.
If the hook denies the call, it says which piece of meaning is missing: add that piece and
re-run the formatter. Do not rewrite the body to satisfy formatting.

Commit message: **one line**, conventional prefix (`feat:` / `fix:` / `refactor:` /
`chore:`), imperative, no body, no trailers. A `PreToolUse` hook enforces this; do not fight
it. Do not amend a pushed commit and never rewrite anyone else's message.

Cross-repo: **backend PR first**, then the client, each naming the other in one line. The
GraphQL schema is the only contract between them and it is unversioned — load
`graphql-contract` when the change crosses that boundary.

## 8. Idempotency — a re-run resumes, it never duplicates

| Already true | Then |
|---|---|
| The commit exists and covers the change | do not commit again; do not amend |
| The remote branch exists and is not behind | do not push again |
| A PR exists for this source branch | **do not create a second.** Report its id, state, destination and whether it already contains the new commit. Offer `bb_put` to update title/description, or a push to add commits |
| `## PR` is already in the sidecar | it was created in an earlier run — verify it instead |

## 9. Safety

- Stage **by explicit path**. Never `git add -A`, `git add .`, `git commit -a`.
- Never discard or rewrite work to make the push go through: no hard reset, no stash, no
  checkout over changed files, no amend of a pushed commit, no forced push, no branch
  deletion. Guardrails block forced pushes and commits on a default branch; do not look for
  a way around them.
- Never merge, approve or close a PR. This workflow opens one.
- **Secrets**: if the preflight flags `.env`, `.pem`, `.key`, `.jks`, `.keystore`, `.npmrc`
  or `credentials.json`, stop and report — do not commit it and do not remove it silently.
- Never touch the user's checkouts (`fk-admin-panel-be/`, `fk-admin-panel-fe/`,
  `fk-mobile/`) for a ticket that has a worktree.
- Never edit, transition, assign or comment on the Jira issue.

## 10. Stop conditions

Report and stop — do not work around any of these: the platform or remote cannot be
established; the destination is ambiguous; unrelated changes cannot be isolated; secret
material is in the diff; the remote branch has commits you do not have; validation failed or
could not run; review is missing or has unresolved blocking findings; a PR already exists;
the Bitbucket tools are unavailable (then output the PR text for manual creation).

## 11. Sidecar and handover

For a ticket, append to `.work/<KEY>/work.md` — never rewrite a section — and set
`state: PR_OPEN`:

```markdown
## PR — <YYYY-MM-DD>
<repo>: PR #<id> <branch> → <destination> (draft) — <url>
commit: <sha> <subject>
reviewers: <names>
still manual: <what nobody has exercised>
```

Then report, short: the PR link, branch → destination, draft state, commit, the checks that
actually ran, and what a human must still do — attach a screenshot, open the paired PR,
exercise a path nobody has. Reference the sidecar rather than reproducing it.
