---
name: session-retro
description: Run a retrospective on the current (or a named) coding session and
  propose environment changes so future sessions go better — routing each lesson
  to the cheapest enforcement layer (guardrail, hook, skill, router, doc or
  memory) and deduping against what already exists. Use when a coding session
  ends, when the user types /session-retro, or whenever they say "retro this",
  "what should we change", "capture what we learned" or "how do we stop this
  recurring". Proposes only; writes nothing without approval except a memory
  file. Not for auditing or rewriting CLAUDE.md on its own (claude-md-improver),
  writing a ticket, reviewing a diff, or fixing a bug — this reshapes the whole
  workspace environment from one session's evidence, not the code.
---

# Session Retro

Answer first: this skill reads a session and returns a ranked list of
**environment** changes — not code changes. Each finding names the one cheapest
layer that fixes it and the exact edit. The weights don't learn between
sessions; this is how you learn *for* the agent.

## The one idea

Every recurring lesson belongs in exactly one layer. Pick the cheapest that
actually enforces it. Cheaper = fires automatically, costs no tokens at run
time, can't be skipped under context pressure.

Routing ladder (cheapest first):

1. **Deterministic check** — `.claude/guardrails/` or `.claude/hooks/`, lint,
   typecheck, CI. For mechanical, syntactic rules: banned API, import shape,
   file location, forbidden command, secret/env edits. If a rule can be
   expressed as "never X" or "always Y in form Z", it goes here. Prose can't
   enforce it; a hook can.
2. **Skill** — `.claude/skills/<name>/`. On-demand standards or docs loaded only
   when a task matches. For judgment calls that need explaining, not blocking.
3. **CLAUDE.md router line** — navigation only. "Where does X live", "which repo
   owns Y". Keep it thin. A standard is never a router line.
