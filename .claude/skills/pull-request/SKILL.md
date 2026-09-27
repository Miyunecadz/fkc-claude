---
name: pull-request
description: Use when turning an implemented, validated and reviewed change in this workspace into a pushed branch and a Bitbucket pull request — committing what is not yet committed, choosing the destination branch, writing a short PR title and description, picking reviewers, and verifying the PR that was created. Covers the ticket worktrees, the Bitbucket Cloud mechanism, the approval gate and the safety rules. Does not implement, review or merge anything.
stacks: [all]
---

# Pull request

Take a change that is already implemented, validated and reviewed and get it onto Bitbucket
as a pull request. Entry point: `/create-pr`. It ends at a verified open PR and a delivery
comment. Not this skill: writing, implementing or reviewing tickets, merging, deploying.

Never wrong about three things: nothing leaves the machine before the user approves (one
gate covers commit, push and PR); the destination is proven, never defaulted; and the
description's shape belongs to `pr-body.py`, not to Claude.

Files next to this one: [`BITBUCKET.md`](./BITBUCKET.md) — API paths and the call budget,
read at run time. [`DESCRIPTION.md`](./DESCRIPTION.md) — read by `pr-author`, not by the main
thread. [`PIPELINE.md`](./PIPELINE.md) — how the formatter and hook work; **not needed at
run time, do not load it** unless you are changing `pr-body.py`.

## 1. Where the change lives

A ticket driven through `/implement-ticket` is already committed on its branch. Which
checkout holds it depends on the mode chosen there (`ticket-delivery` → `WORKTREE.md`):

```
.work/<KEY>/meta/<repo>.env  MODE / BASE_REF / BASE_SHA / BRANCH — what it was cut from
.work/<KEY>/work.md          the sidecar; its `state:` says how far it got
.work/<KEY>/<repo>/          the worktree — worktree mode only; in-place it is <repo>/
```

Never build the path yourself. The preflight prints it as `path:` (or run
`.claude/hooks/ticket-worktree.sh tree <KEY> <repo>`). Then write that path **literally**
in every git command — `git -C /mnt/e/.../.work/FKC-1/fk-admin-panel-be status` — never
`git -C "$tree"` and never `cd`. A shell variable hides the target from the default-branch
guardrail and the command is denied.

In-place, that path is the user's own checkout: changes outside this ticket are a reason to
stop and ask, never to widen the commit.

## 2. Preflight — deterministic, before anything else

```bash
.claude/hooks/pr-preflight.sh <KEY> [repo]              # ticket
.claude/hooks/pr-preflight.sh --checkout <repo> [dest]  # the user's checkout, no ticket
```

It fetches the destination, then prints per repo the path, branch, destination, working
tree, commits, diff range, sensitive-file flags, remote state and the push command. Exit 1
means a human must decide something — relay the `!` lines and stop.

**The main thread never reads the diff.** `pr-author` reads it (one per repo) and returns
the draft plus anything that should stop the PR. Unrelated changes: list them, leave them
where they are, stage only this ticket's files; if they cannot be separated, stop and ask.

## 3. Destination — proven, and `staging` by default

| Situation | Destination |
|---|---|
| Ticket | `BASE_REF` from `.work/<KEY>/meta/<repo>.env`. The preflight prints it |
| No recorded base | the preflight lists the branches HEAD provably descends from. Not exactly one → **ask** |
| User names one | use it, after confirming `origin/<dest>` exists |

Propose **`staging`** and **draft**. `master` and `staging` have diverged in
`fk-admin-panel-be`; `development` is abandoned. A change reaches Production only through a
separate `staging` → `master` PR — say so at the gate.

## 4. Reviewers

None are configured server-side and none are added by default. There is no documented way
here to find "the same author's last PR", so do not guess one. Propose **none**; if the
user names people at the gate, map each name to a UUID from call 2 in `BITBUCKET.md`. A name
not found there is left off and reported — never invent a person or a UUID.

## 5. Title and description

`pr-author` writes two files per repo into the PR directory — `.work/<KEY>/pr/`, or
`.work/no-ticket/pr/` for a `--checkout` run:

```
<repo>.title   one line: the PR title
<repo>.txt     the semantic block, starting at `Ticket:` — Ticket / What / Why / Check
```

The main thread formats and checks them — one call, no LLM:

```bash
.claude/hooks/pr-body.py format -f <pr-dir>/<repo>.txt > <pr-dir>/<repo>.md \
  && .claude/hooks/pr-body.py title -f <pr-dir>/<repo>.title && cat <pr-dir>/<repo>.md
```

Exit 1 names the missing piece. Send it back to **that** `pr-author` with `SendMessage` — it
still has the diff. Never write the missing sentence yourself and never hand-edit the body.

**Ticket line — one source.** A `trello.com` card URL already written on the sidecar's
`ticket:` header line. None there → the draft says `Ticket: none` and the gate asks the user
for the card URL. Given one, re-run `format` with `-t <url>`. Nothing else is the ticket
line: never build a `trello.com` URL from a key, and a Jira link is not the card.

## 6. The approval gate — nothing leaves the machine before this

Present, in one message, per repo, and wait:

```
repo         <repo>            path <literal path>
branch       <branch>  →  <destination>          (draft: yes/no)
commit       <existing sha + subject, or the one-line message to be written>
stage        <exact file list, or "already committed">
excluded     <unrelated files being left alone, or "none">
title        <the checked title>
ticket       <card URL, or "none — paste the Trello card URL to add it">
reviewers    <names the user gave, or "none">
description  <the formatter's output, verbatim>
validation   <checks that ran, with the decisive line; and what did not run>
```

