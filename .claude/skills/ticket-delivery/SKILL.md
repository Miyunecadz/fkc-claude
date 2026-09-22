---
name: ticket-delivery
description: Use when implementing, validating or reviewing the work for a Jira ticket (FKC) in this workspace — driving it from analysis through planning, implementation, validation and independent review. Owns the stage contracts and gates, the per-ticket worktree workspace, the .work/<KEY>/work.md state sidecar, the ticket- and codebase-freshness gates, and what validation actually exists here. Does not write tickets, does not push, does not deploy.
stacks: [all]
---

# Ticket delivery

Take a ticket that already exists in Jira and carry it to a reviewed, validated change on
a branch in an **isolated worktree per repo**. Two entry points, with a human pause between
them: `/implement-ticket <KEY>` writes the code and stops at `IMPLEMENTED`;
`/implement-review <KEY>` validates, reviews and commits it once a human has read it.

Not this skill: writing or refining tickets (`ticket-writing`, `/create-ticket`), pushing,
opening the PR (`pull-request`, `/create-pr`), or deploying. It ends at a reviewed,
committed worktree plus a handover note.

Three things this workflow refuses to be wrong about, and every rule below exists for one
of them:

1. **The ticket may have moved.** Jira is the ticket; a copy read an hour ago is a memory.
2. **The codebase may have moved.** A branch cut yesterday, and a graph built from another
   branch, both describe code that is no longer what will be merged into.
3. **The main context may not hold the codebase.** Reading is delegated; conclusions come
   back, file bodies do not.
4. **The work may not be on this machine.** `.work/<KEY>/` is local and is never committed,
   so a ticket another dev implemented is invisible here. Jira is the only record that
   travels — which is why `/create-pr` writes a delivery comment and both other commands
   check for one before starting.

## 1. The ticket workspace

Everything for one ticket lives under one directory, so two tickets never share state:

```
.work/<KEY>/work.md            state sidecar — the only file the main thread writes
.work/<KEY>/meta/<repo>.env    MODE / BASE_REF / BASE_SHA / BRANCH, recorded at prepare time
.work/<KEY>/meta/<repo>.graph  which commit the ticket's graph was built from
.work/<KEY>/validate/<repo>.log   full check output   (never pasted into context)
.work/<KEY>/review/<n>.md         full reviewer report (never pasted into context)
.work/<KEY>/<repo>/            the checkout — worktree mode only; absent in-place
```

**Where the code lives depends on the mode the user chose**, which is why the last line is
conditional. `/implement-ticket` asks at §2: a **worktree** under `.work/<KEY>/<repo>/`, or
**in-place** in the user's own `<repo>/`. Never assemble that path — ask for it:

```bash
tree=$(.claude/hooks/ticket-worktree.sh tree <KEY> <repo>)
```

`.work/` itself is outside all three repos and the workspace root is not a git repo, so
nothing here is ever committed by accident. Both modes, their trade-offs and their rules:
[`WORKTREE.md`](./WORKTREE.md).

**The sidecar is written through `ticket-worktree.sh sidecar`, never by hand.** The main
thread has no `Edit` and no `Write`; the subcommand appends the section, sets `state:` and
writes the `## Log` line in one atomic step, and it cannot overwrite a finished section:

```bash
.claude/hooks/ticket-worktree.sh sidecar init   <KEY> "<summary>"
.claude/hooks/ticket-worktree.sh sidecar header <KEY> jira=... repos=... graph=...
.claude/hooks/ticket-worktree.sh sidecar append <KEY> Analyse ANALYSED <<'EOF'
<body — conclusions and citations>
EOF
.claude/hooks/ticket-worktree.sh sidecar state  <KEY> BLOCKED "<what is missing>"
.claude/hooks/ticket-worktree.sh sidecar show   <KEY> [--header|--sections]
```

Appending by heredoc-rewriting `work.md` is what this replaces: it cost 1–2k output tokens
per stage, which then sat in context for the rest of the ticket.

**Sidecar shape** — header keys, then one section per completed stage, appended in order:

```markdown
# Work — FKC-123
ticket:   FKC-123 — <summary>
jira:     updated=<ISO from the issue> status=<name> fields-sha=<8 hex>
state:    NEW | ANALYSED | PLANNED | APPROVED | IMPLEMENTING | IMPLEMENTED | VERIFIED |
          REVIEWED | HANDED_OVER | PR_OPEN | BLOCKED | NOT_NEEDED | ALREADY_IMPLEMENTED |
          NOT_APPROVED
blocked:  - | <one line: what is missing and who can answer it>
repos:    fk-admin-panel-be@feat/FKC-123-x from origin/staging@<sha>
graph:    fk-admin-panel-be=worktree-extract@<sha>

## Analyse — <date>
## Plan — <date>
## Approval — <date>
## Implement — <date>
## Validate — <date>
## Review — <date>
## Handover — <date>
## Log            every state change, one line, timestamped
```

