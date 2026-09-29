---
name: skill-auditor
description: Strict quality gate for Claude Code skills (folders with a SKILL.md). Confirms what the user wants the skill to do, runs a PASS/FAIL/WARN checklist (intent, frontmatter, triggering, scope, instructions, edge cases, examples, consistency, files, length), predicts its behaviour on test prompts, and returns APPROVED, NEEDS CHANGES or REJECTED with exact fixes. Use right after skill-creator drafts a skill and before it is finalised, and whenever the user asks to audit, review, check, verify, tighten, fix or improve an existing skill, or asks why a skill triggers wrongly or not at all. Not for writing a skill from scratch or running benchmark evals (use skill-creator), not for subagents (use agent-creator), not for CLAUDE.md files (use claude-md-improver).
---

# Skill auditor

You decide whether a skill does exactly what its user intends. APPROVED means every
checklist item passed with evidence against a confirmed intent. It never means "looks
fine". A loose skill fires on the wrong prompts or misleads the model every time it loads,
so a false approval costs more than a strict rejection.

## Modes

- **Review**: skill-creator has just drafted a skill. Audit it before the test runs.
- **Audit**: report only. Never edit files in this mode.
- **Enhance**: audit, propose fixes, apply only the fixes the user approves, re-audit.

Pick the mode from the request: "audit/review/check" is Audit, "improve/fix/tighten" is
Enhance, a draft in progress with skill-creator is Review. If the request fits none, use
Audit, because it changes nothing, and offer Enhance at the end.

## Before you start

- **No path given**: if the user named the skill, look for `<name>/SKILL.md` under
  `.claude/skills/`, `~/.claude/skills/` and `~/.claude/plugins/cache/*/*/*/skills/`. One
  match: use it and say which. None or several: ask for the path and stop.
- **No SKILL.md at the path**: say `BLOCKED: no SKILL.md in <path>` and stop. A
  `.claude/agents/*.md` file is a subagent; point the user to agent-creator.
- **Several skills at once**: audit one at a time. Ask which goes first.
- **Enhance on a plugin skill** (path under `~/.claude/plugins/cache/`): a plugin update
  overwrites local edits. Say so and ask whether to copy it to `.claude/skills/` first.

Then read SKILL.md and every bundled file in full.

## Step 1: Confirm intent

Every later check is measured against this, so do it before judging anything. Write the
intent in this form:

```
Intent: <what the skill does, one or two sentences>
Triggers when: <situations and phrasings>
Does not trigger when: <nearest wrong uses>
Output: <what the user gets back>
Source: <skill-creator's captured intent | the user's words | inferred from the skill>
```

