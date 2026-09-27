---
name: ticket-writing
description: Turn raw Product Owner input — text, chat, screenshots — into a build-brief ticket (goal, numbered acceptance criteria, decisions already made, out of scope, files to touch, a real pattern to follow) and raise it in Jira through the project `jira` MCP server. Use whenever asked to write, draft, raise, log or create a ticket, issue, bug or task, especially with screenshots or a vague request. Never implements; never saves a local file.
---

# Ticket writing (Jira)

Turn raw Product Owner (PO) input into a ticket someone can build from **without asking
anything and without guessing**. The reader may be a developer or an agent running
`/implement-ticket`; either way the conversation is gone.

Two sections close most gaps: **Decisions already made** (every question the build could
get wrong, with its answer) and **Out of scope** (every neighbouring change ruled out by
name — unlisted means "maybe", and "maybe" gets built). The rest points at the code. The
ticket never designs the solution: no new function names, no schema, no approach.

**Never implement the requested change.** This skill ends at a created Jira issue.

## 0. Three skills do the thinking; this one writes the ticket

They own their subject outright. This skill does not restate or contradict them.

| Skill | Owns | Load |
|---|---|---|
| `requirement-evidence-and-gating` | Tags, ledger, coverage, materiality, question rounds, placeholder ban, the legitimate `UNKNOWN`, the gate verdict and the `BLOCKED` report | **Always**, first, before refining anything |
| `screenshot-requirement-analysis` | Reading every supplied image, and whether several images are one requirement | **Only when images arrived** (paths or a caller's inventory) |
| `business-requirement-writing-style` | The wording of the requirement sections | **At drafting time (§7)**, not at intake |

Each costs 2.5–3.3k tokens that are re-served on every later call, so load one only when it
has work to do.

## 1. The Jira server, local files — the one owner of this rule

The only Jira surface is the MCP server in this workspace's [`.mcp.json`](../../../.mcp.json):
server `jira`, tools `mcp__jira__*`, already scoped by `--jira-projects-filter`.

Forbidden, even when connected and even when it looks the same:

- any other Atlassian/Jira MCP server from user-level config or a plugin — e.g.
  `mcp__MCP_DOCKER__*`, `mcp__atlassian__*`, `mcp__jira-247crm__*`, an `atlassian` skill;
- `curl`, `uvx`, `acli` or any REST call to Jira;
- **saving the ticket to disk** — no `tickets/*.md`, sidecar or draft file, not even when
  asked to "save it too". The Jira issue is the ticket. Offer the key, the link, or the
  body pasted in chat.

If no `mcp__jira__*` tool is available, **stop and say the project Jira MCP server is not
connected**. That is the whole report. No other server, no file instead.

Project key and every call: [`JIRA.md`](JIRA.md).

## 2. Triage

[`TRIAGE.md`](TRIAGE.md) owns the order (its §0), the duplicate check, the existence
verdict and the tier. A duplicate or `ALREADY_IMPLEMENTED` ends the workflow with the
"already exists" report (§10). `CODEBASE` claims mean code read **at the branch for the
affected environment**, not whatever is checked out.

## 3. Evidence → sections

The evidence skill's ledger is the input to §7:

| Ledger row | Lands in |
|---|---|
| `USED` — an outcome the user sees | `Acceptance criteria` |
| `USED` — a rule, value, threshold, label or format | `Decisions already made` |
| `QUESTION`, answered | `Decisions already made`, written as the answer |
| `CODEBASE` — what the code does today | `Files/areas to touch`, or a decision when it settles behaviour |
| `UNVERIFIABLE` | `Decisions already made`, as an unknown line (`TEMPLATE.md`) |
| `SCOPE-OUT` | `Out of scope`, stated once, no invitation to revisit |

**Jira field values are evidence too.** Issue type, label, component, version, parent,
priority and assignee are set only when the requester stated them or the project's
metadata provides them (`JIRA.md` §4). An inferred value is an `INFERENCE` with a field name
on it, and it stays out.

## 4. Screenshots — one Jira limit

The MCP server **cannot upload attachments**. So `Images` carries one line per screenshot
from the inventory (`TEMPLATE.md`), and the report tells the requester to attach the files
(§10). Never imply they were attached.

## 5. Language

- `business-requirement-writing-style` owns the wording of Goal, Acceptance criteria,
  Decisions already made and Out of scope.
- `Files/areas to touch` and `Existing patterns to follow` are technical by design: repo
  paths, and in plain words what each file does today. Still no prescribed design.
- **Audience.** Developers, QA testing by hand (there is almost no automated coverage),
  and agents building from the ticket. Criteria must pass or fail from the ticket alone.
- **Whose labels.** Product labels come from the repos' own UI. Where web and mobile label
  the same thing differently, say which one the ticket means.
- **Spelling and tone:** `plain-uk-english`. Product labels and identifiers stay verbatim.

## 6. The gate, in Jira terms

The gate is the evidence skill's (§6–§9 there): `BLOCKED` means no issue at all. Local rules:

- The placeholder ban covers the whole description. A created issue sits in a shared
  backlog, and someone will build from whatever it says.
- A gap you noticed but did not ask about is not covered by `If something isn't covered
  here`. That line is for what nobody foresaw. A foreseen, material gap goes to the
  requester before creating.

## 7. The ticket itself

**Summary** — one line, the change in the product's own words. No trailing full stop, no
issue key, no "As a user". Match a clear convention in the issues the duplicate search
returned (`JIRA.md` §2); none → this rule.

**Description** — [`TEMPLATE.md`](TEMPLATE.md), exactly. It owns every section, its order,
its fixed lines and what goes in it. The tier sets how much goes in each (`TRIAGE.md` §3).
Name the environment and product area in the text — the reader has no conversation. Direct
prose, no padding.

## 8. Gate B — confirm, then create

Creating an issue is outward-facing and deleting one is not a clean undo. Before the create
call, show the assembled summary and the seven brief sections and ask once:

> Raise this in Jira as written? (Yes, create it / No, and here is what is wrong)

Corrections are `EXPLICIT` evidence: fold them in and ask again. Nothing is created until
the answer is yes. No question tool (a subagent) → hand the draft and this question to the
caller, and create only when resumed with a yes.

Then create per `JIRA.md` §4 — one issue, read back. Do not transition, assign, comment on
or add watchers to it; it stays in the project's default status.

## 9. Validation — all pass before the create call

Delegated — confirm each came back clean:

- **Gate** `PASSED`; coverage ran both ways; placeholder search found nothing.
- **Images**, when supplied: every one reported on; the ticket follows the relationship the
  screenshot skill concluded. None supplied → the skill was not loaded.

Local:

- **No duplicate**: searched with more than one phrasing (`TRIAGE.md` §1).
- **Environment**: named where it matters; current behaviour read at *that* branch.
- **Template**: every `TEMPLATE.md` section in order, headings and fixed lines verbatim, no
  section added, no `[bracket]` left, `Read at:` line filled; tier content per `TRIAGE.md` §3.
- **Criteria**: numbered; each can fail by hand; edge cases on their own lines.
- **Decisions**: each a value or rule, not a topic; every gate answer present.
- **Out of scope**: not empty; every `SCOPE-OUT` row; the obvious neighbours named.
- **Paths**: every path in the two technical sections was opened at the named branch.
- **Language**: no design detail outside the two technical sections, none prescribed in them.
- **Fixed sections**: ticks, `SEVERITY` and `TIME ESTIMATE` per `TEMPLATE.md` evidence rules.
- **Jira fields**: key from `.mcp.json`; type exists; every field and value allowed.
- **Confirmed**: gate B answered yes (§8).

## 10. Report

Raised:

```
Ticket raised in Jira.

Issue:   <KEY> — <summary>
Link:    <the browse_url Jira returned>
Type:    <issue type> · tier <T1|T2|T3> · severity <value or "not set">

Summary: <one-line summary of the requirement>
```

Screenshots supplied → add: `Attach the <n> screenshot(s) to <KEY> — the MCP server cannot
upload them.` Do not reproduce the body unless asked. Never state a link Jira did not return.

Gate `BLOCKED` → the evidence skill's §9 report, first line `No ticket raised — requirement
not sufficiently defined.`

Triage ended it:

```
No ticket raised — this already exists.

Evidence:
- <existing issue key, or file:line / branch ref proving the outcome already holds>

State: ALREADY_IMPLEMENTED | DUPLICATE_OF <KEY>   (or PARTIALLY_IMPLEMENTED, with what remains)

Options: close it, or reframe it as <the specific change that would still be needed>.
```

Which option to take is the requester's call, never yours.
