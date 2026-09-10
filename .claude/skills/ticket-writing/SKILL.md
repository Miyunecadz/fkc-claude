---
name: ticket-writing
description: Turn raw Product Owner input — text, chat messages, screenshots — into a refined, non-technical development ticket and raise it directly in Jira through this workspace's project-scoped `jira` MCP server. Use whenever asked to write, draft, raise, log or create a ticket, issue, bug or task from PO or stakeholder notes, especially when screenshots are attached or the request is vague and needs refining before development can pick it up. Never implements the change and never saves the ticket as a local markdown file.
---

# Ticket writing (Jira)

Turn raw Product Owner (PO) input into a ticket that answers **where this applies, what
the PO wants, what the user should experience, and what success looks like** — and never
**how a developer should build it**.

Two hard boundaries:

- **Never implement the requested change.** This skill ends at a created Jira issue.
- **Never save the ticket as a local file.** No `tickets/*.md`, no sidecar, no draft on
  disk. The Jira issue is the ticket. A local copy is a second source of truth that
  immediately goes stale.

## 0. Three skills do the thinking; this one writes the ticket

Load them **when they apply**, not as a set at intake. They own their subject matter
outright — this skill does not restate their rules and must not contradict them:

| Skill | Owns |
|---|---|
| `requirement-evidence-and-gating` | Evidence tags (`EXPLICIT`/`VISUAL`/`CODEBASE`/`INFERENCE`), the ledger, coverage so nothing is dropped, materiality, the question rounds, the placeholder ban, the legitimate `UNKNOWN`, and the "not sufficiently defined" report |
| `screenshot-requirement-analysis` | Reading every supplied image: page, tabs, labels, columns, filters, states, formats, annotations, before/after pairs, unreadable crops, and whether several images are one requirement |
| `business-requirement-writing-style` | The wording: refine-don't-transcribe, the vague-phrase table ("all information", "same as before", "properly"), non-technical-but-precise, the business-rule checklist, terminology verbatim, scope discipline, testability |

Load order — each of these costs 2.5–3.3k tokens of context that is then re-served on
every subsequent call, so load one when it has work to do, not before:

- `requirement-evidence-and-gating` — **always**, first, before refining anything.
- `screenshot-requirement-analysis` — **only when images were supplied**, as file paths
  or as a caller-prepared inventory. No images, no load: it has nothing to read.
- `business-requirement-writing-style` — **at drafting time (§8)**, not at intake.
  Nothing before §8 writes ticket prose.

What stays here: triage against Jira and the code (§2), the ticket's audience and house
language (§5, §7), the template (§8), the Jira create path (§9, `JIRA.md`), and the
report (§11).

The gate verdict is the evidence skill's to give. `BLOCKED` means **create nothing** and
report per §11 — not "create it with the gaps noted".

## 1. The Jira server: this project's, never the global one

The only Jira surface this skill may use is the MCP server declared in this workspace's
[`.mcp.json`](../../../.mcp.json) — server name `jira`, tools named `mcp__jira__*`.
That server is started with `--jira-projects-filter`, so it is already scoped to this
workspace's project.

Forbidden, even when connected and even when it looks equivalent:

- any other Atlassian/Jira MCP server from the **user-level** config (`~/.claude.json`)
  or from a plugin — e.g. `mcp__MCP_DOCKER__*`, `mcp__atlassian__*`, an
  `atlassian` plugin skill;
- `curl`, `uvx`, `acli`, or any REST call to the Jira API — credentials belong to the
  configured server, not to a shell command;
- falling back to a local markdown file because a Jira call failed.

**Resolve the project key from configuration, never from memory.** Read
`--jira-projects-filter` in `.mcp.json` (currently `FKC`) and confirm it resolves with
`mcp__jira__jira_search_projects` or `mcp__jira__jira_get_all_projects`. If the filter
names more than one project, ask which one with `AskUserQuestion` — do not guess.

If no `mcp__jira__*` tool is available, **stop and say the project Jira MCP server is not
connected**. That is the whole report. Do not substitute another server and do not write a
file instead.

