# Description template — the body of the Jira issue

This file owns the sections: their names, order, fixed lines and what goes in each. Fill
it and pass it as `description` to `mcp__jira__jira_create_issue` (`JIRA.md` §4).

- Same sections, same order, same headings and fixed lines. **No section added** — an
  extra section is how open questions get smuggled in. No section dropped for being short.
- Text in `[brackets]` is instruction. Replace it; never send it.
- No `## Description` heading — in Jira this whole body *is* the description.
- How much each section holds depends on the tier (`TRIAGE.md` §3).

The first seven sections are the build brief. A developer or an agent builds from them
without the conversation. Anything they would have to guess is a gap in the ticket. The
last four are the team's fixed sections.

---

## Goal

[One or two sentences. The problem as the user meets it, and the outcome once fixed. T2/T3:
the outcome is stated so anyone could tell it worked (the success measure). T3: stated as a
problem, not a solution. No design.]

## Acceptance criteria

1. [One observable outcome per line: who does what, where, and what they then see. Each
   passes or fails on its own, by hand, from this ticket alone.]
2. [Edge cases get their own line — empty state, no permission, invalid input, the boundary
   value. "Works correctly" or "is user-friendly" cannot fail, so it is not a criterion.]

## Decisions already made

- **[Topic]:** [the answer]. ([source — PO, screenshot n, or the code at `<branch>`])

[Answers, never topics. Every answered question, business rule, exact value, label, format
and threshold — anything a builder would otherwise pick for themselves. "Sort order: newest
first (PO)" is a decision; "Sort order to be agreed" is a placeholder and blocks creation.
A system fact that could not be verified (evidence skill §8) goes here as
"**[Topic]:** unknown — [what was tried]; [why it does not block the build]." T1 with
nothing to decide: "None beyond the acceptance criteria."]

## Out of scope

- [One line per thing a keen builder might add or change, and must not.]

[Never empty. Every `SCOPE-OUT` row, anything another open issue owns (with its key), and
the obvious neighbours: the same change on the other platform, the other list, the bulk
version, the filter nobody asked for, a refactor of the file being touched.]

## Files/areas to touch

Read at: `<repo>@<branch>`

- `<repo>/<path>` — [what it does today, and what changes there]

[The first line names the branch the paths were read at, once. Only paths opened during
triage. A repo in scope where nothing was read: name the repo and product area in words.
Plain description of what each file does is fine; a prescribed design is not — "the list
page; the export button goes in its toolbar", not "add a `useExport` hook".]

## Existing patterns to follow

- `<repo>/<path>` — [the similar feature, and what to copy from it]

[A real file in the same repo that already solves a similar problem, opened during triage.
None found → "None found in <repo> — no similar feature exists." An invented path is worse
than none: the builder will trust it.]

## If something isn't covered here

Stop and ask on this ticket before building it. Do not guess.

[Keep the line above verbatim. Add a narrower line under it only when the requester gave
one — e.g. "Where web and mobile differ, follow web." Never loosen the default.]

## Images

*Insert images here.

[No screenshots supplied: keep the line above verbatim. Supplied: replace it with one line
per screenshot saying what it establishes — e.g. "Screenshot 1 — Employees list, Active
filter applied, showing the columns to be exported." The requester attaches the files.]

## Affected System(s)

- [ ] IOS
- [ ] Android
- [ ] Web
- [ ] Backend
- [ ] DB

[Tick a box only when `EXPLICIT`, `VISUAL` or `CODEBASE` evidence puts that system in
scope. "The build will probably touch the DB" is an inference — leave it unticked.]

## Other Info

SEVERITY: Low, Medium, High
TIME ESTIMATE:

MERGED TO STAGE: [ ]

MERGED BACK TO DEVELOP: [ ]

[SEVERITY: replace the option list with the value the PO stated. None stated → leave it as
`SEVERITY:` with nothing after it. Never rate it yourself. TIME ESTIMATE: blank unless the
requester stated an appetite — a budget the scope must fit, never your prediction. The two
MERGED boxes stay unticked.]

## Resolution

To be updated*
