---
name: ticket-writing
description: Turn raw Product Owner input — text, chat, screenshots — into a build-brief ticket (goal, numbered acceptance criteria, decisions already made, out of scope, files to touch, a real pattern to follow) and raise it in Jira through the workspace's board server (FKC or SUBC — `BOARDS.md` resolves which), with the screenshots attached. Also extends an existing issue with new or changed requirements. Use whenever asked to write, draft, raise, log or create a ticket, issue, bug or task, or to add to, amend or extend an existing ticket, especially with screenshots or a vague request. Never implements; never saves a local file.
---

# Ticket writing (Jira)

Turn raw Product Owner (PO) input into a ticket someone can build from **without asking
anything and without guessing**. The reader may be a developer or an agent running
`/implement-ticket`; either way the conversation is gone.

Two sections close most gaps: **Decisions already made** (every question the build could
get wrong, with its answer) and **Out of scope** (every neighbouring change ruled out by
name — unlisted means "maybe", and "maybe" gets built). The rest points at the code. The
ticket never designs the solution: no new function names, no schema, no approach.

**Never implement the requested change.** This skill ends at a created Jira issue, or an
existing one extended ([`UPDATE.md`](UPDATE.md)).

## 0. Three skills do the thinking; this one writes the ticket

They own their subject outright. This skill does not restate or contradict them.

