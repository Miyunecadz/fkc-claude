---
name: ticket-delivery
description: Use when implementing, validating or reviewing the work for a Jira ticket (FKC) in this workspace — driving it from analysis through planning, implementation, validation and independent review. Owns the stage contracts and gates, the per-ticket worktree workspace, the .work/<KEY>/work.md state sidecar, the ticket- and codebase-freshness gates, and what validation actually exists here. Does not write tickets, does not push, does not deploy.
stacks: [all]
---

# Ticket delivery

Carry a Jira ticket to a validated, reviewed, committed change on a branch. Two commands,
with a human pause between them:

```
/implement-ticket   Locate (+images) → Prepare → Analyse → Plan → [approve] → Implement   ends IMPLEMENTED
      ── the dev reads the diff, and normally tweaks it by hand ──
/implement-review   Validate → Review → Handover (commit)                                 ends HANDED_OVER
/create-pr          push → PR → the ticket's delivery comment                             ends PR_OPEN
```

This skill is the one owner of the rules. The commands are orchestration and point here.
Not this skill: writing tickets (`ticket-writing`), pushing or the PR (`pull-request`),
deploying.

Four things this workflow refuses to be wrong about:

1. **The ticket may have moved.** Jira is the ticket; a copy read an hour ago is a memory.
2. **The codebase may have moved.** A branch cut yesterday describes code that may no
   longer be what the work merges into.
3. **The main thread cannot hold the codebase.** Reading is delegated; conclusions come
   back, file bodies do not.
4. **The work may not be on this machine.** `.work/<KEY>/` is local and never committed.
   Jira is the only record that travels, which is why `/create-pr` writes a delivery
   comment and both commands check for one first ([`FRESHNESS.md`](./FRESHNESS.md) §1).

## 1. The ticket workspace

```
.work/<KEY>/work.md                 state sidecar — the only file the main thread writes
.work/<KEY>/meta/<repo>.env         MODE / BASE_REF / BASE_SHA (full sha) / BRANCH / PREV_BRANCH
.work/<KEY>/meta/<repo>.env.released  an in-place hold that was released; holds nothing
.work/<KEY>/meta/<repo>.graph       stamp of the worktree's map (worktree mode)
.work/<KEY>/validate/<repo>.log     full check output — never pasted into context
.work/<KEY>/review/<round>.md       full reviewer report — never pasted into context
.work/<KEY>/<repo>/                 the checkout — worktree mode only
```

The code lives in one of two places, chosen by the user per ticket: a **worktree** under
`.work/<KEY>/<repo>/`, or **in-place** in the user's own `<repo>/`. Never build the path.
Ask for it:

```bash
tree=$(.claude/hooks/ticket-worktree.sh tree <KEY> <repo>)
```

Modes, trade-offs, base choice, branch names and dependencies: [`WORKTREE.md`](./WORKTREE.md).

**The sidecar is written only through the hook.** The main thread has no `Edit` or `Write`.

```bash
.claude/hooks/ticket-worktree.sh sidecar init   <KEY> "<summary>"
.claude/hooks/ticket-worktree.sh sidecar header <KEY> jira="updated=<ISO> status=<name>" repos="..." graph="..."
.claude/hooks/ticket-worktree.sh sidecar append <KEY> <Section> <STATE> [--note "<log line>"] <<'EOF'
<body — conclusions and path:line citations>
EOF
.claude/hooks/ticket-worktree.sh sidecar state  <KEY> <STATE> ["<note>"]
.claude/hooks/ticket-worktree.sh sidecar state  <KEY> BLOCKED "<what is missing, who can answer>"
.claude/hooks/ticket-worktree.sh sidecar show   <KEY> --header | --sections | --last [Section...]
```

- `append` adds the section above `## Log`, sets `state:`, clears `blocked:` and logs it,
  in one step. A repeated name becomes `Implement (2)`. A finished section cannot be
  rewritten.
- `BLOCKED` is a flag, not a state. It sets `blocked:` and leaves `state:` alone. The next
  `append` with a real state clears it.
- `append ... Implement` is refused once the current plan has two Implement sections (the
  build and one fix round). A new `## Approval` starts a new count.