Mechanics — exact call order, parameter rules, failure modes: [`JIRA.md`](JIRA.md).

## 2. Triage first — existence, then tier

Read [`TRIAGE.md`](TRIAGE.md) and settle three things, **in its §0 order** — Jira search
and the text-only gap screen come before any code reading, because the code reading is
where the cost is and a request that dies early should die before paying it:

1. **Does Jira already have this?** Search the project with
   `mcp__jira__jira_search` before anything else. An open issue covering the same outcome
   ends the workflow — report the key and let the requester extend that issue instead.
   Duplicate tickets are the one mistake this skill can make that other people have to
   clean up.
2. **Does the code already do this?** `NOT_PRESENT` · `PARTIALLY_IMPLEMENTED` ·
   `ALREADY_IMPLEMENTED` · `IMPLEMENTED_DIFFERENTLY` · `ELSEWHERE_ONLY`. An
   `ALREADY_IMPLEMENTED` verdict **ends the workflow** — report the evidence and let the
   requester close or reframe it.
3. **Which tier?** `T1` / `T2` / `T3`, from `TRIAGE.md`'s trigger table. The tier decides
   how much of `Description` is required and which label the issue carries.

Between 1 and 2 sits the gap screen (`TRIAGE.md` §0): a material gap that **no code
reading can answer** goes back to the requester now, before the investigation, not after
it.

## 3. Evidence — the evidence skill's rules, plus one Jira rule

`requirement-evidence-and-gating` runs first and runs the whole way: it tags every claim,
gives every part of the PO's request a disposition, cross-checks the draft against the
verbatim request, and holds the gate. Take its ledger as the input to §8 — the `USED`
rows are the ticket's content, the `SCOPE-OUT` rows are `Not included in this ticket`.

The one thing it cannot know: **Jira field values are evidence-bound too.** An issue type,
label, component, version, parent module, priority or assignee is only set when the
requester stated it or the project's own metadata provides it (§9, `JIRA.md` §3). A field
value you inferred is an `INFERENCE` with a Jira field name on it, and it does not go in.

`CODEBASE` claims here mean code read **at the branch for the affected environment**
(`TRIAGE.md` §2) — not whatever branch is checked out.

## 4. Screenshots — one Jira limitation

`screenshot-requirement-analysis` owns reading the images and returns the inventory; its
rows arrive tagged `VISUAL`. Nothing about that changes here.

What is Jira-specific: **the MCP server cannot upload attachments** — it only downloads
them (`JIRA.md` §5). So the files stay with the requester. Two consequences:

- `Images` in the ticket carries one line per supplied screenshot saying what it
  establishes, written from the inventory (§8, `TEMPLATE.md`);
- the report tells the requester to attach the files to the created issue (§11). Never
  imply they were attached.

## 5. The ticket's language — the style skill's rules

`business-requirement-writing-style` owns every wording decision in the ticket: the five
slots a requirement sentence carries, refine-don't-transcribe (and don't over-refine), the
vague-phrase table, keeping the prose non-technical without going vague, the business-rule
checklist, terminology verbatim, scope discipline and testability. Do not restate or soften
its rules here.

Four things it defers to this skill, because they are this workspace's:

- **Audience.** The ticket is read by this workspace's developers and by QA testing by
  hand — there is effectively no automated test coverage here. `Expected result` therefore
  has to be pass/fail-able from the ticket alone, with no conversation attached.
- **Whose labels.** Product labels come from the three repos' own UI (`fk-admin-panel-fe`,
  `fk-mobile`, and what the backend exposes). Where web and mobile label the same thing
  differently, say which one the ticket means.
- **House language.** British English, per §7 — the style skill leaves the variant to the
  caller, and its two carve-outs still hold: product labels and technical identifiers.
- **Where the prose goes.** The `Description` sub-headings and their order are §8.

## 6. The gate, in Jira terms

The gate is `requirement-evidence-and-gating`'s: materiality, batched questions with
concrete options, three rounds, no placeholders in the finished text. Do not re-run a
second version of it here.

