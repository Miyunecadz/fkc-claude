---
description: Drive a Jira ticket (FKC) through analysis, planning and implementation — in an isolated git worktree per repo, stopping at IMPLEMENTED so a human can read the code before anything is validated, reviewed or committed
argument-hint: <FKC-123 | ticket key or summary substring> (omit to list ticket workspaces in flight)
allowed-tools: Task, SendMessage, Bash, Read, AskUserQuestion, Skill, mcp__jira__jira_get_issue, mcp__jira__jira_search, mcp__jira__jira_get_issue_images
effort: high   # multi-stage delivery with an approval gate
---

Work the ticket identified by:

$ARGUMENTS

Load the `ticket-delivery` skill **before anything else**. It owns the stage contracts, the
gates, the sidecar format, the worktree layout, the freshness rules, the delegation contract
and the validation matrix. This file is orchestration only: do not restate the skill and do
not improvise a rule it covers.

**This command ends at `IMPLEMENTED`.** It does not validate, does not review, and does not
commit. That is `/implement-review`, run after a human has read the code — see §4. The split
is deliberate: the dev who scans the implementation usually tweaks it, and a reviewer that
ran before those tweaks reviewed a version that will never ship.

## 0. You are the orchestrator. You do not do the work.

You have no `Edit` and no `Write` — deliberate, not an oversight. You cannot open source
files, cannot change them, and cannot run the builds. Agents do all three and hand you
their conclusions.

**Your whole-ticket budget is 18 `Bash` calls.** Not per stage — per ticket. They are for
the hook scripts, the freshness checks and the sidecar, and that is enough for a two-repo
ticket. Past runs of the unsplit command spent **27 to 434** and cost 8–95M tokens; the runs
that stayed near the low end were the ones that delegated. Cost here is `calls × context`,
your context sits at 100–240k, and every extra call re-serves all of it.

Never run these in this thread — each one is an agent's job, and running it yourself is the
failure this command is designed around:

| Never here | Whose job |
|---|---|
| `cat`, `sed -n`, `head`, `less` on a source file | `ticket-analyst` |
| `grep`/`rg` through a repo, `graph.sh query` | `ticket-analyst` |
| `cat > file`, `cat >> file`, `python3 - <<EOF` that edits code | `ticket-implementer` |
| `yarn build`, `yarn lint`, `yarn test`, `node --check` | `ticket-validator`, in `/implement-review` |
| `git diff` to read a change (diffstat is fine) | `change-reviewer`, in `/implement-review` |
| `mcp__jira__jira_download_attachments` — it returns the file **base64-encoded into your context** | `ticket-analyst` |

`jira_get_issue_images` is the one exception, and you have it: it returns images as inline
vision content, not as a base64 blob, and it is read **once per ticket** (§1a). Attachment
*bytes* are a different matter — a 2 MB PDF arrives as ~2.7 MB of base64 text that never
leaves your context again. The analyst pulls those, in its own disposable context.

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
told to prefer `cat`/`sed`/`grep` for reading and heredocs for editing. That advice is for a
thread doing the work itself. Here it produces exactly the failure above — and a heredoc
edit is worse than an `Edit` would have been, because the whole file body becomes output
that stays in context for the rest of the ticket. In this command, reading and editing are
delegated regardless of which tool would be convenient.

At every stage boundary, before you write the sidecar section, count the `Bash` calls you
have made. Past 18, stop delegating work to yourself: report where you are and what is left,
and let the user decide whether to continue.

## 1. Locate — deterministic, do this first

```bash
.claude/hooks/ticket-worktree.sh list          # tickets already in flight, and their state
```

No argument: relay that list, add anything in progress in Jira if it helps, ask which ticket,
stop.

With an argument: resolve it to one issue key. A bare key goes straight to
`mcp__jira__jira_get_issue`; anything else is `mcp__jira__jira_search` first — more than one
match, ask; none, say so and stop. **Read the issue once, in full** — in full means
everything the requirement could be hiding in, which the tool's defaults do not give you:

```
mcp__jira__jira_get_issue  issue_key=<KEY>  fields="*all"  use_display_names=true  include="comments"
```

`fields` defaults to a short essential set with **no `attachment` and no custom fields**, so
acceptance criteria living in a custom field and the attachment manifest are both absent
unless you ask; `comments` are not inlined unless `include` says so, and the delivery-comment
check below has nothing to read without them. Record the freshness fingerprint
(`ticket-delivery` → `FRESHNESS.md` §1). The freshness **re-checks** later in the run compare
the requirement fields only — they do not need the attachments again.

