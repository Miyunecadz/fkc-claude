# Freshness — the ticket and the codebase both move

Two silent failures this workflow refuses. Each has its own check, and both are re-run at
five points across the two commands: **before presenting the Plan and before Implement** in
`/implement-ticket`; **at entry, before Review, and before the commit** in
`/implement-review`.

## 1. The ticket may have moved (Jira)

Jira is the ticket. The copy read at Locate is a snapshot, and a Product Owner editing
acceptance criteria mid-implementation is normal, not exotic.

At Locate, record a fingerprint in the sidecar:

```
jira: updated=<the issue's updated timestamp> status=<name> fields-sha=<8 hex>
```

`fields-sha` is a short hash over summary + description + acceptance criteria + issue type
+ priority — whatever the create-fields actually carry. Compute it however you like; what
matters is that it changes when the requirement changes.

At each re-check, `mcp__jira__jira_get_issue` again and compare:

| Change | What it forces |
|---|---|
| `updated` unchanged | continue |
| `updated` moved, fingerprint identical | note it (a comment, a label); continue |
| summary / description / AC changed | **stop.** Record the diff in `## Freshness`, re-run Analyse for what changed, re-gate the Plan with the user. Never fold a requirement change in silently |
| status moved to Done / Closed / Cancelled | **stop.** Someone else may have shipped it. Report; set `ALREADY_IMPLEMENTED` or `NOT_NEEDED` only with evidence |
| assignee changed to someone else | report before continuing — two people implementing one ticket is worse than a pause |

Also check once, at Locate, whether the work already exists. `.work/<KEY>/` is local and is
never committed, so the local sidecar cannot tell you what another dev did — only Jira and
the remote can. Three signals, in descending order of trust:

| Signal | Written by | Weight |
|---|---|---|
| a **delivery comment** carrying this workflow's marker, a branch, a sha and a PR link | the workflow, at `/create-pr` | **authoritative** — and verifiable, open the PR it names |
| a remote branch carrying the key: `git -C <repo> branch -a --list "*<KEY>*"` | a human or the workflow | strong — someone started this already |
| status past implementation (code review, done, closed) | a human | corroborating only — humans move tickets by mistake, which is the whole reason the comment exists |

Any of them: report what exists and stop. Starting a second implementation of a delivered
ticket is what this check prevents, and it is the normal failure when the dev who did the
work is absent and never pushed.

## 1a. What this workflow may write to Jira

**Never transition, never assign, never edit a field — the description included.** The
description sits inside `fields-sha`, so writing it would trip this file's own "requirement
changed → stop and re-gate the Plan" rule on the workflow's own edit.

**One comment is allowed, at one point:** the delivery comment, written by `/create-pr` once
the PR is confirmed open. It is not decoration — it is the only record of this work that
travels between machines, and the guard every command checks at Locate.

Posting it moves the issue's `updated`. **Re-read the issue immediately afterwards and
rewrite the sidecar's `jira:` header**, or the next freshness check reports drift that the
workflow itself caused.

## 2. The codebase may have moved (git)

```bash
.claude/hooks/ticket-freshness.sh check <KEY> [repo]      # exit 0 fresh, 3 stale
.claude/hooks/ticket-freshness.sh sync  <KEY> <repo>      # fetch + rebase onto the base
```

`check` fetches, then compares the base ref's current tip against `BASE_SHA` recorded when
the worktree was cut, and reports ahead/behind and dirty state per repo.

| Verdict | What it forces |
|---|---|
| `base: fresh` | continue |
| `base: STALE`, before Implement | `sync` — rebase onto the moved base, then rebuild the graph (§3) and re-read anything Analyse asserted about the changed files |
| `base: STALE`, before Review | `sync`, then **re-run validation**. A review against an old base reviews a diff that will not exist after merge |
| `sync` reports conflicts | **stop.** It aborts and leaves the worktree untouched. The base changed under the work — report it and ask; do not resolve conflicts to keep moving |
| worktree dirty at a checkpoint where it should not be | stop and report; changes that are not this ticket's are never absorbed |

`check` also reports whether the **workspace** map (`docs/<repo>/architecture/`) has drifted
from its own checkout, which is what makes that map untrustworthy for anything. It never
rebuilds it — that is `/lodestar-refresh`, and it belongs to the user's checkout.

## 3. The graph may describe another branch

This is the one that produces confident wrong answers. `docs/<repo>/architecture/graph.json`
was built from the main checkout at its default branch. A ticket that targets `staging`, or
any base with commits the map never saw, gets answers about code that is not there.

So the ticket's graph is built **in the ticket's worktree, from the ticket's base**, at
Prepare and again after every `sync`:

```bash
.claude/hooks/ticket-freshness.sh graph <KEY> <repo>
```

- If the worktree HEAD is exactly the commit the workspace map was built from, it copies
  that map instead of re-extracting — same content, no cost.
- Otherwise it runs `graphify extract <worktree> --force --code-only` and records
  `GRAPH_SHA=<worktree HEAD>` so `check` can tell later that the graph and the code have
  drifted apart.
- Query it explicitly, never by default path:

```bash
.claude/hooks/graph.sh query    .work/<KEY>/<repo> "<question>"
.claude/hooks/graph.sh affected .work/<KEY>/<repo> "<node>"
```

`graph.sh` resolves the worktree's own map from that path, so the workspace map cannot be
reached by accident, and it **re-checks freshness on every query** — against HEAD *and* the
dirty working tree, then rebuilds incrementally (~3s) before answering. That closes the
window `check` leaves open: `check` compares HEAD only, so a graph built before three
uncommitted edits still reads `fresh` to it while describing code that is no longer there.
Prefer `graph.sh query` over `graphify query` everywhere for that reason.

Every agent is given this path. An agent that cannot see it reads source instead; falling
back to the workspace map is not allowed, because its answers look identical and are about
a different branch.

**The graph locates; the file confirms.** Community labels are placeholders (the map is
built `--code-only`, no LLM backend), cross-repo edges do not exist in it at all — the API
boundary lives in `docs/_shared/api-contract.md` — and a node's presence is evidence of a
symbol, not of behaviour. Anything that becomes a claim in the sidecar is read in the file
at `path:line` first.
