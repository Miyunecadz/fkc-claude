---
description: Validate, independently review and commit a ticket's implementation after a human has read it — reports blocking findings, never fixes them
argument-hint: <FKC-123 | ticket key> (omit to list ticket workspaces in flight)
allowed-tools: Task, SendMessage, Bash, Read, AskUserQuestion, Skill, mcp__jira__jira_get_issue
effort: high   # an independent review gate, and the commit
---

Validate and review the implementation for:

$ARGUMENTS

Load the `ticket-delivery` skill **before anything else**. It owns the stage contracts, the
gates, the sidecar format, the worktree layout, the freshness rules, the delegation contract
and the validation matrix. This file is orchestration only: do not restate the skill and do
not improvise a rule it covers.

This runs **after** `/implement-ticket` and after a human has read the code. It is the second
half of the delivery pipeline:

```
/implement-ticket   Analyse → Plan → [approve] → Implement      ends IMPLEMENTED
      ── the dev reads the diff and tweaks it by hand ──
/implement-review   Validate → Review → commit                  ends HANDED_OVER
/create-pr          push → PR → the ticket's delivery comment    ends PR_OPEN
```

## 0. What this command may not do

**It has no `ticket-implementer`, and that is the point.** The dev who reaches this command
has usually just hand-edited the worktree. A command that both checks the code and can
silently rewrite it would put those edits at risk, and would review a version the dev never
saw. So:

- **Findings are reported, never fixed.** A blocking finding ends this run. The dev either
  fixes it by hand and runs this command again, or re-runs `/implement-ticket <KEY>`, which
  has the implementer and the two-round cap (its §3a).
- You have no `Edit` and no `Write`. You do not read source files, diffs or build logs — the
  agents do, and hand you conclusions.

**Budget: 12 `Bash` calls** for the whole run — the freshness checks, the sidecar, the
diffstat and the commits. Reading the diff is `change-reviewer`'s job; running the checks is
`ticket-validator`'s.

| Never here | Whose job |
|---|---|
| `cat`/`sed -n`/`head` a source file, `grep` a repo, `graph.sh query` | `change-reviewer` |
| any write to a source file | nobody in this command — see above |
| `yarn build`, `yarn lint`, `yarn test`, `node --check` | `ticket-validator` |
| `git diff` to read the change (a `--stat` line is fine) | `change-reviewer` |

## 1. Locate and gate

```bash
.claude/hooks/ticket-worktree.sh list          # tickets in flight, and their state
.claude/hooks/ticket-worktree.sh sidecar show <KEY>
```

No argument: relay the list, ask which ticket, stop.

Read the Jira issue once with `mcp__jira__jira_get_issue` and re-record the freshness
fingerprint. A **delivery comment** already on the issue means this ticket was delivered from
another machine: report the PR it names and stop, rather than committing a second
implementation of it. Status at or past `In Code Review` says the same thing more weakly —
the ladder here is `To Do → In Progress → In Code Review → In Staging → Production / Release`,
and there is no `Done` or `Closed` to look for.

Then gate on `state:`:

| `state:` | Then |
|---|---|
| `IMPLEMENTED` | proceed — the normal entry |
| `FAILED_VERIFICATION` | proceed — re-validating after a hand fix. Append as `(2)` |
| `REVIEWED` with standing blocking findings | proceed — re-reviewing after a hand fix. Append as `(2)` |
| `NEW` … `APPROVED`, `IMPLEMENTING` | the change is not ready. Name the missing stage, point at `/implement-ticket <KEY>`, stop |
| `HANDED_OVER` | already reviewed and committed. Point at `/create-pr <KEY>`, stop |
| `PR_OPEN` | already delivered. Report the PR and stop |

**No sidecar at all, but the branch exists?** That is the cross-machine case: `.work/<KEY>/`
never leaves the machine it was made on. Do not reconstruct the earlier stages and do not
guess what was intended — say the ticket has no local work, and that delivering it here means
running `/implement-ticket <KEY>` from the start. Stop.