Two things in that issue end the run before any work starts, because each means someone else
may already have delivered this ticket from another machine — `.work/` is local and never
travels:

- a **delivery comment** written by this workflow (its marker, a branch, a sha, a PR link) —
  authoritative, and verifiable by opening the PR it names;
- **status at or past `In Code Review`** — this project's ladder is
  `To Do → In Progress → In Code Review → In Staging → Production / Release`, and only the
  first two mean the work is still yours. Corroborating only, because a human moved it and
  humans move tickets by mistake.

Report what exists and stop. Starting a second implementation of a delivered ticket is the
failure this check exists for. `FRESHNESS.md` §1 also has you look for a branch already
carrying the key — that check stays, and catches the case where the PR was opened by hand.

### 1a. Read the attachments — images are requirement, not decoration

`fields.attachment` is now in front of you. Short ticket text plus a screenshot is the normal
shape of a ticket here, not an edge case: a PO who pastes the screen and writes "make it like
this" has put the entire requirement in the image, and an implementation that never opened it
is building from the half of the ticket that happened to be typed.

**Images** — if the manifest holds any (`png`, `jpe?g`, `gif`, `webp`, `svg`, `bmp`):

```
mcp__jira__jira_get_issue_images  issue_key=<KEY>
```

Call it **once per ticket**, then load `screenshot-requirement-analysis` and produce its
inventory — one row per readable element, relevance marked rather than silently filtered,
labels copied verbatim, annotations treated as explicit intent. Those rows are what travels
to the analysts (§3). The images themselves do not: they are read here and never again, which
is the whole reason this is one call in one place rather than one per repo.

Two rows from that skill outrank the rest and you carry them forward word for word:

- a **contradiction** between the image and the ticket text (text says "all suppliers", the
  screenshot shows a filter) — report both as they are, do not reconcile them yourself;
- an **illegible or cropped region that would change what gets built** — that is a §5 stop
  condition, not a detail to guess past.

**Non-image attachments** (`.csv`, `.sql`, `.pdf`, `.json`, `.log`, `.xlsx`) — record the
manifest only: filename, mime type, size. **Do not download them here.** Pass the manifest to
the analysts; the one whose slice actually needs a file pulls it itself (§3), and the base64
lands in a context that is thrown away rather than in yours for the rest of the ticket.

Scope reads off this too — a mobile frame in a screenshot is scope evidence as good as the
ticket naming iOS, and a screenshot of a screen no repo in scope owns means the scope is
wrong.

Then decide scope from the ticket's own words — affected systems map to repos:
Web → `fk-admin-panel-fe`, Backend/DB → `fk-admin-panel-be`, iOS/Android → `fk-mobile`.
Unstated scope is not yours to guess; ask.

If `.work/<KEY>/work.md` exists, read it and **resume from `state:`**:

| `state:` | Resume at |
|---|---|
| `NEW`, `ANALYSED`, `PLANNED`, `APPROVED` | the stage after it, as normal |
| `IMPLEMENTING` | Implement — the previous run was interrupted |
| `IMPLEMENTED` | nothing to do here. Point the user at `/implement-review <KEY>` |
| `FAILED_VERIFICATION`, or `REVIEWED` with standing blocking findings | **§3a, the fix round** |
| `HANDED_OVER`, `PR_OPEN` | nothing to do here. Say so and stop |

Re-running this command must never repeat completed work or duplicate a sidecar section.

## 2. Prepare the workspace — ask which mode, then one graph per tree

### 2a. Ask the user: in-place, or a worktree?

**Ask every time, with `AskUserQuestion`, before preparing anything.** Do not infer the mode
from the ticket, and do not carry a previous ticket's answer forward — only the user knows
whether they are about to pick up a second ticket or leave this one half-done overnight.

Skip the question only when `.work/<KEY>/meta/<repo>.env` already records a `MODE`: a ticket
keeps the mode it was prepared with, because switching mid-ticket moves the branch out from
under work in progress.

Put it to them roughly like this, with the trade-off stated rather than implied:

- **In-place** *(default for a single ticket)* — the branch is checked out in your own
  `<repo>/`, and `.work/<KEY>/` holds only the sidecar, meta and logs. Queries resolve to the
  repo's own map, which is the **labelled** one, so analysis anchors on real community names.
  Requires a clean checkout, switches your branch, and holds that repo until you are done.
- **Worktree** — an isolated checkout at `.work/<KEY>/<repo>/`; your checkout keeps its branch
  and its uncommitted work. Needed for a second ticket in flight, or a cross-repo ticket whose
  repos are built in parallel. Costs disk, and its map has to be labelled after extraction.