- Body lines starting `# ` or `## ` are demoted to `### `, so they cannot pose as sections.
- Read it back with `show --last` (header plus the last section of each name; default
  `Implement Review`). Use a bare `show` only when a human asks for the whole file.

**Sidecar shape** — the header, then sections in the order they happened:

```markdown
# Work — FKC-123
ticket:   FKC-123 — <summary>
jira:     updated=<the issue's updated> status=<name>
state:    <one state from §3>
blocked:  - | <one line: what is missing and who can answer it>
repos:    <repo>@<branch> from <base-ref>@<sha> (<mode>); ...
graph:    <repo>=<source>@<sha>; ...

## Locate — <date>      scope, user decisions at Locate, delivered-already checks (optional)
## Evidence — <date>    image rows and the attachment manifest, or NONE
## Analyse — <date>     one block per analyst report
## Plan — <date>
## Approval — <date>    the user's decision, verbatim
## Implement — <date>   implementer CHANGED / DEVIATIONS / NOT DONE per repo
## Validate — <date>    prepared vs observed (VALIDATION.md)
## Review — <date>      verdict, AC rows, blocking findings, report path
## Handover — <date>    commits per repo
## PR — <date>          written by /create-pr
## Log                  every state change, one timestamped line
```

`## Decisions` and `## Freshness` are also used when a gate needs one. Old sidecars may
carry `fields-sha=` in `jira:`; ignore it.

Rules: write each stage down **as it finishes**. Store decisions and evidence (`path:line`,
a sha, one decisive output line), not prose, not ticket text, not diffs.

## 2. Stages and gates

| Stage | Who | Produces | State after | Gate |
|---|---|---|---|---|
| Locate | main thread | the issue read once in full; fingerprint; scope | `NEW` | issue exists, not delivered already (FRESHNESS §1), affected systems named |
| Evidence | main thread + `screenshot-requirement-analysis` | image rows and attachment manifest in `## Evidence` | `NEW` | every image inventoried. An image that contradicts the text, or an illegible region that changes the build, is a §7 stop |
| Prepare | `ticket-worktree.sh prepare` + `ticket-freshness.sh graph` | the tree per repo, cut from the fetched base | — | every repo in scope has a tree |
| Analyse | `ticket-analyst`, one per repo, parallel | current behaviour, files to change, unknowns, conflicts | `ANALYSED` | no material unknown; nothing needed is missing from the base |
| Plan | main thread | files per repo, pattern, order, contract, checks, out of scope | `PLANNED` | — |
| **Approval** | the user | the decision, verbatim | `APPROVED` or `NOT_APPROVED` | **nothing is edited before this** |
| Implement | `ticket-implementer`, one per repo | the change | `IMPLEMENTING` → `IMPLEMENTED` | plan followed, or the deviation recorded |
| **Human read** | the dev | their own tweaks | `IMPLEMENTED` | `/implement-ticket` ends here |
| Validate | `ticket-validator`, one per repo, parallel | prepared vs observed checks | `VERIFIED`, `UNVERIFIED` or `FAILED_VERIFICATION` | no check failed |
| Review | `change-reviewer`, mode `gate`, one | verdict, one row per AC | `REVIEWED` or `REVIEW_FAILED` | verdict PASS |
| Handover | main thread | one commit per repo | `HANDED_OVER` | — |

**The reviewer reports; it never fixes.** `/implement-review` has no implementer, so the
dev's hand edits are never rewritten under them. A failed review leaves two routes: fix by
hand and re-run `/implement-review`, or re-run `/implement-ticket` for one agent fix round.

**Fix rounds: one per approved plan.** The hook refuses a third Implement section. A finding
still standing after the fix round is recorded with `sidecar state <KEY> BLOCKED` and goes
to the user.

**Judge against the acceptance criteria, not the plan.** Once a human has edited the code the
plan no longer describes it. The AC is the yardstick that survives.

**Freshness is checked at five points** — what each command actually does:

| Point | Jira half | Git half |
|---|---|---|
| `/implement-ticket` Locate | read in full, fingerprint recorded | — |
| `/implement-ticket` before presenting the Plan | — | `check` |
| `/implement-ticket` before Implement | re-read and compare | `check` |
| `/implement-review` entry | re-read and compare, never re-record | `check` |
| `/implement-review` before the commit | — | `check` |