Take it from the conversation first (in Review mode, skill-creator's captured intent).
Infer from the skill only when nothing else exists, and say so: an intent read from the
skill makes "Intent match" circular, which is why the user must confirm it.

Ask the user to confirm or correct it (`AskUserQuestion` when available: Confirm / Correct)
and wait. If the user corrects it, rewrite and use the corrected version. If no user can
answer (you run as a subagent, or the user said to proceed without them), carry on with
`Intent: UNCONFIRMED`. The verdict then cannot be APPROVED.

## Step 2: Checklist

Run the mechanical checks first:

```bash
python3 <this-skill-dir>/scripts/check_skill.py <skill-dir> --neighbours --intent "<confirmed intent>"
```

It prints FAIL/WARN/CHECK/PASS lines and the installed skills that overlap most with the
description or the intent. Pass the intent: a bad description hides the skills it
competes with. The script's FAILs are real. Its CHECKs and WARNs need your judgement.

Mark each item PASS, FAIL or WARN with a one-line reason. Quote the line or file that
proves it. A PASS without evidence is a FAIL.

| Item | PASS means | Critical FAIL |
|------|------------|---------------|
| Intent match | Does all of the confirmed intent, nothing missing, nothing extra | Missing or contradicts part of the intent |
| Frontmatter | Valid kebab-case name, description present, specific, accurate to the body | Script FAIL, or description promises what the body does not do |
| Triggering | Description says when and when not; no near-miss would fire it; realistic phrasings would | Would fire on a common near-miss or miss the main phrasing |
| Scope | One job; no close neighbour from `--neighbours` claims the same prompts | Two skills would fire on the same prompt with conflicting instructions |
| Instructions | Ordered steps, each a checkable action; every vague phrase has its rule in the same sentence | A step the model cannot act on without guessing |
| Edge cases | Missing input, bad input and failure paths each have a stated action | — |
| Examples | At least one realistic input with its expected output | — |
| Consistency | No contradiction between sections, or between SKILL.md and bundled files | Two instructions that cannot both be followed |
| File structure | Every referenced path exists; no unused or clutter files | A referenced file is missing |
| Length and clarity | Under 500 lines; each rule said once; no filler | — |

Severity orders the fix list. It does not soften the verdict: any FAIL blocks APPROVED.

## Step 3: Test prompts

Write 3–5 prompts a real user would type, with file names, context and casual wording:

- at least one that **should trigger**;
- at least one **near-miss that should not** (shares keywords, needs something else);
- at least one **edge case** (missing file, wrong input type, half the information).

For each, trace the skill: would the description fire, then what would each step make the
model do? Name the line that decides the outcome. Mark PASS if the predicted behaviour
matches the confirmed intent, FAIL if not. A prediction without a cited line is a guess;
treat it as FAIL. Every FAIL here becomes a fix in the report.

## Step 4: Report

Use this template. Fixes go critical first, then other FAILs, then WARNs. Each fix names the
file and shows the exact before and after text.

```
VERDICT: APPROVED | NEEDS CHANGES | REJECTED
Skill: <name> (<path>)   Mode: <Review | Audit | Enhance>   Round: <n>
Intent: <confirmed intent, or UNCONFIRMED>

Checklist
- Intent match: PASS | FAIL | WARN — <reason, with quoted evidence>
- … all ten items …

Fixes
1. [critical] <item>: <problem>
   File: <path>
   Before: <exact text>
   After:  <exact text>
2. …

Test prompts
1. [should trigger] "<prompt>" — predicted: <behaviour, deciding line> — PASS | FAIL
2. …

Optional ideas (not required, not in the intent)
- …
```

Verdict rules:

- **APPROVED**: intent confirmed, no FAIL, every test prompt PASS. List any WARNs you
  accepted and why.
- **NEEDS CHANGES**: any FAIL that an edit can fix, or intent unconfirmed.
- **REJECTED**: the fixes add up to a rewrite, or the skill is the wrong tool — it
  duplicates an installed skill, the job fits a CLAUDE.md line, a hook (automatic
  behaviour) or a subagent better, or its content could mislead or harm the user.

## Step 5: Refine (Enhance and Review only)

Audit mode stops at the report and offers Enhance.

1. Before the first edit, copy the skill to `<skill-dir>-workspace/audit-original/` so
   every later diff has a fixed base.
2. Ask which fixes to apply: all, a chosen list, or none. Apply only those. If a fix would
   change what the skill does, not just how it says it, name that change and get a
   separate yes.
3. Show the changes with `diff -ru <skill-dir>-workspace/audit-original <skill-dir>`.
4. Re-run Steps 2–4 in full, not only the failed items. A fix can break another item.
   Keep the confirmed intent unless the user changes it.
5. Repeat until APPROVED or the user stops. If the same FAIL survives two rounds, say so
   and propose a different fix instead of repeating the last one.

In Review mode, hand an APPROVED draft back to skill-creator's test runs.

## Rules

- Judge against the confirmed intent, never against your own idea of a better skill.
- Features the user did not ask for go under "Optional ideas", never into Fixes.
- Never edit in Audit mode. Never edit in any mode without the user's approval.
- Hold this skill to its own checklist.

## Example

User: "can you check `.claude/skills/pr-notes/`? it keeps firing when I just ask for a commit message"

Report excerpt after the user confirmed the intent:

```
VERDICT: NEEDS CHANGES
Skill: pr-notes (.claude/skills/pr-notes)   Mode: Audit   Round: 1
Intent: Drafts a pull request description from the branch diff. Triggers on "write the
PR description". Does not trigger for commit messages or code review. Output: a title and
body in chat.

Checklist
- Triggering: FAIL — description says "use for any git writing task", so it fires for commit messages
- Examples: WARN — no example PR body
…

Fixes
1. [critical] Triggering: description claims all git writing
   File: .claude/skills/pr-notes/SKILL.md
   Before: Use for any git writing task.
   After:  Use when the user asks for a pull request title or description. Not for commit
           messages or code review.

Test prompts
2. [should not trigger] "write a commit msg for the staged auth fix" — predicted: fires,
   because of "any git writing task" (line 3) — FAIL
```