Whatever they pick, record it verbatim in the sidecar — it is a gate decision like any other.

### 2b. Prepare each repo in scope

```bash
.claude/hooks/ticket-worktree.sh prepare <KEY> <repo> <base> <type>/<KEY>-<slug> [--in-place]
.claude/hooks/ticket-freshness.sh graph   <KEY> <repo>
```

`prepare` refuses in-place when the checkout is dirty or another ticket already holds that
repo in-place. Those refusals are the point — relay them and ask rather than working around
them; a worktree is always the answer that cannot cost the user their working state.

**Never build the tree path yourself.** `.work/<KEY>/<repo>` is only correct in worktree mode.
Ask once per repo and pass what comes back to every agent:

```bash
.claude/hooks/ticket-worktree.sh tree <KEY> <repo>    # -> the checkout holding the branch
```

Choose `<base>` from evidence, not from name-matching — the ticket's environment,
`docs/_shared/env-matrix.md`, then git (`WORKTREE.md` §2). Ask before you commit to a base
you inferred.

The graph step is what stops the analysis being answered from another branch. What it does
depends on the mode, and in both cases it ends with a map that is **labelled** — a map whose
communities are still bare integers answers structurally but cannot anchor a question like
"where do subcontract order task lines live", which is how an analysis lands one module over
from the right one:

- **in-place** — the repo's own map is the ticket's map; `graph.sh ensure` keeps it current.
- **worktree** — extract from the worktree's own commit, then label it (~30s), or copy the
  workspace map *and its label sidecars* when it already describes exactly this commit.

Agents reach it through the resolver, addressing it by the tree path rather than by `--graph`:

```bash
tree=$(.claude/hooks/ticket-worktree.sh tree <KEY> <repo>)
.claude/hooks/graph.sh query    "$tree" "<question>"
.claude/hooks/graph.sh affected "$tree" "<symbol>"
```

Agents are given that path and query only it. The rule that used to read "forbidden the
workspace map" is really "never choose a map by hand" — in-place the workspace map *is* the
right one, and `graph.sh` is what knows the difference.

`graph.sh` re-verifies the map against HEAD **and** the dirty tree on every call and rebuilds
it incrementally when either moved, so a map cannot go quietly stale mid-implementation the
way it does between `ticket-freshness.sh` checkpoints.

Create the sidecar now — through the hook, not by hand:

```bash
.claude/hooks/ticket-worktree.sh sidecar init   <KEY> "<ticket summary>"
.claude/hooks/ticket-worktree.sh sidecar header <KEY> jira="updated=<ISO> status=<name> fields-sha=<8hex>" \
                                                     repos="<repo>@<branch> from <base>@<sha> (<mode>)" graph="<repo>=<source>@<sha>"
```

Record the mode in `repos=`. A resumed run reads it from the meta file, but a human reading
the sidecar needs to know whether the code is in their checkout or under `.work/`.

Then write §1a's findings down, before any agent is dispatched:

```bash
.claude/hooks/ticket-worktree.sh sidecar append <KEY> Evidence NEW <<'EOF'
IMAGES (<n> attached, read once at Locate)
- Image 1 — <screen/page>: <the inventory rows that bear on the build>
- CONTRADICTION: <image> vs <ticket text> — <both, as they are>

ATTACHMENTS (not downloaded — manifest only)
- <filename> (<mime>, <size>) — <what it looks like it is for>

NONE — the ticket carries no attachments
EOF
```

This is the section that makes the images survive. Your context is compacted; the sidecar is
not. A resumed run, a second fix round and `/implement-review` all read the image evidence
from here, and none of them can call `jira_get_issue_images` — it is on this command only.

## 3. Run the stages

Analyse → Plan → **Approval** → Implement, each gated as the skill specifies, each written to
the sidecar as it completes together with its `state:` update.

Delegate the reading and the writing; keep the conclusions:

| Stage | Delegate to | Concurrency |
|---|---|---|
| Analyse | `ticket-analyst`, one per repo | **parallel** — dispatch them in a single message |
| Implement | `ticket-implementer`, one per repo | parallel **only** when the plan pins the exact API contract; otherwise backend first, clients after |

**Plan is yours and is not delegated.** You write it from the analysts' reports, and it ends
by presenting the plan and waiting. Nothing in any worktree is edited before the user
approves. Record the decision verbatim in `## Approval`.

### 3a. The fix round — entered from `/implement-review`'s findings

`/implement-review` reports blocking findings; it never fixes them. A dev who wants them
fixed by an agent rather than by hand re-runs this command, and lands here.