What each verdict forces: [`FRESHNESS.md`](./FRESHNESS.md).

## 3. States — the one resume table

`state:` holds exactly one of these. `blocked:` is separate (§1).

| State | Means | `/implement-ticket` | `/implement-review` |
|---|---|---|---|
| `NEW` | Located; maybe Evidence written | continue from the first missing section | not ready: point at `/implement-ticket`, stop |
| `ANALYSED` | analyst reports recorded | write the Plan | not ready, stop |
| `PLANNED` | plan written, not approved | present the plan again, wait | not ready, stop |
| `APPROVED` | user approved | Implement | not ready, stop |
| `IMPLEMENTING` | a run died mid-Implement | run `status`; re-dispatch the repos with no Implement row | not ready, stop |
| `IMPLEMENTED` | code written, nothing judged | nothing to do: point at `/implement-review` | **normal entry**: Validate |
| `FAILED_VERIFICATION` | a check failed | fix round | re-validate (the dev fixed it by hand) |
| `UNVERIFIED` | checks ran clean but none could speak to the change, or none exist (`fk-mobile`) | point at `/implement-review` | Review, then say plainly nothing automated verified it |
| `VERIFIED` | every applicable check ran and passed | point at `/implement-review` | re-validate (the tree may have moved), then Review |
| `REVIEW_FAILED` | reviewer returned FAIL | fix round | re-validate, then re-review (the dev fixed it by hand) |
| `REVIEWED` | reviewer returned PASS; not committed | point at `/implement-review` | re-check git freshness, then commit |
| `HANDED_OVER` | committed in the tree | stop: point at `/create-pr` | stop: point at `/create-pr` |
| `PR_OPEN` | PR open, delivery comment written | stop | stop |
| `NOT_NEEDED`, `ALREADY_IMPLEMENTED`, `NOT_APPROVED` | ended without a change, reason in the last section | report the reason, stop. Restart only if the user asks | same |

`blocked:` set, in any state: report it, ask whether it is resolved, and only then continue
from `state:`. An old sidecar with `state: BLOCKED` pre-dates the flag: read the last real
state from `## Log` and ask.

## 4. What runs in parallel, and what never does

| Parallel | Because |
|---|---|
| Analyse, one agent per repo | read-only, independent codebases |
| Implement, one per repo — **only when the plan pins the exact API contract** | separate trees and branches |
| Validate, one per repo | the checks share no state |

Never at the same time: two writers in one tree; client code against an unpinned contract
(the backend goes first — load `graphql-contract`); more than one reviewer, or review before
every repo has validated; anything in a user checkout the ticket was not given in-place.

## 5. Context discipline

The main thread reads the Jira issue, the sidecar and the agents' reports. It never reads
source, diffs or build logs.

**Budget:** `/implement-ticket` 25 `Bash` calls, `/implement-review` 15, per run. Count at
each stage boundary. Past it, stop, report where you are and what is left, and let the user
decide. This overrides the session's general advice to read with `cat` and edit with
heredocs: here, reading and editing are always delegated.

| Never in the main thread | Owner |
|---|---|
| `cat`/`sed -n`/`head` on a source file, `grep` a repo, `graph.sh query` | `ticket-analyst` (or `change-reviewer` in review) |
| any write to a source file (`cat >`, `python3 - <<EOF`, an editor) | `ticket-implementer` |
| `yarn build`/`lint`/`test`, `node --check` | `ticket-validator` |
| `git diff` to read the change (`--stat` is fine) | `change-reviewer` |
| `mcp__jira__jira_download_attachments` (returns base64 into context) | `ticket-analyst` |

Need a file's contents to decide? **`SendMessage` the agent that read it.** Its context still
holds the file. Do not open it, and do not spawn a fresh agent to read it again.

Every agent: returns conclusions with `repo path:line` citations, never file bodies, diffs
or logs; stays near 40 lines; says `UNKNOWN — REQUIRES VERIFICATION` rather than filling a
gap; edits only inside the tree it was given; never commits.

