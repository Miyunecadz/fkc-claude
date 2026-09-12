---
description: Push a reviewed ticket branch and open its Bitbucket pull request — draft, into staging, with one approval gate before anything leaves the machine
argument-hint: <FKC-123 | ticket key> [repo] [destination] · or --checkout <repo> [destination] for a change with no ticket
allowed-tools: Task, Agent, SendMessage, Bash, Read, AskUserQuestion, Skill, mcp__jira__jira_get_issue, mcp__jira__jira_add_comment, mcp__jira__jira_edit_comment, mcp__bitbucket__bb_get, mcp__bitbucket__bb_post, mcp__bitbucket__bb_put
effort: high   # an outward-facing action behind an approval gate
---

Open the pull request for:

$ARGUMENTS

Load the `pull-request` skill **before anything else**. It owns the Bitbucket mechanism, the
destination rules, the title and description convention, reviewer selection, the safety
rules and the idempotency table. This file is orchestration only: do not restate the skill
and do not improvise a rule it covers.

This runs **after** implementation, validation and review. It does not implement, does not
review, and does not merge.

## 0. Budget — this is a short command, keep it short

Measured runs of this command: **3.3–8.1 minutes of machine time** and a median of **5.5M
tokens ($15)**, worst case 23.7M ($56). The wall-clock the user waits on is mostly the
approval gate, which is correct — everything else is overhead worth removing.

| Budget | Why |
|---|---|
| **14 `Bash` calls** for the whole run | the preflight, the freshness check, the formatter, the commit, the push, and the two of §7b. Reading the diff is `pr-author`'s job |
| **5 Bitbucket calls** — 2 before the post, the post, 2 after | the fixed list in `pull-request` → `BITBUCKET.md`. Past runs spent 13–15, surveying PRs unrelated to this branch |
| **0 reviewers spawned** | this command never runs `change-reviewer` — see §3 |
| **0 agents left running** | see §7 |

You have no `Edit` and no `Write`. You do not read the diff, and you do not write the PR
body — `pr-author` writes it to disk and `pr-body.py` formats it.

## 1. Resolve the change

A ticket key in the arguments (the normal case — the work is in its worktree):

```bash
.claude/hooks/ticket-worktree.sh list       # tickets in flight, and their state
.claude/hooks/pr-preflight.sh <KEY> [repo]
```

Read `.work/<KEY>/work.md`, and read the Jira issue once with `mcp__jira__jira_get_issue`.
`state:` must be `REVIEWED` or `HANDED_OVER`. Anything earlier and the change is not ready —
say which stage is missing and stop. `PR_OPEN` means a PR already exists: verify it, do not
open a second.

**Then check the issue itself, because `state:` is local and this ticket may already be
delivered from another machine.** `.work/<KEY>/` is never committed: a colleague who
implemented, reviewed and opened the PR on their laptop leaves no trace on yours, and your
sidecar will happily say `HANDED_OVER` while a PR is already open. That is how one ticket
gets two PRs.

| On the issue | Then |
|---|---|
| a **delivery comment** with this workflow's marker | authoritative. Open the PR it names, confirm it is still open, report it, **stop** |
| status at or past `In Code Review`, **no** comment | ambiguous — a hand-made PR, or a mis-moved ticket. Report both readings and ask; do not push |
| neither | proceed |

The preflight's remote-branch check covers the third case, where someone pushed but never
opened a PR.

No ticket (`--checkout <repo>`): run `.claude/hooks/pr-preflight.sh --checkout <repo>
[destination]`, say in the output that there is no ticket, and get the requirement from the
user. Never infer one from the diff.

Exit 1 from the preflight means a human must decide something — relay the `!` lines and stop.

## 2. Draft, without reading the diff yourself

Per repo in scope, dispatch `pr-author` — in a single message when there is more than one:

Give it only the repo, the worktree path, the branch, the destination, the diff range the
preflight printed, and the ticket key. It reads the diff, **writes the four pieces to
`.work/<KEY>/pr/<repo>.txt` itself**, and returns the path, the title and its flags. The
body never enters this context until the formatter prints it at the gate — where the user
has to see it anyway.

**Dispatch every repo in one message** so they draft concurrently. Sending them one at a
time is the difference between one drafting pass and two, in wall-clock the user watches.

Its draft is **meaning, not Markdown**. Do not reformat it, do not tidy its headings, do
not renumber its checks — that is the formatter's job in §4 and it costs nothing.

Skipping the agent and reading the diff yourself is the failure mode here: it was measured
in 7 of 8 past runs, and it is where the 10–21 `Bash` calls and most of the tokens went.

Its `stop:` line, a secret flag, or an out-of-scope change ends the run here — report it.

## 3. Review and validation must be real

- **Review**: the sidecar's `## Review` section, or a `change-reviewer` run earlier in this
  session. No review evidence, or an unresolved blocking finding → **stop and say which
  stage is missing**. Your own reading of the diff is not a review, and a verdict is never
  invented.

  **Never spawn `change-reviewer` from here.** Reviewing is `/implement-review`'s Review
  stage; a round costs 1.2–2.5M tokens and 2–3 minutes, and one past run spent 4.2M doing
  it three times inside this command. Missing review is a stop condition, not work to pick
  up — send the user to `/implement-review <KEY>`.

- **Validation**: `ticket-delivery`'s `VALIDATION.md` is the only list of checks that exist
  here. Decide whether to re-run **mechanically, not by feel**:

  ```bash
  git -C .work/<KEY>/<repo> rev-parse --short HEAD     # against the sha in ## Validate
  ```

  Same sha → the sidecar's result stands; cite it and move on. Different → dispatch
  `ticket-validator` for **that repo only**, with the specific checks affected. Do not run
  the checks in this thread, and do not re-validate a repo whose code has not moved. A
  check that did not run is never reported as passing — say what could not run and why.

## 4. Format, then the approval gate — nothing leaves the machine before this

Turn the agent's four pieces into the body that will be posted — one command, no LLM:

```bash
.claude/hooks/pr-body.py format -f .work/<KEY>/pr/<repo>.txt > .work/<KEY>/pr/<repo>.md
cat .work/<KEY>/pr/<repo>.md
```

`pr-author` already wrote the `.txt`; you do not create it. If a piece is missing, send
**that agent** a follow-up with `SendMessage` — it still has the diff — rather than
writing the missing sentence yourself from a diff you have not read.

Exit 1 means a piece of meaning is missing (`missing Why section`, `What section is
empty`). Supply that piece and re-run — never edit the body to get past it, and never
invent a ticket link. Show the user this output verbatim at the gate: it is byte-for-byte
what gets posted. A `PreToolUse` hook re-checks it at `bb_post`/`bb_put` and denies the
call if it is not the contract.

Re-check freshness first:

```bash
.claude/hooks/ticket-freshness.sh check <KEY>     # exit 3 = stale
```

Then present the skill's gate block (§6) in one message, per repo, and **wait**. Propose
**draft** and **`staging`**, and say plainly that the change does not reach Production until
a separate `staging` → `master` PR merges. The user may edit any field; an approval for one
repo is not an approval for the other.

## 5. Execute

Stage by explicit path if anything is uncommitted → commit → push → confirm the remote
branch carries the commit → create the PR, passing the formatted body **verbatim** → fetch
it back and verify id, repo, source, destination, title, draft state and its commits. Only
then report it as created.

Cross-repo: backend first, then the client, each naming the other.

## 6. Write the delivery comment on the ticket

**After the PR is verified, before you report.** This is not optional and it is not a
per-run question: the comment is the only record of this work that leaves the machine, and
both other commands check for it before starting. Skip it and the next person to pick up
this ticket implements it a second time.

Post it with `mcp__jira__jira_add_comment` — or `jira_edit_comment` on the existing one if
the marker is already there, so a re-run updates rather than duplicates. `DESCRIPTION.md`
owns the wording; the shape is two audiences in one comment:

```
<!-- fkc-delivery:<KEY> -->
**Delivered — in review**

<one plain sentence per acceptance criterion: what now happens, in the ticket's own
language. No file paths, no function names — a non-technical reader is the audience.>

Not yet on Production. This reaches Production when the PR merges to `staging` and a
separate `staging` → `master` release goes out.

---
<repo> · `<branch>` · commit `<sha>` · PR #<id> — <url>
checks: <what actually ran, with results> · not run: <what, and why>
still manual: <what nobody has exercised>
```

The AC sentences come from the reviewer's `ACCEPTANCE CRITERIA` rows in the sidecar's
`## Review`, restated for a PO. The footer is the machine-checkable half — that is what
makes a mistakenly-moved ticket recoverable:

```bash
git -C <repo> merge-base --is-ancestor <sha> origin/staging && echo MERGED || echo "NOT MERGED"
```

Then **re-read the issue and rewrite the sidecar's `jira:` header**. Your own comment moved
its `updated`; without this the next freshness check reports drift you caused
(`FRESHNESS.md` §1a).

Never transition the issue, never assign it, never touch its description — the description
is inside `fields-sha`, and writing it would trip the workflow's own requirement-changed
stop.

If the post fails, **say so prominently** in the report. The PR stands, but the ticket is
delivered with no shared record, and the next dev has no guard.

## 7. Report

Short: PR link, branch → destination, draft state, commit, the checks that actually ran, and
what a human must still do — attach a screenshot, open the paired PR, exercise a path nobody
has. Append `## PR` to the sidecar and set `state: PR_OPEN` — through the hook, in one call:

```bash
.claude/hooks/ticket-worktree.sh sidecar append <KEY> PR PR_OPEN <<'EOF'
- <repo>: PR #<id> <branch> → <destination>, draft — <url>
- checks: <what ran, with results> · not run: <what, and why>
- jira: delivery comment posted, fingerprint refreshed
EOF
```

## 7b. Offer to reap the worktree

The branch is pushed and the PR holds the work, so the worktree is no longer the only copy
of anything — and a ticket workspace nobody reaps outlives the ticket by months. Show its
size and offer teardown, in the same message as the report:

```bash
du -sh .work/<KEY>/*                                  # what it is costing
.claude/hooks/ticket-worktree.sh remove <KEY>         # only after the user says yes
```

**Offer, never run it unasked** — deleting a checkout is the user's call, so this is a
question in the report, not a step in the pipeline. Declining is a normal outcome; `list`
keeps showing it, so it can be reaped later. If `remove` refuses (dirty, or unpushed
commits), relay the refusal — never reach for `--force`. `WORKTREE.md` §1 owns the rest,
including `clean <KEY>` for the user who wants the disk back but not the checkout.

## 8. No agent outruns the report

Every agent you dispatch must be **awaited and finished before you report**. Concretely:

- Dispatch `pr-author` for all repos in one message, then wait for all of them. Do not
  start pushing one repo while another is still drafting.
- **Never dispatch an agent after the approval gate.** By then the only work left is push,
  post and verify — none of it belongs to an agent, and an agent started there is still
  running while the user is already looking at a finished PR.
- If a stage's agent is still running when you are otherwise ready, say so and wait. Do not
  report a PR as done with work still in flight behind it — that is what makes a finished
  run look unfinished.
- One agent per repo per stage. A second `pr-author` for a repo that already has a draft is
  a re-run, not a retry: say why, or use `SendMessage` to continue the first one.

## Stop conditions

The platform or remote cannot be established; the destination is ambiguous; unrelated
changes cannot be isolated; secret material is in the diff; the remote branch has commits
you do not have; validation failed or could not run; review is missing or has unresolved
blocking findings; a PR already exists; the Bitbucket tools are unavailable — then output
the PR text for manual creation. Report and stop; do not work around any of these.