Read the standing findings from the sidecar's last `## Review` section. Dispatch
`ticket-implementer` for **only the repos a finding names**, giving it the finding text
verbatim and nothing else new. Append `## Implement (2)`, set `IMPLEMENTED`, and send the
user back to `/implement-review`.

**Two fix rounds, hard cap.** `## Implement (3)` does not exist. A finding still standing
after the second round is recorded, `blocked:` is set, and it goes to the user — a reviewer
that has been wrong twice about the same code will not be right on the third pass, and a
round costs 1.2–2.5M tokens.

### What each agent is given — brief, but never starved

Delegating is only cheaper if the agent does not have to rediscover what a previous stage
already established. Every dispatch carries **all** of this, and nothing else:

1. the ticket key and the requirement text **for that repo's slice**, quoted from Jira — not
   summarised, not paraphrased;
2. its worktree path, its base `ref@sha`, and its graph path;
3. **the image evidence rows for the surface that repo owns**, copied verbatim from the
   sidecar's `## Evidence`, plus the attachment manifest — send an analyst the rows for the
   screen it builds, not the whole inventory, and never re-read the images to do it. Say
   plainly that a row is what a screenshot showed, so a contradiction with the code comes
   back as a finding instead of being silently resolved in the agent's favour;
4. **the findings the earlier stages already paid for**, copied from the sidecar: the
   analyst's `FILES TO CHANGE`, `PATTERN / REUSE` and `RISKS` rows go to the implementer;
5. its slice of the approved plan, verbatim;
6. any decision the user made at a gate, in the user's own words.

Never paste the codebase into a prompt, and never read source files yourself. A cited
`path:line` is what travels between stages — the agent at the other end opens the file.

This is what the sidecar is for: it is the ticket's memory, and it outlives every agent's
context and any compaction of yours. Append each stage's findings **as that stage finishes**,
not at the end — an interrupted run that resumes reads the sidecar, and anything you did not
write down is lost. Re-read it with `sidecar show <KEY>` after a compaction rather than
reconstructing from memory.

Re-check both halves of freshness before the Plan presentation and before Implement:

```bash
.claude/hooks/ticket-freshness.sh check <KEY>     # exit 3 = stale; FRESHNESS.md says what each verdict forces
```

## 4. Stop at IMPLEMENTED — and hand over to the human

Set `state: IMPLEMENTED` and stop. Do not run the checks, do not review, do not commit.

`IMPLEMENTED` is the pause: the code is written and nothing has judged it. The dev reads it
now, and typically tweaks it — that is expected, and is why the reviewer runs afterwards
rather than before.

Your closing report must tell them, in this order:

1. **what changed**, per repo, with the mode, the tree path and the branch;
2. **how to read it**: `git -C <tree> diff <base>...HEAD`, with `<tree>` as
   `ticket-worktree.sh tree` returned it — in-place that is the repo itself, so say so
   plainly: *"this is checked out in your own `<repo>/` right now"*;
3. **what to run next**: `/implement-review <KEY>` — it validates, reviews and commits;
4. **the push warning**, whenever the work may outlive today:

   > This ticket lives only on this machine — the branch is local and `.work/<KEY>/` is never
   > committed. If anyone else may need to pick it up, push the branch before you stop:
   > `git -C <tree> push -u origin <branch>`

   Say it plainly. An unpushed local branch plus an absent dev is how one delivered ticket
   gets implemented twice.

## 5. Stop conditions

Set `blocked:` in the sidecar, report, and stop — rather than working around it — when the
ticket is ambiguous in a way that changes what gets built; the ticket changed materially in
Jira mid-flight; the ticket already carries a delivery comment or has moved past
implementation; the base branch moved and the rebase conflicts; something the ticket needs is
absent from the base; a requirement contradicts the codebase; or the tree holds changes that
are not this ticket's.

**Edit only inside the tree `ticket-worktree.sh tree` names, and only for the repos in scope.**
In worktree mode that means never touching `fk-admin-panel-be/`, `fk-admin-panel-fe/` or
`fk-mobile/` themselves — the point of the worktree is that the user's checkouts stay exactly
as they left them. In-place the user has explicitly handed you one of those checkouts for one
repo; the other two are still off limits, as is any file in that repo unrelated to this
ticket. The gate has not moved: nothing is edited before the user approves the plan.

## 6. Report

Short: ticket key, state reached, repos with their branch and worktree path, the diff command
per repo, `/implement-review <KEY>` as the next step, the push warning, anything blocked.
Reference `.work/<KEY>/work.md` rather than reproducing it.

Never claim the change is validated, reviewed or done. It is `IMPLEMENTED`, which means code
was written and nothing more.