Rules:

- **Append; never rewrite a completed section.** A second pass adds `## Validate (2)` —
  `sidecar append` does this for you, and refuses to clobber.
- `state:` and the `## Log` line move with the section, in the same call. An interrupted
  run must never claim progress it did not make.
- **Write each stage down as it finishes, not at the end.** The sidecar is the ticket's
  memory: it outlives every agent's context and any compaction of the main thread. What
  is not in it is lost, and a resumed run has no way to know it ever existed.
- Store decisions and evidence — `path:line`, a sha, one decisive output line — not prose,
  not the ticket text, not diffs. The reviewer reads the ticket and the diff itself.
- Re-running either command resumes from `state:`, and each refuses the states that belong
  to the other. Check the sidecar
  before writing anything; nothing here is safe to duplicate.

## 2. Stages and gates

Strictly ordered — each stage consumes the previous one's output.

The pipeline is split across **two commands**, with a human pause between them:

```
/implement-ticket   Locate (+images) → Prepare → Analyse → Plan → [approve] → Implement
                                                                         ends IMPLEMENTED
      ── the dev reads the diff, and normally tweaks it by hand ──
/implement-review   Validate → Review → Handover (commit)                        ends HANDED_OVER
/create-pr          push → PR → the ticket's delivery comment                    ends PR_OPEN
```

| Stage | Command | Who does it | Produces | State after | Gate before moving on |
|---|---|---|---|---|---|
| Locate | implement | main thread | the Jira issue read once (`fields="*all"`, `include="comments"`), fingerprint recorded, repos in scope | `NEW` | issue exists, carries no delivery comment, has not moved past implementation, and names its affected systems |
| Evidence | implement | main thread + `screenshot-requirement-analysis` | the ticket's images read **once**, inventoried as rows in `## Evidence`; non-image attachments recorded as a manifest and **not** downloaded | `NEW` | every attached image has been inventoried, or the ticket has none. A contradiction between an image and the ticket text, or an illegible region that would change the build, is a §5 stop |
| Prepare | implement | `ticket-worktree.sh` + `ticket-freshness.sh graph` | a worktree per repo, cut from the **fetched** base; a graph built from that worktree | — | every repo in scope has a worktree and a graph whose `GRAPH_SHA` is its HEAD |
| Analyse | implement | `ticket-analyst`, one per repo, **parallel** | requirement interpretation, affected files as `path:line`, unknowns, risks, image-row-vs-code conflicts | `ANALYSED` | no material unknown; nothing the ticket needs is missing from the base; every image row for that repo's surface is either satisfied by the plan or raised as a `CONFLICT` |
| Plan | implement | main thread | files to touch per repo, pattern to follow, cross-repo order, the contract if one changes, validation commands, out of scope | `PLANNED` | — |
| **Approval** | implement | the user | the decision, recorded verbatim | `APPROVED` | **the user approves.** Nothing under any worktree is edited before this. A presented plan is not an approved one |
| Implement | implement | `ticket-implementer`, one per repo | the change, scoped to the plan | `IMPLEMENTING` → `IMPLEMENTED` | plan followed, or the deviation recorded in `## Implement` |
| **Human read** | — | the dev | whatever they change by hand | `IMPLEMENTED` | **the command ends here.** Nothing is validated, reviewed or committed until a human has read the code |
| Validate | review | `ticket-validator`, one per repo, **parallel** | prepared checks vs observed results, decisive lines only | `VERIFIED`, else `FAILED_VERIFICATION` | every applicable check ran and passed — a check that did not run is never recorded as passing |
| Review | review | `change-reviewer`, mode `gate`, **one, sequential** | independent verdict, AC by AC | `REVIEWED` | no blocking finding stands, and no AC row is `[FAIL]` |
| Handover | review | main thread | commit per repo, report | `HANDED_OVER` | — |

Terminal endings without implementation are legitimate, not failures: `NOT_NEEDED`,
`ALREADY_IMPLEMENTED`, `NOT_APPROVED`, `BLOCKED`.

**`IMPLEMENTED` is the pause, and no state was added for it.** The command ending is what
makes it durable: a blocking prompt dies when the dev goes home, and the dev who comes back
may be a different person on a different day.

