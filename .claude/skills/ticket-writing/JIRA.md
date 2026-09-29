# Jira mechanics — the project server only

This file owns the call order, the JQL, how text survives the trip into Jira, and the
create, attach and update mechanics. Every call uses the `jira` MCP server
(`mcp__jira__*`) and nothing else (SKILL.md §1).

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

## 3. Writing text that survives Jira

`FKC` is on Jira Cloud. The server turns the Markdown `description` into Jira's own
document format (ADF). Checked against the server's converter:

| You write | Jira shows |
|---|---|
| `##` headings, `**bold**`, numbered and bullet lists, tables, inline code | the same, intact |
| `[text](https://…)` | a link |
| a bare `FKC-21` | a link to FKC-21 on this site — fine for this project's keys |
| a list made **only** of `- [ ]` / `- [x]` lines | real Jira checkboxes, `[x]` ticked — as in `Affected System(s)` |
| a `- [ ]` line inside an ordinary bullet list | plain text starting `[ ]` — keep checkbox lists separate |
| `[ ]` inside a sentence (`MERGED TO STAGE: [ ]`) | literal text — expected, leave it |
| HTML, `<!-- comments -->` | stripped or mangled — never use |

- **Keys from another Jira site get an explicit link.** A bare `SUBC-18` in an FKC issue
  links to this site, where it does not exist. Write
  `[SUBC-18](https://247crm.atlassian.net/browse/SUBC-18)`, in headings too.
- **Comments are not descriptions.** Bracket and `#` damage seen in comments came from the
  comment path; this skill does not comment.
- The read-back (§4) shows the stored text converted back to Markdown. Judge it by content
  — sections present, lines intact — not by exact characters.

## 4. Discover the fields, then create — one call

Project facts — still check at runtime:

- `FKC` is a team-managed Jira Cloud project. `Module` is its epic-level container: link
  with `{"parent": "FKC-<n>"}`, not `epicKey`, and only when the requester named the module.
- `jira_search` and `jira_get_issue` return `browse_url` per issue. That is the link to
  report; never build one by hand.

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
  summary:     "<one line, 255 characters at most, SKILL.md §7>",
  issue_type:  "<discovered type name>",
  description: "<TEMPLATE.md, filled, Markdown per §3>",
  components:  "<comma-separated names — only when the requester named them and they exist>",
  additional_fields: "<JSON string — only what the requester gave>"
}
```

- `additional_fields` is a **JSON string**, not an object: `{"priority": {"name": "High"}}`,
  `{"labels": ["..."]}`, `{"parent": "FKC-123"}`.

Then attach (§5), and read it back once, after both:

```
mcp__jira__jira_get_issue { issue_key: "<KEY>-<n>", fields: "summary,issuetype,description,priority,labels,status,attachment", comment_limit: 0 }
```

Check the sections rendered intact, the fields hold what you sent, and every file you
uploaded appears in `attachment`.

## 5. Attach the screenshots

Only for screenshots that arrived as file paths (SKILL.md §4). One call, all files:

```
mcp__jira__jira_update_issue {
  issue_key:     "<KEY>-<n>",
  fields:        "{}",
  attachments:   "[\"/abs/path/one.png\", \"/abs/path/two.png\"]",
  return_fields: "attachment"
}
```

- **Absolute paths.** The server runs in its own process; a relative path may not resolve.
  Check each file exists before the call.
- `fields` is required; `"{}"` changes nothing else. Never send a field here — this call
  attaches, it does not edit.
- Result has `attachment_results`. A file that failed is named in the report as one to
  attach by hand, with the reason. Do not retry more than once.
- This is the only use of `jira_update_issue` on a new issue. Editing an existing issue's
  description is `UPDATE.md`.

## 6. Failure modes

| Symptom | Do this |
|---|---|
| No `mcp__jira__*` tool at all | Stop — SKILL.md §1 |
| Auth / 401 / 403 | Stop and report it. Credentials live in the server's env file — do not read it or work round it |
| Create errored, unclear whether it landed | Search first: `project = <KEY> AND summary ~ "<summary>" ORDER BY created DESC`. Create again only if nothing came back |
| Field rejected, or value not allowed | Re-read `jira_get_create_fields` / `jira_get_field_options` and drop the field rather than force it |
| Summary rejected as too long | Shorten it — detail belongs in the description |
| Attachment upload failed | The issue stands. Report the file as one to attach by hand, with the error line |
| Screenshot with no file (pasted inline) | Cannot be uploaded. Report it as one to attach by hand |
| Requester asks for a local copy | Offer the key and link, or paste the body in chat — SKILL.md §1 |

## 7. Out of scope

Transitioning, assigning, commenting, watchers, issue links, estimating, sprints,
hierarchy edits, deleting, and any other project. Raising the issue, attaching its
screenshots, and extending an existing issue (`UPDATE.md`) are where this stops.