Only the consequences are local:

- **`BLOCKED` means no issue is created.** No draft issue, no issue with open questions in
  the description, no "raising it to track the discussion". Report per §11.
- A created issue **never** contains "To be confirmed with the Product Owner", "TBC",
  "TBD", "to be decided", "development to decide" or an `UNKNOWN` standing in for a PO
  decision. Once created, that text is in a shared backlog and someone will build from it.
- A `SCOPE-OUT` row becomes the `Not included in this ticket` line — stated once, with no
  invitation to confirm it later.

## 7. British English — mandatory

All generated prose uses British spelling and terminology (organisation, behaviour,
authorised, customise, recognise, licence (noun), whilst, postcode, mobile number,
surname, annual leave, tick box). Two exceptions: **product/UI labels stay verbatim** (if
the UI says `Organization Type`, write `Organization Type`), and **technical identifiers
are never renamed**.

## 8. The ticket itself

**Summary** — one line, the change in the product's own words, no trailing full stop, no
issue key, no "As a user". Match the conventions actually used in the project: read the
recent issues you already pulled in triage and follow their shape (§2, `JIRA.md` §2).
When the backlog is too thin to show a convention, follow the rule above rather than
copying a single existing issue (`JIRA.md` §2a).

**Description** — Markdown, built from [`TEMPLATE.md`](TEMPLATE.md) in this directory,
exactly: same sections, same order, same wording of the fixed lines. **No section may be
added** — an extra section is how open questions get smuggled into a ticket that should
not have been created.

`Description` sub-headings, where applicable, in this order:

- **Problem** — what is wrong or missing today, from the user's point of view, in one or
  two sentences. Not the solution. Required.
- **Context** — product area, page, user type, environment when relevant.
- **Current behaviour** — only if needed to understand the change.
- **Requested behaviour** — what should change.
- **Success measure** — how anyone would know this worked, in business terms. Required
  for T2 and T3; optional for T1, where the expected result is the whole story.
- **Business rules** — required information and conditions, including edge cases.
- **Not included in this ticket** — the boundary. Required, even when it feels obvious.
- **Expected result** — testable outcomes QA can pass or fail. Required.

Direct prose. No narrative padding.

Fixed-section rules:

- `Images` — one line per supplied screenshot saying what it establishes; when none were
  supplied, keep `*Insert images here.` verbatim (§4).
- `Affected System(s)` — tick only what is reasonably affected. Do not tick DB merely
  because the build will probably touch it. Uncertain → leave unticked.
- `SEVERITY:` — the PO's value if given; otherwise Low (minor/limited impact), Medium
  (meaningful workflow impact), High (blocks an important workflow or causes major
  business impact). Cannot be reasonably determined → leave blank.
- `TIME ESTIMATE:` — blank unless the requester states an **appetite**: how much time this
  is worth to them. An appetite is a budget the scope must fit, never a prediction, and it
  is theirs to set, never yours to infer.
- `MERGED TO STAGE:` / `MERGED BACK TO DEVELOP:` — always left unticked. Writing a ticket
  is not implementing or deploying it.
- `Resolution` — always `To be updated*`.

## 9. Confirm, then create in Jira

### Gate B — the requester confirms the written ticket

Creating a Jira issue is outward-facing: other people see it, and deleting one is not a
clean undo. So answers to your questions are not enough — before the create call, show
the assembled summary and `Description` (Problem, Requested behaviour, Business rules,
Not included, Expected result) and ask one `AskUserQuestion`:

> Raise this in Jira as written? (Yes, create it / No, and here is what is wrong)

Corrections come back as `EXPLICIT` evidence: fold them in and ask again. Nothing is
created until this is answered.

### Create

Follow [`JIRA.md`](JIRA.md) — discover the issue types and create-fields for the resolved
project, then one `mcp__jira__jira_create_issue` call. Rules that matter most:

- **Every Jira field value is discovered, never invented.** Issue type from
  `jira_get_project_issue_types`; required and optional fields from
  `jira_get_create_fields`; allowed values from `jira_get_field_options`. A label,
  component, version, epic or priority that the project does not have is not set.
- **Only what the requester gave.** No assignee, no sprint, no epic link, no priority
  unless they said so. An unassigned ticket in the backlog is the correct default.
- **One issue per request.** Do not split a request into several issues, and do not
  create a sub-task hierarchy, unless the requester asked for it.
- **After creating, read it back** with `mcp__jira__jira_get_issue` and check the
  description rendered with its sections intact.
- **Never retry a create blindly.** If the call errors ambiguously, search the project by
  summary first — the issue may exist (`JIRA.md` §5).

Do not transition, assign, comment on, or add watchers to the new issue. The issue's Jira
status is the state record; this skill leaves it in the project's default.

## 10. Validation — all must pass before the create call

Delegated, not repeated — confirm each came back clean rather than re-deriving it:

- **Gate**: `requirement-evidence-and-gating` returned `PASSED`, its coverage check ran
  (nothing dropped, nothing added, both directions cross-checked, values copied exactly),
  and its placeholder search found nothing in the drafted text.
- **Images**: when images were supplied, `screenshot-requirement-analysis` was loaded,
  reported on every one of them, and the relationship it concluded between them is the
  one the ticket is written to. No images supplied — this check does not apply and the
  skill should not have been loaded.

Ticket- and Jira-specific, and nobody else checks these:

- **No duplicate**: the project was searched with more than one phrasing, and no existing
  issue covers this outcome (`TRIAGE.md` §1).
- **Environment**: the affected environment is identified where it matters, and current
  behaviour was read from the code at *that* branch (`TRIAGE.md` §2). Environment-only
  functionality is not described as existing everywhere.
- **Clarity**: development knows what to build; QA can decide pass/fail from
  `Expected result` alone.
- **Language level**: implementation detail removed, business rules still explicit (§5).
- **British English**: prose checked; product labels and technical identifiers untouched
  (§7).
- **Template**: all sections present in `TEMPLATE.md` order, fixed lines verbatim, merge
  fields untouched, `Resolution` still `To be updated*`.
- **Problem and boundary**: `Problem` present; `Not included in this ticket` present;
  `Success measure` present for T2 and T3 (§8, `TRIAGE.md` §3).
- **Jira fields**: project key resolved from `.mcp.json`; the issue type exists in that
  project; every field set exists and every value is one the project allows.
- **Confirmed**: gate B answered by the requester (§9).

## 11. Report

After creating, report only:

```
Ticket raised in Jira.

Issue:   <KEY> — <summary>
Link:    <the browse_url Jira returned>
Type:    <issue type> · tier <T1|T2|T3> · severity <value or "not set">

Summary: <one-line summary of the requirement>
```

Add one line when screenshots were supplied: `Attach the <n> screenshot(s) to <KEY> —
the MCP server cannot upload them.`

Do not reproduce the ticket body unless asked, and never state a link you did not get
back from Jira — `jira_search` and `jira_get_issue` return `browse_url` for exactly this.

When the gate stopped the ticket, **nothing is created** and the report is the evidence
skill's own shape (its §9) with the deliverable filled in as the ticket:

```
No ticket raised — requirement not sufficiently defined.

Open questions:
- <question>  (why it changes what gets built)

Already established:
- <what the investigation did settle>

Answer these and the ticket can be raised.
```

Reporting open questions is a **successful outcome**, not a failure. Do not apologise for
it, and do not offer to raise the ticket anyway with the gaps noted.

When §2 ended it — the capability already exists, or Jira already has the issue —
nothing is created and the report is:

```
No ticket raised — this already exists.

Evidence:
- <existing issue key, or file:line / branch ref proving the outcome already holds>

State: ALREADY_IMPLEMENTED | DUPLICATE_OF <KEY>   (or PARTIALLY_IMPLEMENTED, with what remains)

Options: close it, or reframe it as <the specific change that would still be needed>.
```

Which option to take is the requester's call, never yours.