What the user approves is byte-for-byte what gets posted. An edit at the gate goes back
through `pr-author` or `format -t`, then is shown again. No commit, no push, no PR until the
user approves. An approval for one repo is not an approval for the other.

## 7. Execute, checking each step

In order, per repo, all with the literal path:

1. Stage by explicit path, only if something is uncommitted. Commit: one line,
   conventional prefix (`feat:` / `fix:` / `refactor:` / `chore:`), no body, no trailers —
   a hook enforces it.
2. Push: the exact command the preflight printed.
3. Confirm the remote carries the commit — one call, the two hashes must match:
   `git -C <path> ls-remote origin refs/heads/<branch> && git -C <path> rev-parse HEAD`
4. Create the PR with the approved title and the `.md` output, verbatim. If the hook
   denies it, it shows a diff: fix the source and re-run the formatter — never retype.
5. Fetch it back and verify id, repo, source, destination, title, draft and its commits.
   Only then report it as created.

Never amend a pushed commit or rewrite anyone's message. Cross-repo: **backend first**,
then the client, each naming the other in one line under Why. Load `graphql-contract` when
the change crosses the GraphQL boundary.

## 8. Idempotency — a re-run resumes, it never duplicates

| Already true | Then |
|---|---|
| The commit exists and covers the change | do not commit again; do not amend |
| The remote branch exists and is not behind | do not push again |
| A PR exists for this source branch | **do not create a second.** Report its id, state, destination and whether it holds the new commit. Offer `bb_put` for title or description, or a push for commits |
| `## PR` is in the sidecar | created in an earlier run — verify it |
| The issue has a delivery comment (§10) | delivered, maybe from another machine. Verify the PR it names; **never open a second** |
| That comment exists and this run added commits | `jira_edit_comment` on that comment. Never post a second |

## 9. Safety

- Stage by explicit path. Never `git add -A`, `git add .`, `git commit -a`.
- Never discard or rewrite work to make a push go through — no hard reset, stash, forced
  push or branch deletion.
- Never merge, approve or close a PR.
- Secrets (`.env`, `.pem`, `.key`, `.jks`, `.keystore`, `.npmrc`, `credentials.json`, or a
  literal credential): stop and report. Do not commit it and do not remove it silently.
- Never touch the user's checkouts for a ticket that has a worktree.
- Never transition, assign or edit a field of the Jira issue, description included — it
  sits inside the freshness fingerprint. The one write allowed is the delivery comment.

## 10. The delivery comment — after the PR is verified, before the report

Not optional: it is the only record that leaves the machine, and the other commands check
for it. Jira drops HTML comments, escapes `**` and turns square brackets into links — so it
is plain text, lists are in words, and there is no marker:

```
Delivered — in review

<one plain sentence per acceptance criterion: what now happens, in the ticket's words.
No file paths or function names — a Product Owner reads this.>

Not yet on Production. It reaches Production when the PR merges to staging and a separate
staging to master release goes out.

---
<repo> · branch <branch> · commit <sha> · PR #<id> — <url>
checks: <what ran and the result, in words> · not run: <what, and why>
still manual: <what nobody has exercised>
```

The AC sentences restate the reviewer's `ACCEPTANCE CRITERIA` rows in `## Review`.

**Finding it again.** A delivery comment is one whose first non-empty line, with any `\` and
`*` removed, reads `Delivered — in review`, and which names `PR #<id>`. Found → edit that
one with `jira_edit_comment`. Not found → `jira_add_comment`. The footer's sha makes the
claim checkable; a ticket past `In Code Review` that prints `NOT MERGED` was moved by mistake:

```bash
git -C <literal path> merge-base --is-ancestor <sha> origin/staging && echo MERGED || echo "NOT MERGED"
```

**Then refresh the fingerprint.** Posting moved the issue's `updated`. Re-read the issue
with `mcp__jira__jira_get_issue` and record what it returns (`ticket-delivery` FRESHNESS.md):

```bash
.claude/hooks/ticket-worktree.sh sidecar header <KEY> jira="updated=<as read> status=<as read>"
```

If the post fails, say so prominently. The PR stands, but nothing guards the ticket.

## 11. Sidecar and report

Append `## PR` and set `state: PR_OPEN` in one call. Record what actually happened — the
`jira:` line says posted, edited or failed, and whether the fingerprint was refreshed:

```bash
.claude/hooks/ticket-worktree.sh sidecar append <KEY> PR PR_OPEN <<'EOF'
- <repo>: PR #<id> <branch> → <destination>, <draft|ready> — <url>
- commit: <sha> <subject>
- reviewers: <names, or none>
- checks: <what ran, with results> · not run: <what, and why>
- still manual: <what nobody has exercised>
- jira: delivery comment <posted|edited|FAILED: reason>; fingerprint <refreshed|NOT refreshed: reason>
EOF
```

A `--checkout` run has no sidecar; put these lines in the report instead. Then report,
short: PR link, branch → destination, draft state, commit, the checks that ran, and what a
human must still do.

## 12. Stop conditions

Report and stop — do not work round any of these: the platform or remote cannot be
established; the destination is ambiguous; unrelated changes cannot be isolated; secret
material is in the diff; the remote branch has commits you do not have; validation failed
or could not run; review is missing or has unresolved blocking findings; a PR already
exists; the Bitbucket tools are unavailable (then print the title, body, source and
destination for the user to paste, and say the PR was not created).
