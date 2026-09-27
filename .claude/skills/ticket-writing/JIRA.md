# Jira mechanics — the project server only

This file owns the call order, the JQL and the create mechanics. Every call uses the
`jira` MCP server (`mcp__jira__*`) and nothing else (SKILL.md §1).

## 1. Resolve the target project — from config, not memory

1. Read `.mcp.json` at the workspace root and take the value after `--jira-projects-filter`
   (today `FKC`). The file is the source of truth; it can change without this skill.
2. Confirm it resolves: `mcp__jira__jira_search_projects { query: "<key>" }`, or
   `mcp__jira__jira_get_all_projects` when that returns nothing useful.
3. Several comma-separated keys → ask the requester which one, offering the keys.
4. Empty or missing filter → the server is not project-scoped. Ask for the key; never
   default to the first project that appears.

`project_key` must match `^[A-Z][A-Z0-9_]+$`.

## 2. Duplicate search

```
mcp__jira__jira_search { jql: "project = <KEY> AND statusCategory != Done AND text ~ \"<key phrase>\" ORDER BY updated DESC", limit: 20 }
```

- Two or three phrasings (`TRIAGE.md` §1). Add a `statusCategory = Done` sweep when the
  request sounds like a regression.
- Escape double quotes inside `jql`. If `text ~` errors, use `summary ~ "<phrase>"`.
- Summary shape: when the results show a clear, repeated summary convention, match it.
  Otherwise follow SKILL.md §7. Never copy a convention, or a label, from one sample.
  There is no separate house-style search.

## 3. Project facts — still discover at runtime

- `FKC` is a team-managed Jira Cloud project. `Module` is its epic-level container: link
  with `{"parent": "FKC-<n>"}`, not `epicKey`, and only when the requester named the module.
- `jira_search` and `jira_get_issue` return `browse_url` per issue. That is the link to
  report; never build one by hand.

## 4. Discover the fields, then create — one call

```
mcp__jira__jira_get_project_issue_types { project_key: "<KEY>" }
mcp__jira__jira_get_create_fields       { project_key: "<KEY>", issue_type_id: "<id>" }
mcp__jira__jira_get_field_options       { ... }   # only when a field needs its allowed values
```

- **Type** from what the project offers: `Bug` when today's behaviour is wrong; the
  story/task type for new or changed behaviour; never an epic unless asked.
- **Every value is discovered, never invented.** A label, component, version, parent or
  priority the project does not have is not set.
- **Only what the requester gave.** No assignee, sprint, parent, label or priority unless
  they said so. Priority only from a severity the PO stated, only if `priority` is in the
  create-fields, only with a name from its options.
- A **required** field you cannot fill from evidence is a question for the requester, not
  a guess. An **optional** field nobody mentioned stays unset.
- **One issue per request.** No split, no sub-tasks, unless the requester asked.

```
mcp__jira__jira_create_issue {
  project_key: "<KEY>",
  summary:     "<one line, SKILL.md §7>",
  issue_type:  "<discovered type name>",
  description: "<TEMPLATE.md, filled, Markdown>",
  additional_fields: "<JSON string — only what the requester gave>"
}
```

- `description` is Markdown; the server converts it. `##` headings and `- [ ]` boxes
  survive. No HTML.
- `additional_fields` is a **JSON string**, not an object: `{"priority": {"name": "High"}}`,
  `{"labels": ["..."]}`, `{"parent": "FKC-123"}`.

Then read it back and check the sections rendered intact and the fields hold what you sent:

```
mcp__jira__jira_get_issue { issue_key: "<KEY>-<n>", fields: "summary,issuetype,description,priority,labels,status" }
```

## 5. Failure modes

| Symptom | Do this |
|---|---|
| No `mcp__jira__*` tool at all | Stop — SKILL.md §1 |
| Auth / 401 / 403 | Stop and report it. Credentials live in the server's env file — do not read it or work round it |
| Create errored, unclear whether it landed | Search first: `project = <KEY> AND summary ~ "<summary>" ORDER BY created DESC`. Create again only if nothing came back |
| Field rejected, or value not allowed | Re-read `jira_get_create_fields` / `jira_get_field_options` and drop the field rather than force it |
| Screenshots to attach | Cannot be done — the server only downloads attachments. Say so in the report |
| Requester asks for a local copy | Offer the key and link, or paste the body in chat — SKILL.md §1 |

## 6. Out of scope

Transitioning, assigning, commenting, watchers, estimating, sprints, hierarchy edits,
deleting, and any other project. Raising the issue is where this stops.
