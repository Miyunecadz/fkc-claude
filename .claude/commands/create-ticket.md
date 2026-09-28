---
description: Turn a rough Product Owner request (text and/or screenshots) into a refined build-brief ticket raised in this workspace's Jira project (FKC)
argument-hint: <Product Owner request> [screenshot paths]
allowed-tools: Agent, Task, SendMessage, Read, AskUserQuestion
effort: low   # orchestration only: prepare the input, delegate, relay the report
---

Create a development ticket from this Product Owner request:

$ARGUMENTS

Delegate to the `ticket-creator` agent (the `Agent` tool; `Task` on older builds). Do not
analyse, refine, triage or write the ticket yourself, do not call Jira, and do not
implement the request.

## Before delegating

**Screenshots.**

- **File paths** in the request or conversation — pass them through verbatim, as absolute
  paths. The agent attaches these files to the issue.
- Images **pasted inline** — the agent cannot see them, and there is no file to attach. Read each one and pass a factual
  inventory with the request: page and title, section, tab, field labels and values,
  required markers, controls, table columns in order, filters, sorts, states, dates and
  formats, annotations. Only what is readable; anything cropped or blurry is
  **unreadable**, not guessed. No interpretation. Say how many images there were and
  whether they look like one requirement or separate asks.
- The request mentions screenshots but none are present — ask the user for them first.

**Pass through verbatim** anything the user stated about: environment (Staging /
Production), product area or page, repo(s), severity, a time **appetite**, and any Jira
parent module, label or priority. Add nothing they did not state.

## While the agent runs — asking and resuming

The agent may not have `AskUserQuestion`. Then it returns **Needs input — nothing raised
yet**, with numbered questions (and, at gate B, the draft).

1. Put the questions to the user with `AskUserQuestion` — at most four per call, the
   agent's options as given. At gate B, show the draft and ask *Raise this in Jira as
   written?*
2. Never answer on the user's behalf, and never settle a question from the code yourself.
3. Resume **the same agent** with `SendMessage` (its agent ID), sending the answers
   numbered as asked. Do not start a fresh run — it would repeat the whole inspection.
4. Only if `SendMessage` is unavailable: start a new run with the original request, every
   answer so far and, at gate B, the confirmed draft.

## After the agent returns

Relay its report as-is. Do not reproduce the ticket body unless asked, and never state a
Jira link the agent did not report.

- **Ticket raised** or **Ticket updated** — relay the key and link, and the attachment
  line as the agent gave it (which files were attached, which to attach by hand).
- **Not raised — requirement not sufficiently defined** — relay the open questions
  verbatim and stop. Do not ask the agent to raise it anyway. When the user answers,
  resume the same agent with `SendMessage` as above.
- **Not raised — this already exists** — relay the evidence and options. The choice is the
  user's. If they choose to extend the existing issue, resume the same agent with that
  choice.
- **Jira not reachable** — relay it and stop. No other Jira server, no local file.

The Jira issue is the ticket: never write a local copy, even if asked (`ticket-writing`
§1). Never transition, assign or comment on the created issue.
