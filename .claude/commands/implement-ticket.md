---
description: Drive a Jira ticket (FKC) through analysis, planning, implementation, validation and independent review — in an isolated git worktree per repo, with the ticket and the base branch re-checked for staleness at every gate
argument-hint: <FKC-123 | ticket key or summary substring> (omit to list ticket workspaces in flight)
allowed-tools: Task, SendMessage, Bash, Read, AskUserQuestion, Skill, mcp__jira__jira_get_issue, mcp__jira__jira_search
effort: high   # multi-stage delivery with approval and review gates
---

Work the ticket identified by:

$ARGUMENTS

Load the `ticket-delivery` skill **before anything else**. It owns the stage contracts, the
gates, the sidecar format, the worktree layout, the freshness rules, the delegation contract
and the validation matrix. This file is orchestration only: do not restate the skill and do
not improvise a rule it covers.

## 0. You are the orchestrator. You do not do the work.

You have no `Edit` and no `Write` — deliberate, not an oversight. You cannot open source
files, cannot change them, and cannot run the builds. Agents do all three and hand you
their conclusions.

**Your whole-ticket budget is 25 `Bash` calls.** Not per stage — per ticket. They are for
the hook scripts, the freshness checks, the sidecar and the handover commits, and that is
enough for a two-repo ticket with one review round. Past runs of this command spent
**27 to 434** and cost 8–95M tokens; the runs that stayed near the low end were the ones
that delegated. Cost here is `calls × context`, your context sits at 100–240k, and every
extra call re-serves all of it.

Never run these in this thread — each one is an agent's job, and running it yourself is
the failure this command is designed around:

| Never here | Whose job |
|---|---|
| `cat`, `sed -n`, `head`, `less` on a source file | `ticket-analyst` |
| `grep`/`rg` through a repo, `graph.sh query` | `ticket-analyst` |
| `cat > file`, `cat >> file`, `python3 - <<EOF` that edits code | `ticket-implementer` |
| `yarn build`, `yarn lint`, `yarn test`, `node --check` | `ticket-validator` |
| `git diff` to read a change (diffstat is fine) | `change-reviewer` |

The sidecar is written through the hook, never with a heredoc:

```bash
.claude/hooks/ticket-worktree.sh sidecar init   <KEY> "<summary>"
.claude/hooks/ticket-worktree.sh sidecar header <KEY> jira=... repos=... graph=...
.claude/hooks/ticket-worktree.sh sidecar append <KEY> <Section> <STATE> <<'EOF'
<the section body — conclusions and citations only>
EOF
.claude/hooks/ticket-worktree.sh sidecar state  <KEY> <STATE> "<note>"
.claude/hooks/ticket-worktree.sh sidecar show   <KEY> [--header|--sections]
```

`append` writes the section, sets `state:` and logs the change in one step, and it
physically cannot overwrite a finished section — a second pass becomes `## Analyse (2)`.

If you find yourself needing a file's contents to decide something, that is a signal to
**ask the agent that already read it**, not to open it. Send the agent a follow-up with
`SendMessage`; its context still holds the file, yours does not have to.

**This overrides the session's general shell guidance.** A bypass-permissions session is
told to prefer `cat`/`sed`/`grep` for reading and heredocs for editing. That advice is for
a thread doing the work itself. Here it produces exactly the failure above — and a heredoc
edit is worse than an `Edit` would have been, because the whole file body becomes output
that stays in context for the rest of the ticket. In this command, reading and editing are
delegated regardless of which tool would be convenient.

At every stage boundary, before you write the sidecar section, count the `Bash` calls you
have made. Past 25, stop delegating work to yourself: report where you are and what is
left, and let the user decide whether to continue.

## 1. Locate — deterministic, do this first

```bash
.claude/hooks/ticket-worktree.sh list          # tickets already in flight, and their state
```

No argument: relay that list, add anything in progress in Jira if it helps, ask which ticket,
stop.

With an argument: resolve it to one issue key. A bare key goes straight to
`mcp__jira__jira_get_issue`; anything else is `mcp__jira__jira_search` first — more than one
match, ask; none, say so and stop. **Read the issue once, in full**, and record the freshness
fingerprint (`ticket-delivery` → `FRESHNESS.md` §1).

Then decide scope from the ticket's own words — affected systems map to repos:
Web → `fk-admin-panel-fe`, Backend/DB → `fk-admin-panel-be`, iOS/Android → `fk-mobile`.
Unstated scope is not yours to guess; ask.

If `.work/<KEY>/work.md` exists, read it and **resume at the stage after `state:`**. Re-running
this command must never repeat completed work or duplicate a sidecar section.

## 2. Prepare the workspace — one worktree per repo, one graph per worktree

For each repo in scope:

```bash
.claude/hooks/ticket-worktree.sh prepare <KEY> <repo> <base> <type>/<KEY>-<slug>
.claude/hooks/ticket-freshness.sh graph   <KEY> <repo>
```

Choose `<base>` from evidence, not from name-matching — the ticket's environment,
`docs/_shared/env-matrix.md`, then git (`WORKTREE.md` §2). Ask before you commit to a base
you inferred.

