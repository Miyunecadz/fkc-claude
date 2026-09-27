# Freshness — the ticket and the codebase both move

Two checks, run at the five points in SKILL §2: the Jira half (§1) and the git half (§2).
The graph (§3) is a third thing and is never a reason to stop.

## 1. The ticket may have moved (Jira)

At Locate, read the issue once in full and record the fingerprint:

```
mcp__jira__jira_get_issue  issue_key=<KEY>  fields="*all"  use_display_names=true  include="comments"
.claude/hooks/ticket-worktree.sh sidecar header <KEY> jira="updated=<fields.updated> status=<fields.status.name>"
```

The fingerprint is the issue's `updated` value and status name, copied exactly. Nothing
else is computed, so any run can reproduce it. An old `fields-sha=` token in the line is
ignored.

**Compare, never re-record.** At each re-check, re-read the issue (same call) and compare
with the sidecar's `jira:` line:

| What changed | What it forces |
|---|---|
| nothing | continue |
| status is `In Code Review` or later | **stop.** Someone may have shipped it. Report; set `ALREADY_IMPLEMENTED` or `NOT_NEEDED` only with evidence |
| `updated` moved, and the newest comment's time equals the new `updated` | read that comment. A delivery comment → stop (below). A requirement stated in it → stop and re-gate. Otherwise continue |
| `updated` moved for any other reason | **stop.** Tell the user the old and new `updated`, and ask whether the requirement changed. A change means re-run Analyse for what changed and re-gate the Plan |
| assignee is now someone else | report before continuing |

Only when the user confirms nothing material changed, record the new value with
`sidecar header <KEY> jira="updated=<new> status=<name>"` and say so in the Log note.

### Delivered already?

`.work/` never leaves this machine, so only Jira and the remote show another dev's work.
Check at Locate and at `/implement-review` entry:

| Signal | Weight |
|---|---|
| a **delivery comment**: strip `\` and `*` from the comment, and its first line is `Delivered — in review`; it ends with a `PR #<id>` footer. Older ones say `fkc-delivery` in plain text instead | **authoritative** — open the PR it names |
| a branch carrying the ticket: `git -C <repo> branch -a --list "*<KEY>*"`, and also `"*FKC-<trello-number>*"` when the Trello number is known (branches carry the Trello number, WORKTREE §1) | strong — a lead to check, not proof |
| status at or past `In Code Review` | corroborating only; humans move tickets by mistake |

This project's status ladder — `Done`, `Closed` and `Cancelled` do not exist here:

```
To Do  →  In Progress  →  In Code Review  →  In Staging  →  Production / Release
```

Only `To Do` and `In Progress` mean the work is still open. Any signal: report what exists
and stop.

## 1a. What this workflow may write to Jira

Never transition, assign or edit a field. One comment is allowed: the delivery comment,
written by `/create-pr` once the PR is open (the `pull-request` skill owns its wording).
Posting it moves `updated`, so `/create-pr` re-reads the issue straight after and runs
`sidecar header <KEY> jira="updated=<new> status=<name>"`.

## 2. The codebase may have moved (git)

```bash
.claude/hooks/ticket-freshness.sh check <KEY> [repo]
.claude/hooks/ticket-freshness.sh sync  <KEY> <repo>     # rebase onto the moved base
```

`check` fetches, then compares the base's tip with `BASE_SHA` recorded at the cut.

| Exit | Verdict | What it forces |
|---|---|---|
| 0 | `FRESH` | continue |
| 4 | `FRESH BASE, graph drift only` | continue. The map is behind the tree (any edit does that); the next query rebuilds it. **Not** a stale base |
| 3 | `STALE BASE` | `/implement-ticket`, tree clean: `sync`, then re-check what Analyse said about the changed files. `/implement-review`: **stop** and ask — the tree holds the dev's edits, `sync` refuses a dirty tree, and a rebase would change what the human read |
| 5 | `UNKNOWN` | **stop** and report the line: not prepared, offline (fetch failed), or the in-place branch is not checked out. Never treat it as fresh |
| 1 | usage or failure | report it |

`sync` refuses a dirty tree and a tree not on the ticket branch. It exits 5 when offline. On
conflicts it aborts and leaves the tree untouched: that is a stop (SKILL §7).

## 3. The graph may describe another commit

Each tree has its own map, and `graph.sh` picks it from the path:

| Mode | Map |
|---|---|
| in-place | `<repo>/graphify-out/graph.json` — it follows whatever branch the checkout is on |
| worktree | `.work/<KEY>/<repo>/graphify-out/graph.json`, stamp in `.work/<KEY>/meta/<repo>.graph` |

At Prepare:

```bash
.claude/hooks/ticket-freshness.sh graph <KEY> <repo>
```

It runs `graph.sh ensure` on the tree (copying the repo's map when the commit matches,
otherwise extracting), then labels it if names are missing. Exit 4 means built but not
labelled: the map answers with community numbers only. Record that in `graph:` and tell the
analyst. It prints the absolute query command.

Query by tree path only, never with `--graph`:

```bash
.claude/hooks/graph.sh query    "$tree" "<question>"
.claude/hooks/graph.sh affected "$tree" "<node>"
```

`graph.sh` re-checks the map against HEAD and the dirty tree on every query and rebuilds it
first (~3s), so it cannot go stale mid-task. An agent that cannot reach the map reads source
instead.

**The graph locates; the file confirms.** Labels may be missing; there are no cross-repo
edges (the API boundary is in SKILL §6); a node proves a symbol exists, not what it does.