**The reviewer reports; it never fixes.** `/implement-review` has no `ticket-implementer` —
a command that both checks the code and can rewrite it would put the dev's hand-edits at
risk and would review a version they never saw. A blocking finding leaves two routes: the
dev fixes it by hand and re-runs `/implement-review`, or re-runs `/implement-ticket`, which
owns the implementer and the cap.

**The fix round is capped at two.** A finding sends only the repo it names back through
implement → validate → review, appended as `(2)`. There is no round three: it is recorded,
`blocked:` is set, and it goes to the user — a reviewer twice wrong about the same code will
not be right on the third pass, and a round costs 1.2–2.5M tokens.

**Judge against the ticket's acceptance criteria, not the plan.** Once a human has edited the
code — or a second dev has reimplemented it their own way — the plan no longer describes what
is there. The AC is the only yardstick that survives that, which is why the reviewer returns
one PASS/FAIL row per criterion.

**Freshness is re-checked at five points**, not once: before presenting the Plan, before
Implement, at the start of `/implement-review`, before Review, and before the commit. Both
halves — the Jira issue and the base branch. [`FRESHNESS.md`](./FRESHNESS.md) owns how, and
what each verdict forces.

## 3. What runs in parallel, and what never does

| Runs in parallel | Because |
|---|---|
| Analyse, one agent per repo | reads only; the repos are independent codebases |
| Implement, one agent per repo | separate worktrees, separate branches — **only when the plan pins the API contract** (see below) |
| Validate, one agent per repo | separate worktrees; the checks do not share state |
| Two different tickets, in two sessions | separate `.work/<KEY>/`, separate worktrees, separate branches |

Never concurrent:

- **Two agents in the same worktree.** One worktree, one writer, at a time.
- **Implementation across repos when the contract is not pinned.** If the ticket changes
  the GraphQL surface and the plan does not state the exact SDL, the backend slice goes
  first and the clients follow; otherwise the clients are coding against a guess. Load
  `graphql-contract` when the change crosses a repo boundary.
- **Review.** One reviewer, after every repo has validated. Reviewing half a change is
  reviewing the wrong change.
- **Anything at all with the user's own checkouts.** `fk-admin-panel-be/`,
  `fk-admin-panel-fe/` and `fk-mobile/` are read-only for this workflow.

Yarn installs are not parallel-safe here either: worktrees **share** the main checkout's
`node_modules` by symlink. Never run `yarn install`, `yarn add` or `yarn upgrade` inside a
worktree — it writes through the link into the user's checkout. See [`WORKTREE.md`](./WORKTREE.md) §3.

## 4. Context discipline — the detail stays on disk

The main thread orchestrates. It reads the Jira issue, the sidecar and the agents' reports,
and it writes the sidecar through the hook. It does **not** read source files, diffs or
build logs — that is what the agents are for, and it is the whole reason this workflow
survives a long ticket.

**This is a budget, not an aspiration: 25 `Bash` calls for the whole ticket**, covering the
hook scripts, the freshness checks, the sidecar and the handover commits. Measured runs
that ignored it spent 27–434 calls and 8–95M tokens, main thread accounting for 62–93% of
the total. The arithmetic is `calls × context`: an orchestrator call carries 100–240k of
context, an agent call 17–22k, and the agent's context is discarded when it returns instead
of compounding into every later call. Delegating the same work is 3–5× cheaper per call and
does not grow the main thread at all.

Forbidden in the main thread, because each has an owner:

| Never in the orchestrator | Owner |
|---|---|
| `cat`/`sed -n`/`head` a source file, `grep` a repo, `graph.sh query` | `ticket-analyst` |
| any write to a source file — `cat >`, `python3 - <<EOF`, an editor | `ticket-implementer` |
| `yarn build`/`lint`/`test`, `node --check` | `ticket-validator` |
| `git diff` to read the change (a `--stat` line is fine) | `change-reviewer` |

Needing a file's contents to decide something means **asking the agent that read it** — its
context still holds the file. Continue that agent with `SendMessage` rather than opening the
file or spawning a fresh one that has to read it all over again.

Every agent obeys the same contract:

- Return **conclusions with citations** (`repo path:line`), never file bodies, never a full
  diff, never a full log. A decisive output line is quoted; the rest is written to
  `.work/<KEY>/…` and referenced by path.
- Cap the report at roughly 40 lines. Longer means it is reporting its work instead of its
  findings.
- Say `UNKNOWN — REQUIRES VERIFICATION` rather than filling a gap. An invented field,
  table, permission or route is the failure this workflow exists to prevent.
- Never edit outside the worktree it was given, and never commit unless told to.

If the main thread needs a file's content to decide something, it asks the agent that has
already read it — it does not open the file.

### Nothing is lost at a stage boundary