Re-check the codebase half of freshness before judging anything:

```bash
.claude/hooks/ticket-freshness.sh check <KEY>     # exit 3 = stale
```

A stale base means the reviewer would judge a diff that will not exist after merge. Resolve it
(`FRESHNESS.md` §2) before dispatching anyone.

## 2. Validate

Dispatch `ticket-validator`, **one per repo, all in a single message** so they run
concurrently. Give each one:

- its worktree path and branch;
- the implementer's `CHANGED` and `DEVIATIONS` rows from the sidecar;
- the plan's validation commands.

It writes full output to `.work/<KEY>/validate/<repo>.log` and returns decisive lines only.
`VALIDATION.md` is the only list of checks that exist here — a check that did not run is never
recorded as passing, and a repo with no test framework cannot have passing tests.

Append `## Validate` with `VERIFIED`, or `FAILED_VERIFICATION` if a check failed. A failed
check ends the run: report which one, with its decisive line, and stop. The same check failing
twice is a stop condition, not a third attempt.

## 3. Review

One `change-reviewer`, mode `gate`, after **every** repo has validated. Never two, never in
parallel — reviewing half a change is reviewing the wrong change.

Give it the ticket key, the worktree paths and branches, the sidecar path, mode `gate`, and
one thing more that `/implement-ticket` never had to say:

> Some hunks in this diff were written by a human after the implementer finished. Review the
> full branch against its base, including uncommitted work. Judge it against the ticket's
> acceptance criteria, not against the plan — the plan is intent, and a hand-written change
> that departs from it is not a finding on that ground alone.

That instruction is load-bearing. Without it every hand-tweak reads as an unexplained
deviation and comes back as a false finding.

Append `## Review` with the verdict. `VERDICT: FAIL` with a blocking finding ends the run —
report the findings, tell the dev their two routes (fix by hand and re-run this command, or
`/implement-ticket <KEY>` for the agent fix round), and stop. Do not fix anything.

## 4. Commit

Only on `VERDICT: PASS`. Re-check freshness, then per repo:

- stage **by explicit path** — never `git add -A`, `git add .`, `git commit -a`;
- **one commit**, conventional one-line subject, no body, no trailer;
- nothing to commit (the dev already committed their tweaks) is a normal outcome — say so and
  move on, do not amend their commit.

Do not push, do not open a PR, do not transition the Jira issue: those are the user's call,
and the branch leaves the machine through `/create-pr` and its own approval gate.

Append `## Handover` and set `state: HANDED_OVER`.

## 5. Stop conditions

Set `blocked:` in the sidecar, report, and stop — never work around — when: the ticket carries
a delivery comment or has moved past implementation; the ticket changed materially in Jira;
the base moved and the rebase conflicts; a check failed, or the same check failed twice; the
reviewer returned a standing blocking finding; a worktree holds changes that are not this
ticket's; the reviewer reports `STALE BASE`.

Never touch `fk-admin-panel-be/`, `fk-admin-panel-fe/` or `fk-mobile/` themselves.

## 6. Report

Short: ticket key, state reached, per repo the branch and worktree path, the checks that
actually ran with their results **and what was not run and why**, the review verdict, what a
human must still verify by hand, and the next step — `/create-pr <KEY>`, or the two fix routes
when a finding stands.

Repeat the push warning whenever the work may outlive today:

> `.work/<KEY>/` is local and is never committed. If anyone else may pick this up, push it:
> `git -C .work/<KEY>/<repo> push -u origin <branch>`

Use the sidecar's vocabulary. `VERIFIED` means the applicable checks ran and passed.
`REVIEWED` means the reviewer returned PASS. `HANDED_OVER` means committed in the worktree and
nothing further. None of them mean delivered — nothing is delivered until `/create-pr` opens
the PR and writes the ticket's delivery comment.
