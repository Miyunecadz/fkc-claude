# Bitbucket Cloud — the mechanism

Verified 2026-09-10 from `git remote -v` in all three repos.

| Fact | Value |
|---|---|
| Hosting | **Bitbucket Cloud** |
| Remote | `origin` → `git@bitbucket.org-247tech:lisafk/<repo>.git` (SSH host alias) |
| Workspace / slug | `lisafk/fk-admin-panel-be`, `lisafk/fk-admin-panel-fe`, `lisafk/fk-mobile` |
| Merge strategy in use | merge commit — merges read `Merged in <branch> (pull request #N)` |
| Repo-level default reviewers | **none configured** — a PR created through the API gets none unless you pass them |

`pr-preflight.sh` re-derives the platform and the slug from the remote on every run and
stops if it is not Bitbucket. Trust the script over this table if they ever disagree.

## Tools

`ToolSearch` for `bitbucket`, then `mcp__bitbucket__bb_get` / `bb_post` / `bb_put`. There is
no hosting CLI for this platform on this machine — `gh` is installed, it is GitHub, and it
is useless here.

**If the Bitbucket tools are unavailable in the session, do not invent another route.**
Print the title, description, source and destination for the user to paste into the
browser, and say plainly that the PR was not created.

The `/2.0` prefix is added for you. Always pass `jq` — an unfiltered response is enormous.

### The call budget: 2 before the post, 2 after — 5 calls including the post

Every one of these is a serial network round trip, and they are most of this command's
wall-clock. Measured runs spent 13–15 — reading unrelated PRs, their comments, and merged
history — for information that changed nothing. The list is fixed:

| # | When | Call | Answers |
|---|---|---|---|
| 1 | before | PRs for **this source branch** | is there already a PR? (§8 idempotency) |
| 2 | before | recent PRs into the destination, `pagelen=5` | reviewer UUIDs and the house title shape |
| 3 | post | `bb_post` create | — |
| 4 | after | the created PR | id, state, draft, src, dst, title, url |
| 5 | after | its commits | does it contain what was pushed |

Call 2 is skipped entirely on a re-run, or whenever the reviewers are already known.

Do not fetch: another PR's comments, merged PRs, PRs for a different branch, the diff or
the diffstat through the API, or a PR you are not about to create or verify. If a question
cannot be answered from the five calls above, it is not a question this command needs to
answer — say what is unknown and let the user decide.

```
list PRs for a branch   bb_get  /repositories/lisafk/<repo>/pullrequests
                          queryParams q=source.branch.name="<branch>"
                          jq values[*].{id:id,state:state,dest:destination.branch.name,title:title}
recent PRs into a dest  bb_get  /repositories/lisafk/<repo>/pullrequests
                          queryParams q=destination.branch.name="<dest>"  pagelen=5  sort=-updated_on
                          jq values[*].{id:id,author:author.display_name,rev:reviewers[*].{n:display_name,uuid:uuid}}
create                  bb_post /repositories/lisafk/<repo>/pullrequests
update title/desc       bb_put  /repositories/lisafk/<repo>/pullrequests/<id>
verify                  bb_get  /repositories/lisafk/<repo>/pullrequests/<id>
                          jq {id:id,state:state,draft:draft,src:source.branch.name,dst:destination.branch.name,title:title,url:links.html.href}
commits in the PR       bb_get  /repositories/lisafk/<repo>/pullrequests/<id>/commits
                          jq values[*].{hash:hash,msg:summary.raw}
```

## Create body

Only fields this platform actually takes — nothing invented:

```json
{
  "title": "...",
  "description": "...",
  "source":      { "branch": { "name": "<work branch>" } },
  "destination": { "branch": { "name": "<destination>" } },
  "reviewers":   [ { "uuid": "{...}" } ],
  "draft": true,
  "close_source_branch": false
}
```

- `close_source_branch: false` matches every recent PR here.
- Reviewers are **UUIDs**, not names or display names.
- `draft: true` is the default for this workspace. **Verify it came back true** on the
  fetch-back step — if the created PR reports `draft: false`, the field was ignored by the
  API; say so and tell the user to mark it draft in the browser. Never report a draft PR
  that is not one.

## Verify, then report

After `bb_post`, fetch the PR back and confirm **id, repo, source, destination, title,
draft, and the commits it contains**. A PR is reported as created only after that check
passes. If the commit list does not match what you pushed, say so rather than reporting
success.

## Screenshots

UI PRs here carry Bitbucket-hosted images:

```
![](https://bitbucket.org/repo/bxjg5L4/images/1126540498-image.png){: data-layout='center' }
```

Those URLs are minted by uploading through the PR editor in the browser. **The API cannot
create one and cannot attach a local file.** So: include an image only when the user
supplies an already-uploaded Bitbucket URL; otherwise omit it entirely and tell them to
attach it in the browser after the PR is open. Never invent an image URL, never point at a
local path, never leave a placeholder.