Cheap delegation fails the moment an agent has to rediscover what the previous stage
already paid to learn. Each dispatch therefore carries the earlier stages' findings
forward, copied from the sidecar:

| Stage | Receives, verbatim from the sidecar |
|---|---|
| Analyse | the ticket's requirement text for that repo, worktree path, base `ref@sha`, graph path |
| Plan | every analyst's full report (this is the main thread's own stage) |
| Implement | its plan slice · the analyst's `FILES TO CHANGE`, `PATTERN / REUSE`, `MISSING FROM THIS BASE`, `RISKS` |
| Validate | the implementer's `CHANGED` and `DEVIATIONS` · the plan's validation commands |
| Review | the ticket text · the plan · the implementer's `CHANGED`/`DEVIATIONS` · the validator's verdict |
| Handover | the sidecar, read back with `sidecar show` |

Requirement text and user decisions travel **quoted, never summarised** — a paraphrase is
where a requirement quietly changes. A `path:line` citation travels instead of the file:
the receiving agent opens it in its own context, which is the cheap place to hold it.

A report that turns out to be too thin to act on is a follow-up to **that same agent** via
`SendMessage` — it still has the file loaded. Re-reading it in the main thread, or spawning
a fresh agent to read it again, both pay for the same work twice.

## 5. Evidence discipline

- The requirement comes from the Jira issue. Its wording and its business rules are not
  yours to reinterpret; a gap goes back to the requester.
- Any claim about current behaviour comes from code read **in the worktree**, at the base
  the work is cut from — not from memory, not from the workspace `docs/` map unless
  `FRESHNESS.md` says that map matches this commit.
- Graph answers are a map, not the territory: `graph.sh query <path> "<question>"` finds the
  place, the file confirms the fact. Address it by path — `graph.sh` resolves which of this
  workspace's maps describes that path and refreshes it before answering, so `--graph` is
  never passed by hand.
- Everything else is an unknown: record it, ask if it changes the work, never build on it.

## 6. Follow the code that is already there

Order: reuse → extend → compose → refactor → create. Before adding a util, hook, component,
resolver or table, look for the existing one — and confirm it exists **on this base**.

Load the repo's own standards skill when writing its code, and nothing else:
`backend-standards`, `frontend-standards`, `mobile-standards`; `graphql-contract` when the
change crosses the API boundary; `architecture-overview` when tracing a flow between repos.
Do not restate them here.

## 7. Stop conditions

Set `blocked:` in the sidecar, report, and stop — rather than working around it — when:

- the ticket is ambiguous in a way that changes what gets built;
- something the ticket needs is absent from the base branch;
- a requirement contradicts the codebase;
- the Jira issue changed materially mid-flight (`FRESHNESS.md` §1);
- the base branch moved and the rebase conflicts (`FRESHNESS.md` §2);
- a repo in scope has a worktree with changes that are not this ticket's;
- the **same** check fails twice — a third attempt is guessing.

Never stash, reset, checkout over, or discard anything in the user's checkouts. There is
nothing to work around there: this workflow does not touch them.

## 8. Handover

Report in the sidecar's vocabulary — do not invent a second one. `IMPLEMENTED` is code
written and nothing more. `VERIFIED` means the applicable checks ran and passed, with their
output recorded. `REVIEWED` means the reviewer returned PASS, or its blocking findings are
fixed and re-validated. "Done" is never `IMPLEMENTED`.

Handover belongs to `/implement-review`, after the reviewer returns PASS. Per repo: re-check
freshness, then **commit inside the worktree** — one commit, conventional one-line subject,
no body. Nothing to commit, because the dev already committed their own tweaks, is a normal
outcome: say so and do not amend their commit. Do not push, do not open a PR, do not
transition the Jira issue: those are the user's call. Report the branch and the exact command
they would run to push it.

Say the push line whenever the work may outlive the day. `.work/<KEY>/` never leaves this
machine, so an unpushed branch plus an absent dev is how one ticket gets implemented twice.

The branch leaves the machine through `/create-pr` (the `pull-request` skill) and its own
approval gate — never from here. It sets `state: PR_OPEN` when the PR is open, and writes the
ticket's delivery comment, which is what makes the work visible to anyone else.

Last sidecar section, and the reply to the user:

- files changed per repo, with the branch and worktree path;
- checks run and their result, verbatim where it matters, plus what was **not** run and why;
- what still needs manual verification, named specifically;
- for a cross-repo change: the required merge order (backend first) and one PR per repo;
- anything left blocked or out of scope.

Details: [`WORKTREE.md`](./WORKTREE.md) · [`FRESHNESS.md`](./FRESHNESS.md) · [`VALIDATION.md`](./VALIDATION.md)
