# Extending an existing issue

Use this file instead of SKILL.md §7–§10 when the change belongs on an issue that already
exists. The thinking is the same — evidence, gate A, the template's rules for each
section, `plain-uk-english`. What changes is that someone else's issue is being edited,
and other people may already be building from it.

## 1. When this applies

Only one of these:

- The requester named an issue and asked to add to it, amend it or extend it.
- Triage reported `DUPLICATE_OF <KEY>` or a partial overlap, and the requester chose
  "extend `<KEY>`" from the "already exists" options (SKILL.md §10).

Never choose to extend on your own. An overlap is reported; the requester decides.

## 2. Read the issue first — it decides whether you may edit

```
mcp__jira__jira_get_issue { issue_key: "<KEY>-<n>", fields: "summary,issuetype,status,description,attachment,parent", comment_limit: 10 }
```

| Status category | What happens |
|---|---|
| To Do | Continue |
| In Progress | Tell the requester someone may be building from it now, and ask whether to edit it or raise a new issue linked in the text. Continue only on "edit it" |
| Done | Do not edit. A finished issue is a record of what was delivered. Offer a new issue that names it (`Out of scope` or `Decisions`), and go back to SKILL.md §7 |

Read the comments too: a decision agreed in a comment is `EXPLICIT` evidence, and a
change that contradicts it is a question for the requester.

## 3. Draft the change — add, do not rewrite

The existing description stays. Other people wrote it, and people may be building from it.

- **Keep its shape.** If it follows `TEMPLATE.md`, add under its headings. If it has its
  own shape (FKC-23 uses `Problem`, `Business rules`, `Expected result`), add under the
  heading that fits. Never convert a whole issue to the template.
- **Add** new criteria numbered after the last one, new decisions and out-of-scope lines at
  the end of their section, new screenshots at the end of `Images`.
- **Change an existing line** only when the requester's change replaces it, and say so on
  the line: `(revised <YYYY-MM-DD> by PO: was "<old wording>")`. The old wording stays
  readable so a builder part-way through can see what moved.
- **Never delete** a line to make room. Something no longer wanted moves to `Out of scope`
  with its revised note.
- **Summary** changes only when the requester asked, or the change makes the old summary
  wrong. Same rules as SKILL.md §7.
- The same gate applies: no placeholder, no open material gap, no design outside the two
  technical sections.
- Fixed sections (`Affected System(s)`, `Other Info`, `Resolution`): tick a new system only
  on evidence. Do not change `SEVERITY`, `TIME ESTIMATE` or the MERGED boxes unless the
  requester stated a new value.

## 4. Gate B — confirm the change, not the whole issue

Show only what changes, as added and changed lines under their section headings, plus any
summary change and the files to attach. Ask once:

> Update <KEY> as shown? (Yes, update it / No, and here is what is wrong)

Corrections are `EXPLICIT`: fold them in and ask again. Nothing is sent until yes. No
question tool → hand the change and this question to the caller.

## 5. Send it

```
mcp__jira__jira_update_issue {
  issue_key:     "<KEY>-<n>",
  fields:        "{\"description\": \"<the whole description: existing text plus the change>\"}",
  attachments:   "<absolute file paths, when screenshots have files — JIRA.md §5>",
  return_fields: "summary,status,attachment"
}
```

- `description` replaces the whole field, so send the full text: what you read in §2 with
  your change folded in. Sending only the new lines wipes the rest.
- Just before sending, read the description again. If it no longer matches the §2 read,
  someone edited it while you waited at gate B: fold your change into the new text and
  confirm again.
- Images already embedded in the description are kept by the server.
- `fields` holds `summary` too when the summary changes. Nothing else: no status,
  assignee, priority or labels unless the requester gave them, and then only values
  `jira_get_create_fields` allows.

Read back with `jira_get_issue` (`fields: "summary,description,attachment"`) and check
the old content is still there and your change landed.

## 6. Report

```
Ticket updated in Jira.

Issue:   <KEY> — <summary>
Link:    <the browse_url Jira returned>
Changed: <n> added line(s), <n> revised line(s)<, summary changed>

Summary: <one line: what the change adds or revises>
```

Add the attachment line from SKILL.md §10 when screenshots were supplied. Do not transition,
assign, comment on or watch the issue.
