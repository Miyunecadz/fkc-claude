---
description: Validate, independently review and commit a ticket's implementation after a human has read it — reports blocking findings, never fixes them
argument-hint: <FKC-123 | ticket key> (omit to list ticket workspaces in flight)
allowed-tools: Task, Agent, SendMessage, Bash, Read, AskUserQuestion, Skill, mcp__jira__jira_get_issue
effort: high   # an independent review gate, and the commit
---

Validate and review the implementation for:

$ARGUMENTS

Load the `ticket-delivery` skill first. It owns every rule: states and resume (§3), budget
and the never-here table (§5), stop conditions (§7), commit rules (§8). This file is the
order of steps.

This runs after `/implement-ticket` and after a human has read, and usually tweaked, the
code. **It has no implementer: findings are reported, never fixed.** You have no `Edit` or
`Write`, and you never read source, diffs or logs.

## 1. Locate and gate

```bash
.claude/hooks/ticket-worktree.sh list
.claude/hooks/ticket-worktree.sh sidecar show <KEY> --last Evidence Implement Validate Review
```

No argument: relay the list, ask which ticket, stop.

No sidecar but the branch exists: the work was done on another machine. Say that delivering
it here means `/implement-ticket <KEY>` from the start, and stop.

Gate on `state:` and `blocked:` with SKILL §3.

Re-read the issue (FRESHNESS §1 call) and **compare** it with the sidecar's `jira:` line.
Never re-record it at entry. Stop if the ticket was delivered already or changed (FRESHNESS
§1).

```bash
.claude/hooks/ticket-freshness.sh check <KEY>
```

Exit 0 or 4: continue. Exit 3 or 5: stop and report. At this stage a moved base is a stop,
not a sync (FRESHNESS §2).

## 2. Validate

One `ticket-validator` per repo, all in one message. Give each its tree path and branch, the
implementer's `CHANGED` and `DEVIATIONS` from the last `## Implement`, and the plan's checks.

Append `## Validate` with the combined state from VALIDATION.md: `VERIFIED`, `UNVERIFIED` or
`FAILED_VERIFICATION`. A failure ends the run: report the check and its decisive line, and
the two routes below. `UNVERIFIED` continues to review.

## 3. Review

One `change-reviewer`, mode `gate`, after every repo has validated. Give it **paths only**:
the key, the tree paths and branches, the sidecar path, the round number `<n>` (1 plus the
Review sections so far), and this instruction verbatim:

> Some hunks were written by a human after the implementer finished. Review the full branch
> against its base, including uncommitted work. Judge it against the ticket's acceptance
> criteria, not the plan; a hand change that departs from the plan is not a finding on that
> ground alone. Write your full report to `.work/<KEY>/review/<n>.md`.

When it returns, check that `.work/<KEY>/review/<n>.md` exists (`test -s`). If it does not,
record that in the Review section.

- `VERDICT: PASS` → append `## Review` with `REVIEWED`.
- `VERDICT: FAIL` → append `## Review` with `REVIEW_FAILED` and stop. Give the two routes:
  fix by hand and re-run `/implement-review <KEY>`, or `/implement-ticket <KEY>` for the one
  agent fix round.
- `VERDICT: STALE BASE` → `sidecar state <KEY> BLOCKED "base moved during review"`, stop.

## 4. Commit

Only on `REVIEWED`. Run `ticket-freshness.sh check <KEY>` again (exit 0 or 4 to go on), then
commit per repo by SKILL §8. Append `## Handover` with `HANDED_OVER`.

Do not push, open a PR or touch Jira. Next step is `/create-pr <KEY>`.

## 5. Report

Short: key, state reached, per repo the branch and tree path; the checks that ran with their
results and what did not run and why (say `UNVERIFIED` plainly when it applies); the review
verdict and report path; what a human must still check by hand; the next step; the push
line from SKILL §8.
