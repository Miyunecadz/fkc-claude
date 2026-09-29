---
description: Push a reviewed ticket branch and open its Bitbucket pull request — draft, into staging, with one approval gate before anything leaves the machine
argument-hint: <FKC-123 | ticket key> [repo] [destination] · or --checkout <repo> [destination] for a change with no ticket
allowed-tools: Task, Agent, SendMessage, ToolSearch, Bash, Read, AskUserQuestion, Skill, mcp__jira__jira_get_issue, mcp__jira__jira_add_comment, mcp__jira__jira_edit_comment, mcp__bitbucket__bb_get, mcp__bitbucket__bb_post, mcp__bitbucket__bb_put
effort: high   # an outward-facing action behind an approval gate
---

Open the pull request for:

$ARGUMENTS

Load the `pull-request` skill **before anything else**, then read its `BITBUCKET.md`. The
skill owns every rule; this file is the order of steps only. Do not load `DESCRIPTION.md`
or `PIPELINE.md` — `pr-author` reads the first, and the second is not needed to run.

This runs after implementation, validation and review. It does not implement, review or
merge.

## Budget

| Rule | Limit |
|---|---|
| `Bash` calls | 14 for the whole run |
| Bitbucket calls | 5 — the fixed list in `BITBUCKET.md` |
| Diff reads in this thread | 0 — `pr-author` reads it |
| `change-reviewer` runs | 0 — missing review is a stop, not work to pick up |
| Agents running at the report | 0 |

You have no `Edit` and no `Write`. `pr-author` writes the draft; `pr-body.py` shapes it.

`<pr-dir>` below is `.work/<KEY>/pr` for a ticket, or `.work/no-ticket/pr` for `--checkout`.

## 1. Resolve the change

```bash
.claude/hooks/ticket-worktree.sh list && .claude/hooks/pr-preflight.sh <KEY> [repo]
```

Read `.work/<KEY>/work.md` and the Jira issue once with `mcp__jira__jira_get_issue`.
`state:` must be `REVIEWED` or `HANDED_OVER`; earlier → say which stage is missing and stop.
`PR_OPEN` → verify the existing PR, do not open a second.

`state:` is local, so check the issue too — the ticket may have been delivered from
another machine:

| On the issue | Then |
|---|---|
| a delivery comment (skill §10, "Finding it again") | open the PR it names, confirm it is open, report it, **stop** |
| status at or past `In Code Review`, no such comment | ambiguous — report both readings and ask; do not push |
| neither | proceed |

No ticket: `.claude/hooks/pr-preflight.sh --checkout <repo> [destination]`, say there is
no ticket, and get the requirement from the user. Never infer one from the diff.

Preflight exit 1 → relay the `!` lines and stop.

## 2. Draft — dispatch, do not read the diff

Dispatch one `pr-author` per repo, **all in one message**, and wait for all of them. Give
each only: repo, the literal path, branch, destination, the diff range the preflight
printed, the ticket key (or "none"), the Trello card URL from the sidecar's `ticket:`
header (or "none"), and `<pr-dir>`. It writes `<pr-dir>/<repo>.title` and
`<pr-dir>/<repo>.txt` and returns the paths, the title and its flags.

A `stop:` line, a secret flag or an out-of-scope change ends the run — report it.

## 3. Review and validation must be real

- **Review**: the sidecar's `## Review`, or a `change-reviewer` run earlier in this
  session. None, or an unresolved blocking finding → stop and send the user to
  `/implement-review <KEY>`. Never spawn `change-reviewer` here.
- **Validation**: compare the preflight's `branch: <b> @ <sha>` with the sha in
  `## Validate`. Same → the result stands; cite it. Different → dispatch `ticket-validator`
  for that repo only, with the checks affected (`ticket-delivery` → `VALIDATION.md`). A
  check that did not run is never reported as passing.

## 4. Format, then the gate

Run the skill's §5 format-and-title command for each repo, then
`.claude/hooks/ticket-freshness.sh check <KEY>` (exit 3 base moved or 5 unknown → stop; 4 is graph drift only, carry on). Present the skill's
§6 gate block for every repo in one message, and **wait**. Propose draft and `staging`.

## 5. Execute and deliver

Follow skill §7 for each repo (backend first), then §10 (delivery comment and
fingerprint), then §11 (sidecar and report). Never dispatch an agent after the gate.

## 6. Offer to reap the worktree

In the same message as the report, show `du -sh .work/<KEY>/*` and offer
`.claude/hooks/ticket-worktree.sh remove <KEY>`. Offer only — run it when the user says yes.
If it refuses, relay the refusal; never `--force`. In-place tickets and `clean <KEY>` are
covered in `ticket-delivery` → `WORKTREE.md`, section "Finishing".

## Agents

Every agent is awaited and finished before the report. One `pr-author` per repo: a second
is a re-run — say why, or continue the first with `SendMessage`.

Stop conditions: skill §12.
