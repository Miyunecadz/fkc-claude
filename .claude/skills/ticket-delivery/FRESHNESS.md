# Freshness — the ticket and the codebase both move

Two silent failures this workflow refuses. Each has its own check, and both are re-run at
four points: **before presenting the Plan, before Implement, before Review, at Handover.**

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

Also check once, at Locate, whether the work already exists: search Jira for the key in
other issues, and look for branches already carrying it —
`git -C <repo> branch -a --list "*<KEY>*"`. A branch someone else pushed is evidence, and
starting a second one is how two half-implementations happen.

Never edit, transition, assign or comment on the issue from this workflow.

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