### What each dispatch carries

| Stage | Receives |
|---|---|
| Analyse | ticket key; that repo's requirement text **quoted**; tree path; base `ref@sha`; that repo's `## Evidence` rows verbatim (marked as what a screenshot showed) and the attachment manifest |
| Implement | its plan slice verbatim; the analyst's `FILES TO CHANGE`, `PATTERN / REUSE`, `MISSING FROM THIS BASE`, `RISKS`; user decisions in their own words; tree path |
| Fix round | the failing AC rows and blocking findings from the last `## Review`, verbatim; tree path |
| Validate | tree path, branch; the implementer's `CHANGED` and `DEVIATIONS`; the plan's checks |
| Review | **paths only**: key, tree paths and branches, sidecar path, round number, mode `gate`. The reviewer reads Jira, the sidecar and the diff itself |

Requirement text and user decisions travel quoted, never summarised. A `path:line` travels
instead of the file.

## 6. Evidence and existing code

- The requirement comes from Jira. A gap goes back to the requester.
- A claim about current behaviour comes from code read **in the tree**, at its base.
- `graph.sh query <tree> "<question>"` locates; the file at `path:line` confirms. Never
  pass `--graph`. Community names come from graphify's labelling pass (claude CLI) and may
  be missing; the map has no cross-repo edges.
- Reuse → extend → compose → refactor → create. Confirm the thing exists on this base.
- The API contract: `docs/_shared/api-contract.md` to find your way, the code to confirm —
  backend `fk-admin-panel-be/src/typedefs/*.typedef.js`
  (merged in `index.js`), `src/resolvers/`, permissions in `src/configs/shield.js` and
  `src/utils/permissions/`; client operations in `fk-admin-panel-fe/src/graphql/` and
  `fk-mobile/src/graphql/`. Migrations: `fk-admin-panel-be/db/migrations/`.
- When writing a repo's code, load its standards skill (`backend-standards`,
  `frontend-standards`, `mobile-standards`) and nothing else, plus `graphql-contract` when
  the change crosses the API.

## 7. Stop conditions

Set `blocked:`, report, and stop — never work around it — when:

- the ticket is ambiguous in a way that changes what gets built, or an image contradicts
  the text, or an illegible region would change the build;
- the ticket was delivered already, or its status is at or past `In Code Review`;
- the Jira issue changed mid-flight (FRESHNESS §1);
- something the ticket needs is absent from the base, or a requirement contradicts the code;
- the base moved and `sync` conflicts, or the base moved during `/implement-review`
  (FRESHNESS §2);
- a freshness check says `UNKNOWN`;
- a tree holds changes that are not this ticket's;
- the same check fails twice, or a finding stands after the fix round.

Never stash, reset, check out over or discard anything in a user's checkout.

## 8. Handover

Only after `VERDICT: PASS`, in `/implement-review`. Per repo, inside the tree:

- stage **by explicit path** — never `git add -A`, `git add .` or `git commit -a`; in-place,
  anything in `git status` that is not this ticket's is a stop;
- **one commit**, one-line conventional subject, no body, no trailer; the branch and commit
  number follow the branch name (WORKTREE §1), not the Jira key;
- use a literal `git -C <tree> ...`; a denied commit inside a tree is a bug to report, never
  a reason for `--no-verify`;
- nothing to commit (the dev already committed) is normal: say so, never amend their commit.

Never push, open a PR or change the Jira issue here. Those go through `/create-pr` and its
own approval gate.

Report in the state vocabulary above, never "done". The report and the `## Handover`
section carry: files changed per repo with branch and tree path; checks run and their result
plus what was **not** run and why; what a human must still verify, named; for a cross-repo
change, the merge order (backend first) and one PR per repo; anything blocked.

Say the push line whenever the work may outlive the day:

> This ticket lives only on this machine: the branch is local and `.work/<KEY>/` is never
> committed. If anyone else may pick it up, push it: `git -C <tree> push -u origin <branch>`

Details: [`WORKTREE.md`](./WORKTREE.md) · [`FRESHNESS.md`](./FRESHNESS.md) · [`VALIDATION.md`](./VALIDATION.md)
