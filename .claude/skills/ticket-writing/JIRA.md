# Jira mechanics — the project server only

Everything here uses the `jira` MCP server declared in this workspace's `.mcp.json`, whose
tools are named `mcp__jira__*`. No other Jira surface is permitted (SKILL.md §1).

## 1. Resolve the target project — from config, not memory

1. Read `.mcp.json` at the workspace root and take the value after
   `--jira-projects-filter`. Today that is `FKC`; treat the file as the source of truth,
   because it can change without this skill changing.
2. Confirm it exists and you can see it:

   ```
   mcp__jira__jira_search_projects  { query: "<key>" }
   ```

   or `mcp__jira__jira_get_all_projects` when the search returns nothing useful.
3. Comma-separated filter with several keys → ask the requester which one with
   `AskUserQuestion`, offering the keys as options.
4. Empty or missing filter → the server is not project-scoped. Ask for the key rather
   than defaulting to whatever project appears first.

`project_key` must match `^[A-Z][A-Z0-9_]+$`. Never pass a project the requester did not
name or the filter did not resolve.

## 2. Read the project before writing to it

Two searches, both cheap, both required (SKILL.md §2):

```
# duplicate check — the outcome, in the requester's own nouns
mcp__jira__jira_search { jql: "project = <KEY> AND statusCategory != Done AND text ~ \"<key phrase>\" ORDER BY updated DESC", limit: 20 }

# house style — what recent issues in this project actually look like
mcp__jira__jira_search { jql: "project = <KEY> ORDER BY created DESC", limit: 10, fields: "summary,issuetype,labels,priority,status" }
```

From the second, take the summary shape, the issue types in real use, and the labels that
already exist. Match them. Do not invent a new convention for one ticket, and do not treat
a label you saw once as required.

Escape double quotes inside `jql`. If a `text ~` search errors on this instance, fall back
to `summary ~ "<phrase>"`.

## 2a. This project, as verified on 2026-09-10

A snapshot to save you a wrong guess — **still discover at runtime**, because a
team-managed project changes without notice:

- `FKC` → **fk-connect**, Jira **Cloud**, `software`, **team-managed** (next-gen),
  instance `zero-hero-tech.atlassian.net`.
- Issue types: `Story`, `Bug`, `Task`, `Module`, `Subtask`. `Module` is this project's
  epic-level container — link to one with `{"parent": "FKC-<n>"}`, not `epicKey`, and only
  when the requester named the module.
- No required custom field beyond `project`, `summary`, `issuetype` and `reporter`
  (`reporter` is set from the server's own credentials). `priority`, `labels`, `parent`,
  `duedate`, `assignee` all exist and are optional.
- The backlog is nearly empty, so **there is no house style to copy yet.** With fewer than
  a handful of real issues, follow SKILL.md §8 and `TEMPLATE.md` and do not generalise a
  convention — or a label — from one sample ticket.
- `jira_search` and `jira_get_issue` return `browse_url` per issue. That is the link to
  report (SKILL.md §11); never build one by hand.

## 3. Discover the fields for the type you are about to create

```
mcp__jira__jira_get_project_issue_types { project_key: "<KEY>" }
mcp__jira__jira_get_create_fields       { project_key: "<KEY>", issue_type_id: "<id from above>" }
mcp__jira__jira_get_field_options       { ... }   # only when a field needs its allowed values
```

- Pick the type from what the project actually offers. `Bug` when today's behaviour is
  wrong or broken; the project's story/task type when it is new or changed behaviour;
  never `Epic` unless the requester asked for an epic.
- A **required** field you cannot fill from `EXPLICIT`/`VISUAL`/`CODEBASE` evidence is a
  gate-§6 question for the requester, not a guess and not a placeholder.
- An **optional** field the requester said nothing about stays unset.

## 4. Create — one call

```
mcp__jira__jira_create_issue {
  project_key: "<KEY>",
  summary:     "<one line, SKILL.md §8>",
  issue_type:  "<discovered type name>",
  description: "<TEMPLATE.md, filled, Markdown>",
  additional_fields: "<JSON string — only what the requester gave>"
}
```

- `description` is Markdown and the server converts it. Keep the template's `##` headings
  and `- [ ]` tick boxes; they survive. Avoid HTML.
- `additional_fields` is a **JSON string**, not an object. Use it only for values the
  requester stated: `{"priority": {"name": "High"}}`, `{"labels": ["..."]}`,
  `{"parent": "<KEY>-123"}` for a parent the requester named.
- `assignee` stays unset unless the requester named someone. `components` only when they
  exist in the project and the requester's wording maps to one.
- Priority is set only from a severity the PO stated, only if the project's create-fields
  include `priority`, and only using a name from that field's options. The `SEVERITY:`
  line in the description is the record either way.

Then read it back:

```
mcp__jira__jira_get_issue { issue_key: "<KEY>-<n>", fields: "summary,issuetype,description,priority,labels,status" }
```

Check the description rendered with its sections intact and the fields hold what you sent.
Report the key and the URL Jira returned — never construct a link from a base URL you
assumed.

## 5. Failure modes

| Symptom | Do this |
|---|---|
| No `mcp__jira__*` tool at all | Stop. Report that the project Jira MCP server is not connected. No other server, no local file (SKILL.md §1) |
| Auth / 401 / 403 | Stop and report it. The credentials live in the server's env file — do not read it, do not work around it |
| Create errored, unclear whether it landed | Search first: `project = <KEY> AND summary ~ "<summary>" ORDER BY created DESC`. Only create again if nothing came back |
| Field rejected as unknown or value not allowed | Re-read `jira_get_create_fields` / `jira_get_field_options` and drop the field rather than forcing it |
| Screenshots to attach | Cannot be done here — the server only downloads attachments. Say so in the report and leave it to the requester |
| Requester asks for a local copy anyway | The Jira issue is the ticket. Offer the key and link, or paste the body in chat — do not write a file |

## 6. Out of scope for this skill

Transitioning, assigning, commenting, estimating, sprint assignment, epic hierarchy
edits, deleting an issue, and anything in another project. Raising the ticket is where
this stops.