4. **docs/** — reference material too long for a skill, read on demand. (Local,
   untracked here — never add to tracked git.)
5. **Memory** — `~/.claude/projects/.../memory/`. Cross-session facts and user
   feedback that don't fit the four above. The "why" lives here.

If a lesson is already prose in CLAUDE.md but is mechanical → that's a finding:
promote it to a guardrail/hook and delete the prose.

## Second axis — shared or personal

The ladder above picks the cheapest layer. A team building one codebase needs a
second decision on every finding: does this bind everyone, or just you?

- **SHARED** — reaches teammates, but only through git. These live in the
  tracked workspace repo: `.claude/guardrails/`, `.claude/hooks/`,
  `.claude/skills/`, `.claude/commands/`, `.claude/agents/`, and `CLAUDE.md`.
  A finding here is not done until it is **committed and pushed**, and the
  teammate has pulled.
- **PERSONAL** — your machine only, never shared: `~/.claude/` (global skills,
  settings), the memory dir under `~/.claude/projects/`, and `docs/` (untracked
  in this workspace).

Rule: if a lesson should bind everyone building this codebase — a convention
across fe, be and automation-testing, a shared check, a navigation fact — route
it to a SHARED layer **even when a personal layer is cheaper**, and the finding
is not complete until it is committed and pushed. A personal preference (your
own tone, your own shortcut) stays personal. **A team convention parked in
personal memory is itself a finding** — it is why one teammate's agent drifts
from another's.

## Steps

1. **Load context.** Read `plain-uk-english` for output style. Read `MEMORY.md`
   and list `.claude/guardrails/`, `.claude/hooks/`, `.claude/skills/` so you
   know what already exists. This is the dedup set.
2. **Read the session.** Use the current session unless the user names another.
   Prefer the live transcript you already hold. If the user names a past session
   and you cannot see it, session logs live under
   `~/.claude/projects/<slugged-cwd>/` as `.jsonl` files — read the matching one;
   if none matches, say so and ask the user to paste or name it rather than
   guessing. Pull the primary sources: what the user corrected, what was
   retried, what was searched for repeatedly, what tools no-op'd or got denied.
3. **Scan for findings** across these signals:
   - **Prose that should be a check** — a rule stated in CLAUDE.md/docs/skill
     that the agent still broke, or that is purely mechanical. → layer 1.
   - **Repeated correction** — the user said the same thing more than once, or a
     thing they've said before (check MEMORY.md). → layer 1 if mechanical, else
     memory/skill.
   - **Navigation miss** — agent couldn't find a file, resolver, or convention
     and had to grep around. → router line or docs pointer.
   - **Missing guardrail** — a destructive or irreversible action went
     unguarded. → layer 1. Flag even if nothing went wrong this time.
   - **Wasted tool pattern** — same failed call shape, denied permission, or
     no-op repeated. → permission allowlist, hook, or a note.
   - **Uncaptured feedback** — a genuine preference or decision that lives
     nowhere. → memory file if personal to you; a SHARED layer (committed) if it
     is a team convention everyone should follow.
   - **Team lesson stuck on a personal layer** — a convention that belongs to
     everyone but sits in your memory, your global `~/.claude`, or untracked
     `docs/`. → re-home it to a SHARED layer so teammates' agents stop drifting.
4. **Dedup.** Drop any finding already covered by an existing guardrail, hook,
   skill, router line or memory. For near-duplicates, propose *updating* the
   existing artefact, not a new one.
5. **Present, ranked by severity.** Severity = how often it bit × how costly the
   bite. One block per finding:

   ```
   ### <short title>  [severity: high|med|low]
   Finding:   <what recurs>
   Evidence:  <the moment in the session — quote the correction or the retry>
   Layer:     <guardrail | hook | skill | router | docs | memory>
   Scope:     <shared — commit + push so teammates get it | personal — your machine>
   Change:    <exact edit — file path + the line/rule to add or promote>
   Dedup:     <none | updates existing <artefact>>
   ```

6. **Gate.** Propose only. Write nothing except a memory file (the memory system
   is write-direct), and even then confirm the slug first. Guardrails, hooks,
   skills and CLAUDE.md edits wait for the user's go-ahead — one at a time. For a
   **shared** finding, saying the edit is not enough: end it with "commit + push
   so teammates' agents pick it up", and never push on your own (the user decides
   when a branch leaves the machine).

## Principles

- **Implement vs review.** The implementing agent is under context pressure and
  will skip prose rules. Push enforceable standards to deterministic checks or
  to review-time, not to a note it reads while debugging.
- **No new file if an old one fits.** Updating beats adding. Sprawl is a cost.
- **A repo with no lint/typecheck/test gate is itself a finding**, even on a
  clean session.
- **Never auto-edit guardrails or CLAUDE.md.** Those are enforced, not advisory;
  the human owns them.

## Edge cases

- **Nothing worth proposing.** A clean session with no recurring lesson is the
  normal, good outcome. Say "No environment changes — the session was clean" and
  stop. Never invent a finding to fill the list.
- **No log found.** User names a past session you cannot locate under
  `~/.claude/projects/`. Say which paths you checked and ask them to paste or
  name it. Do not retro a session you cannot read.
- **Not a Lodestar workspace.** No `.claude/guardrails/` or `.claude/hooks/`
  present. Fall back to the layers that do exist here — lint/CI config,
  `CLAUDE.md`/`AGENTS.md`, docs, memory. Report the missing guardrail layer
  itself as a finding (layer 1): there is nowhere to put a mechanical rule.
- **No memory system.** No `MEMORY.md` or memory dir. Skip the memory layer and
  the dedup-against-memory step; propose the other layers only.
- **Workspace not under git.** `.claude/` is not tracked (no repo, or ignored).
  Then no layer is truly SHARED — say so, and tell the user a team lesson needs
  the workspace committed first before it can reach a colleague. Do not pretend a
  local edit will propagate.

## Example

Input: "/session-retro" after a session where the user twice corrected a commit
message that carried a `Co-Authored-By` line.

Output (one finding):

```
### Commit messages keep adding Co-Authored-By  [severity: high]
Finding:   Co-Authored-By trailer added to commits twice this session.
Evidence:  User: "no Co-Authored-By line" (twice, on the auth and schema commits).
Layer:     guardrail (mechanical — a banned trailer, not a judgement call)
Scope:     shared — every teammate's commits must follow this, so it belongs in
           the tracked repo; commit + push so their agents enforce it too.
Change:    Add .claude/guardrails/block-coauthor-trailer.md — reject any commit
           message containing "Co-Authored-By".
Dedup:     Updates intent of existing memory commit-message-style.md, which
           states the rule as prose, is personal to you, and does not enforce it.
           Promote to a shared guardrail; keep the memory note as the "why".
```

Then: propose only, wait for the user's go-ahead before writing the guardrail,
and because the scope is shared, finish with "commit + push so teammates get it".

## Not this skill

Writing or reviewing code. Raising tickets. Pushing. Diagnosing a live bug.
Auditing CLAUDE.md on its own (that is claude-md-improver). Those have their own
skills — route to them, don't absorb them.