| Skill | Owns | Load |
|---|---|---|
| `requirement-evidence-and-gating` | Tags, ledger, coverage, materiality, question rounds, placeholder ban, the legitimate `UNKNOWN`, the gate verdict and the `BLOCKED` report | **Always**, first, before refining anything |
| `screenshot-requirement-analysis` | Reading every supplied image, and whether several images are one requirement | **Only when images arrived** (paths or a caller's inventory) |
| `business-requirement-writing-style` | The wording of the requirement sections | **At drafting time (§7)**, not at intake |

Each costs 2.5–3.3k tokens that are re-served on every later call, so load one only when it
has work to do.

## 1. The Jira servers, local files — the one owner of this rule

The Jira surface is the `mcp-atlassian` servers in this workspace's
[`.mcp.json`](../../../.mcp.json) — `jira` (FKC) and `jira-247crm` (SUBC) today, each scoped
by its own `--jira-projects-filter`. [`BOARDS.md`](BOARDS.md) resolves which board a request
targets; every call goes to that board's server and no other.

Forbidden, even when connected and even when it looks the same:

- any Atlassian/Jira MCP server **not in this workspace's `.mcp.json`** — a user-level or
  plugin server such as `mcp__MCP_DOCKER__*`, `mcp__atlassian__*`, or an `atlassian` skill;
- `uvx`, `acli` or a REST call to Jira — one sanctioned exception: the 247crm attachment
  fallback in `BOARDS.md` §3, because that site's MCP server has no upload tool;
- **saving the ticket to disk** — no `tickets/*.md`, sidecar or draft file, not even when
  asked to "save it too". The Jira issue is the ticket. Offer the key, the link, or the
  body pasted in chat.

If the resolved board's `mcp__…__*` tools are not available, **stop and say that board's
Jira MCP server is not connected**. If no board resolves at all — no `.mcp.json`, or it holds
no `mcp-atlassian` server — **stop and say no Jira board is configured** (`BOARDS.md` §1 step
6). Either way that is the whole report. No other server, no file instead.

Which board, which server, which profile: [`BOARDS.md`](BOARDS.md). Every call: [`JIRA.md`](JIRA.md).

## 2. Triage

[`TRIAGE.md`](TRIAGE.md) owns the order (its §0), the duplicate check, the existence
verdict and the tier. A duplicate or `ALREADY_IMPLEMENTED` ends the workflow with the
"already exists" report (§10). If the requester then chooses to extend the existing issue,
or asked to amend a named issue from the start, follow [`UPDATE.md`](UPDATE.md) instead of
§7–§10. `CODEBASE` claims mean code read **at the branch for the
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

## 4. Screenshots — attach what has a file

The board attaches files by its own method — FKC through `jira_update_issue`'s
`attachments` input, SUBC through the REST fallback (`JIRA.md` §5, `BOARDS.md` §3). Either
way it can only upload a file that exists on this machine, so:

- **A screenshot with a file path** — attach it to the issue straight after creating it.
- **A screenshot pasted inline** that arrived only as a caller's written inventory — there
  is no file to upload. It is still evidence (`VISUAL`, for what the inventory records),
  but the requester attaches it by hand, and the report says so (§10).

Either way `Images` carries one line per screenshot (`TEMPLATE.md`), so the ticket reads
the same whichever way the file arrives. Say a file is attached only when the read-back's
`attachment` field lists it.

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

- **The gate blocks only on a material requirement gap** — an undefined rule, value, label or
  scope the builder would otherwise guess. It does **not** block on which board, which server,
  or how to place code: the board is settled in `BOARDS.md` §1, and raising on the resolved
  board is always a valid forward action. A board or workflow tangle is never a reason to
  refuse; if every option you are about to offer is blocked, re-resolve the board and proceed.
- The placeholder ban covers the whole description. A created issue sits in a shared
  backlog, and someone will build from whatever it says.
- A gap you noticed but did not ask about is not covered by `If something isn't covered
  here`. That line is for what nobody foresaw. A foreseen, material gap goes to the
  requester before creating.

## 7. The ticket itself

**Summary** — one line, the change in the product's own words. No trailing full stop, no
issue key, no "As a user". Jira refuses more than 255 characters; aim for under 100, so it
reads in a board card. Detail goes in the description, not the summary. Match a clear
convention in the issues the duplicate search returned (`JIRA.md` §2); none → this rule.

**Issue type** sets the shape inside the sections. A `Bug` carries actual behaviour,
expected behaviour, where it was seen and steps to reproduce (`TEMPLATE.md`, "Bug"). A bug
report with no way to see the fault — no steps, no page, no environment — has a material
gap: ask before creating.

**Description** — [`TEMPLATE.md`](TEMPLATE.md), exactly. It owns every section, its order,
its fixed lines and what goes in it. The tier sets how much goes in each (`TRIAGE.md` §3).
Name the environment and product area in the text — the reader has no conversation. Direct
prose, no padding.

## 8. Gate B — confirm, then create

Creating an issue is outward-facing and deleting one is not a clean undo. Before the create
call, show the assembled summary, the issue type, the seven brief sections and the files
that will be attached, and ask once:

> Raise this in Jira as written? (Yes, create it / No, and here is what is wrong)

Corrections are `EXPLICIT` evidence: fold them in and ask again. Nothing is created until
the answer is yes. No question tool (a subagent) → hand the draft and this question to the
caller, and create only when resumed with a yes. **A relayed answer is consent:** a "yes"
that arrives through `AskUserQuestion` or a `SendMessage` relay is the requester's own word,
exactly as if typed here. Never read a relay as non-consent, and never re-ask gate B because
of a board or workflow tangle — only a new correction reopens it.

Then create per `JIRA.md` §4 — one issue — attach the screenshot files per `JIRA.md` §5,
and read it back. Do not transition, assign, comment on or add watchers to it; it stays in
the project's default status.

## 9. Validation — all pass before the create call

Delegated — confirm each came back clean:

- **Gate** `PASSED`; coverage ran both ways; placeholder search found nothing.
- **Images**, when supplied: every one reported on; the ticket follows the relationship the
  screenshot skill concluded. None supplied → the skill was not loaded.

Local:

- **No duplicate**: searched with more than one phrasing (`TRIAGE.md` §1).
- **Environment**: named where it matters; current behaviour read at *that* branch.
- **Board**: resolved from `.mcp.json` and the request (`BOARDS.md` §1); the ticket carries
  only the sections that board's profile keeps (`BOARDS.md` §2).
- **Template**: every section the profile carries, in order, headings and fixed lines
  verbatim, no section added, no `[bracket]` left; `Read at:` filled where the technical
  sections apply; tier content per `TRIAGE.md` §3.
- **Criteria**: numbered; each can fail by hand; edge cases on their own lines.
- **Decisions**: each a value or rule, not a topic; every gate answer present.
- **Out of scope**: not empty; every `SCOPE-OUT` row; the obvious neighbours named.
- **Paths**: on a board with local code, every path in the two technical sections was opened
  at the named branch; a no-code board omits those sections (`BOARDS.md` §2).
- **Language**: no design detail outside the two technical sections, none prescribed in them.
- **Fixed sections**: on FKC, ticks, `SEVERITY` and `TIME ESTIMATE` per `TEMPLATE.md`
  evidence rules; another board, only its own profile's fixed sections.
- **Summary**: 255 characters at most; no key, no full stop.
- **Bug**: a `Bug` has actual, expected, where seen and steps (`TEMPLATE.md`).
- **Jira text**: `JIRA.md` §3 and the board's `BOARDS.md` §3 quirks — other-site keys as
  explicit links, no HTML, no comments.
- **Jira fields**: key from `.mcp.json`; type exists on that board; every field and value allowed.
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

Screenshots supplied → add the line that is true:

- all attached: `Attached: <n> screenshot(s) — <file names>.`
- some or none had a file, or an upload failed: `Attach <file names or "the <n> pasted
  screenshot(s)"> to <KEY> by hand — <no file on this machine | upload failed: <reason>>.`

Do not reproduce the body unless asked. Never state a link Jira did not return.

Gate `BLOCKED` → the evidence skill's §9 report, first line `No ticket raised — requirement
not sufficiently defined.`

Triage ended it:

```
No ticket raised — this already exists.

Evidence:
- <existing issue key, or file:line / branch ref proving the outcome already holds>

State: ALREADY_IMPLEMENTED | DUPLICATE_OF <KEY>   (or PARTIALLY_IMPLEMENTED, with what remains)

Options: close it, extend <KEY> with this change (`UPDATE.md`), or reframe it as <the
specific change that would still be needed>.
```

Which option to take is the requester's call, never yours.

Extended an existing issue → the report in `UPDATE.md` §6.