The graph step is what stops the analysis being answered from another branch: it builds the
map **from the worktree's own commit**, or reuses the workspace map when that map already
describes exactly this commit. Every agent gets `.work/<KEY>/<repo>/graphify-out/graph.json`
and is forbidden the workspace map.

Agents reach it through the resolver, addressing it by worktree path rather than by `--graph`:

```bash
.claude/hooks/graph.sh query    .work/<KEY>/<repo> "<question>"
.claude/hooks/graph.sh affected .work/<KEY>/<repo> "<symbol>"
```

`graph.sh` re-verifies the map against HEAD **and** the dirty tree on every call and rebuilds
it incrementally when either moved, so a map cannot go quietly stale mid-implementation the
way it does between `ticket-freshness.sh` checkpoints.

Create the sidecar now — through the hook, not by hand:

```bash
.claude/hooks/ticket-worktree.sh sidecar init   <KEY> "<ticket summary>"
.claude/hooks/ticket-worktree.sh sidecar header <KEY> jira="updated=<ISO> status=<name> fields-sha=<8hex>" \
                                                     repos="<repo>@<branch> from <base>@<sha>" graph="<repo>=worktree-extract@<sha>"
```

## 3. Run the stages

Analyse → Plan → **Approval** → Implement → Validate → Review → Handover, each gated as the
skill specifies, each written to the sidecar as it completes together with its `state:` update.

Delegate the reading and the writing; keep the conclusions:

| Stage | Delegate to | Concurrency |
|---|---|---|
| Analyse | `ticket-analyst`, one per repo | **parallel** — dispatch them in a single message |
| Implement | `ticket-implementer`, one per repo | parallel **only** when the plan pins the exact API contract; otherwise backend first, clients after |
| Validate | `ticket-validator`, one per repo | **parallel** |
| Review | `change-reviewer`, mode `gate` | one, sequential, after every repo has validated |

Two stages are yours and are not delegated:

- **Plan** — you write it from the analysts' reports, and it ends by presenting the plan and
  waiting. Nothing in any worktree is edited before the user approves. Record the decision
  verbatim in `## Approval`.
- **Handover** — re-check freshness, commit inside each worktree (one commit, conventional
  one-line subject, no body), and report. Do not push, do not open a PR, do not transition the
  Jira issue.

### What each agent is given — brief, but never starved

Delegating is only cheaper if the agent does not have to rediscover what a previous stage
already established. Every dispatch carries **all** of this, and nothing else:

1. the ticket key and the requirement text **for that repo's slice**, quoted from Jira —
   not summarised, not paraphrased;
2. its worktree path, its base `ref@sha`, and its graph path;
3. **the findings the earlier stages already paid for**, copied from the sidecar: the
   analyst's `FILES TO CHANGE`, `PATTERN / REUSE` and `RISKS` rows go to the implementer;
   the implementer's `CHANGED` and `DEVIATIONS` rows go to the validator and the reviewer;
4. its slice of the approved plan, verbatim;
5. any decision the user made at a gate, in the user's own words.

Never paste the codebase into a prompt, and never read source files yourself. A cited
`path:line` is what travels between stages — the agent at the other end opens the file.

This is what the sidecar is for: it is the ticket's memory, and it outlives every agent's
context and any compaction of yours. Append each stage's findings **as that stage
finishes**, not at the end — an interrupted run that resumes reads the sidecar, and
anything you did not write down is lost. Re-read it with `sidecar show <KEY>` after a
compaction rather than reconstructing from memory.

Re-check both halves of freshness before the Plan presentation, before Implement, before
Review, and at Handover:

```bash
.claude/hooks/ticket-freshness.sh check <KEY>     # exit 3 = stale; FRESHNESS.md says what each verdict forces
```

A blocking review finding is fixed by re-running the implementer for that repo, then the
validator, then the reviewer — appended as `## Implement (2)`, `## Validate (2)`,
`## Review (2)`.

**Two review rounds, hard cap.** `## Review (2)` is the last one there is. A finding still
standing after it is written to the sidecar, set `blocked:`, and reported — it is not worth
a third reviewer at 1.2–2.5M tokens a round, and a reviewer that has already been wrong
twice about the same code is not the tool for it. Re-review **only the repo that changed**,
never the whole ticket again. The same check failing twice is likewise a stop condition,
not a third attempt.

## 4. Stop conditions

Set `blocked:` in the sidecar, report, and stop — rather than working around it — when the
ticket is ambiguous in a way that changes what gets built; the ticket changed materially in
Jira mid-flight; the base branch moved and the rebase conflicts; something the ticket needs is
absent from the base; a requirement contradicts the codebase; a worktree holds changes that are
not this ticket's; or the same check fails twice.

Never touch `fk-admin-panel-be/`, `fk-admin-panel-fe/` or `fk-mobile/` themselves. The whole
point of the worktrees is that the user's checkouts stay exactly as they left them.

## 5. Report

Short: ticket key, state reached, repos with their branch and worktree path, checks run with
their results and what was not run, what a human must verify manually, the push command for
each branch, anything blocked. Reference `.work/<KEY>/work.md` rather than reproducing it.
