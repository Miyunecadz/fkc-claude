---
description: Drive a Jira ticket (FKC) through analysis, planning and implementation — in an isolated git worktree per repo, stopping at IMPLEMENTED so a human can read the code before anything is validated, reviewed or committed
argument-hint: <FKC-123 | ticket key or summary substring> (omit to list ticket workspaces in flight)
allowed-tools: Task, Agent, SendMessage, Bash, Read, AskUserQuestion, Skill, mcp__jira__jira_get_issue, mcp__jira__jira_search, mcp__jira__jira_get_issue_images
effort: high   # multi-stage delivery with an approval gate
---

Work the ticket identified by:

$ARGUMENTS

Load the `ticket-delivery` skill first. It owns every rule: states and resume (§3), budget
and the never-here table (§5), what each agent receives (§5), stop conditions (§7). This
file is the order of steps. Where a step names a rule, follow the skill, do not restate it.

**This command ends at `IMPLEMENTED`.** No validation, review or commit: that is
`/implement-review`, after a human has read the code.

You are the orchestrator. You have no `Edit` or `Write`. `Read` is for the sidecar and skill
files, never source files. Agents read and write code and hand you conclusions. Write the
sidecar only with the `sidecar` commands in SKILL §1.

## 1. Locate

```bash
.claude/hooks/ticket-worktree.sh list
```

No argument: relay the list, ask which ticket, stop.

Resolve the argument to one key: a bare key goes to `mcp__jira__jira_get_issue`; anything
else to `mcp__jira__jira_search` first (several matches: ask; none: stop). Read the issue
**once, in full**, with the call in FRESHNESS §1 (`fields="*all"`, `include="comments"`).
The defaults leave out custom-field acceptance criteria, attachments and comments.

Stop, reporting what exists, if the ticket was delivered already (FRESHNESS §1: delivery
comment, branch by key or Trello number, status at or past `In Code Review`).

If `.work/<KEY>/work.md` exists, read it with `sidecar show <KEY> --last Evidence Implement Review`
and resume from `state:` using SKILL §3. Never repeat finished work.

### 1a. Images and attachments

Short text plus a screenshot is the normal ticket here: the image is requirement.

- Images in `fields.attachment` (`png`, `jpe?g`, `gif`, `webp`, `svg`, `bmp`): call
  `mcp__jira__jira_get_issue_images issue_key=<KEY>` **once per ticket**, load
  `screenshot-requirement-analysis`, and produce its rows. Carry forward word for word any
  image-versus-text contradiction, and any illegible region that would change the build
  (both are SKILL §7 stops).
- Other attachments: record filename, type and size only. Never download them here; the
  analyst whose slice needs one pulls it.

Scope comes from the ticket's words and images: Web → `fk-admin-panel-fe`, Backend/DB →
`fk-admin-panel-be`, iOS/Android → `fk-mobile`. Unstated scope: ask.

## 2. Prepare

**Ask with `AskUserQuestion`, every time, before preparing:** in-place or worktree (the
trade-off table is WORKTREE top). Skip only when the meta already records a `MODE`. In the
same question, confirm the base (WORKTREE §2) and the Trello card number for the branch
name (WORKTREE §1) unless the ticket states both.

Per repo in scope:

```bash
.claude/hooks/ticket-worktree.sh prepare <KEY> <repo> <base> <type>/FKC-<trello>-<slug> [--in-place]
.claude/hooks/ticket-freshness.sh graph   <KEY> <repo>
.claude/hooks/ticket-worktree.sh tree    <KEY> <repo>      # pass this path to every agent
```

Relay any refusal or `WARNING` from `prepare` and ask. `graph` exit 4 means the map has no
community names: note it in `graph:` and carry on.

Create the sidecar, then write the Evidence before any agent is dispatched:

```bash
.claude/hooks/ticket-worktree.sh sidecar init   <KEY> "<summary>"
.claude/hooks/ticket-worktree.sh sidecar header <KEY> jira="updated=<ISO> status=<name>" \
    repos="<repo>@<branch> from <base-ref>@<sha> (<mode>)" graph="<repo>=<source>@<sha>"
.claude/hooks/ticket-worktree.sh sidecar append <KEY> Evidence NEW <<'EOF'
IMAGES (<n>, read once at Locate)
- Image 1 — <screen>: <rows that bear on the build>
- CONTRADICTION: <image> vs <text> — both, as they are
ATTACHMENTS (manifest only)
- <filename> (<mime>, <size>) — <what it looks like it is for>
(or: NONE — the ticket carries no attachments)
EOF
```

Record the user's mode, base and branch answers in `## Locate` or the header. Later runs,
the fix round and `/implement-review` read images only from `## Evidence`.

## 3. Analyse → Plan → Approval → Implement

1. **Analyse.** One `ticket-analyst` per repo, all in one message. Give each what SKILL §5
   lists for Analyse, and nothing else. Append `## Analyse` with `ANALYSED`. A thin report
   gets a `SendMessage` follow-up to the same analyst.
2. **Plan.** Yours, not delegated. Files per repo, the pattern to follow, cross-repo order,
   the contract if it changes, the checks to run, out of scope. Run
   `ticket-freshness.sh check <KEY>` (FRESHNESS §2 says what each exit forces), append
   `## Plan` with `PLANNED`, present it, and wait.
3. **Approval.** Append the user's words verbatim as `## Approval` with `APPROVED`, or
   `NOT_APPROVED`. Nothing is edited before this.
4. **Before Implement:** `ticket-freshness.sh check <KEY>`, and re-read the issue and compare
   the fingerprint (FRESHNESS §1). Never re-record it on your own.
5. **Implement.** `sidecar state <KEY> IMPLEMENTING`, then one `ticket-implementer` per
   repo. In parallel only when the plan pins the exact contract; otherwise backend first.
   Give each what SKILL §5 lists for Implement, including `MISSING FROM THIS BASE`. Append
   `## Implement` with `IMPLEMENTED`, one block per repo: `CHANGED`, `DEVIATIONS`,
   `NOT DONE`, `NEEDS THE USER`.

### 3a. The fix round

Entered from `REVIEW_FAILED` or `FAILED_VERIFICATION` (SKILL §3). Read the last
`## Review` or `## Validate` from `sidecar show <KEY> --last Validate Review`. Dispatch
`ticket-implementer` only for the repos a finding names, giving it the finding text verbatim
and its tree path. Append `## Implement` with `IMPLEMENTED` and send the user to
`/implement-review`.

One fix round per approved plan (SKILL §2). If the hook refuses the append, record the
standing finding with `sidecar state <KEY> BLOCKED "<finding>"` and hand it to the user.

## 4. Stop at IMPLEMENTED and hand over

Do not run checks, review or commit. Your report, in this order:

1. what changed per repo, with mode, tree path and branch;
2. how to read it: `git -C <tree> diff <base-ref>...HEAD`. In-place, say plainly: *"this is
   checked out in your own `<repo>/` right now"*;
3. next: `/implement-review <KEY>`;
4. the push line from SKILL §8.

Anything blocked goes in the report and in `blocked:`. Reference `.work/<KEY>/work.md`
rather than reproducing it. Never call the change validated, reviewed or done.
