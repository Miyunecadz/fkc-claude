---
description: Turn a rough Product Owner request (text and/or screenshots) into a refined, non-technical ticket raised in this workspace's Jira project (FKC)
argument-hint: <Product Owner request> [screenshot paths]
allowed-tools: Task, Read, AskUserQuestion
effort: low   # orchestration only: prepare the input, delegate, relay the report
---

Create a development ticket from this Product Owner request:

$ARGUMENTS

Delegate to the `ticket-creator` agent. Do not analyse, refine, triage or write the ticket
yourself, do not call Jira yourself, and do not implement the request.

## Before delegating

**Screenshots.**

- Screenshot **file paths** in the request or the conversation — pass them through verbatim.
- Images **pasted inline** into this conversation — the agent cannot see them. Read each
  one yourself and pass a factual visual inventory alongside the request, following the
  `screenshot-requirement-analysis` skill: page/screen title, section, tab, visible field
  labels and values, required markers, controls, table columns in order, filters, sorts,
  states, dates and formats, annotations. Record only what is genuinely readable; mark
  anything cropped, blurry or cut off as **unreadable** rather than guessing. No
  interpretation, no invented fields. Say how many images there were and whether they look
  like one requirement seen from several angles or separate asks.
- Request mentions screenshots but none are present — ask the user for them before
  delegating.

**Pass through, verbatim, anything the user stated about:** the affected environment
(Staging / Production), the product area or page, the repo(s), severity, a time
**appetite**, and any Jira parent module, label or priority they named. Do not add values
they did not state — the agent treats an inferred field value as an inference and drops it.

## After the agent returns

Relay the agent's report as-is. Do not reproduce the ticket body unless the user asks, and
never state a Jira link the agent did not report.

The agent refines the requirement with the requester before raising anything, so four
outcomes are all normal:

- **Ticket raised** — relay the issue key and link. If screenshots were supplied, keep the
  agent's line telling the user to attach them: the MCP server cannot upload files.
- **Not raised — requirement not sufficiently defined.** Relay the open questions
  verbatim and stop. Do not answer them on the requester's behalf, do not resolve them
  from the codebase yourself, and do not ask the agent to raise the ticket anyway with the
  gaps noted. Once the user answers, re-run the agent with the original request plus the
  answers.
- **Not raised — this already exists** (already implemented, or a duplicate Jira issue).
  Relay the evidence and the options. Which option to take is the user's call, never yours.
- **Jira not reachable** — the `jira` MCP server is not connected. Relay that and stop;
  do not fall back to another Jira server and do not offer to save a local file instead.

The agent asks the user directly before creating the issue. If it reports that it could not
reach the user, put its questions or its draft to the user yourself with `AskUserQuestion`,
then re-run the agent with the answers.

## Boundaries

The Jira issue is the ticket. Never write `tickets/*.md` or any local copy, even if asked
to "save it too" — offer the key, the link, or the body pasted in chat instead. Never
implement the change, and never transition, assign or comment on the created issue.
