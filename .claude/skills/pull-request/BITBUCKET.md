# Bitbucket Cloud — the mechanism

| Fact | Value |
|---|---|
| Remote | `origin` → `git@bitbucket.org-247tech:lisafk/<repo>.git` (SSH host alias) |
| Workspace / slug | `lisafk/fk-admin-panel-be`, `lisafk/fk-admin-panel-fe`, `lisafk/fk-mobile` |
| Merges | merge commit — `Merged in <branch> (pull request #N)` |
| Default reviewers | **none configured** — the API adds none unless you pass them |

`pr-preflight.sh` derives the platform and slug from the remote on every run and stops if
it is not Bitbucket. Trust the script over this table.

## Tools

Load them with `ToolSearch` (`select:mcp__bitbucket__bb_get,mcp__bitbucket__bb_post,mcp__bitbucket__bb_put`).
`gh` is GitHub and useless here. **If the Bitbucket tools are unavailable, do not invent
another route**: print the title, description, source and destination for the user to paste,
and say the PR was not created.

The `/2.0` prefix is added for you. Always pass `jq` — an unfiltered response is enormous.
The `pr-body.py` hook checks every `bb_post`, `bb_put` and `bb_patch` to a PR path.

## The call budget — 5, including the post

| # | When | Call | Answers |
|---|---|---|---|
| 1 | before | PRs for **this source branch** | is there already a PR? |
| 2 | only if the user named reviewers | recent PRs into the destination, `pagelen=5` | each named person's UUID |
| 3 | post | `bb_post` create | — |
| 4 | after | the created PR | id, state, draft, src, dst, title, url |
| 5 | after | its commits | does it hold what was pushed |

Do not fetch another PR's comments, merged PRs, PRs for another branch, the diff or
diffstat, or a PR you are not about to create or verify. A question these five calls cannot
answer is not one this command needs — say what is unknown.

```
1 list PRs for a branch   bb_get  /repositories/lisafk/<repo>/pullrequests
                            queryParams q=source.branch.name="<branch>"
                            jq values[*].{id:id,state:state,dest:destination.branch.name,title:title}
2 reviewer UUIDs          bb_get  /repositories/lisafk/<repo>/pullrequests
                            queryParams q=destination.branch.name="<dest>"  pagelen=5  sort=-updated_on
                            jq values[*].reviewers[*].{n:display_name,uuid:uuid}
3 create                  bb_post /repositories/lisafk/<repo>/pullrequests
  update title/desc       bb_put  /repositories/lisafk/<repo>/pullrequests/<id>
4 verify                  bb_get  /repositories/lisafk/<repo>/pullrequests/<id>
                            jq {id:id,state:state,draft:draft,src:source.branch.name,dst:destination.branch.name,title:title,url:links.html.href}
5 commits in the PR       bb_get  /repositories/lisafk/<repo>/pullrequests/<id>/commits
                            jq values[*].{hash:hash,msg:summary.raw}
```

A named reviewer who is not in call 2's result is left off and reported. Never guess a
UUID from a name.

## Create body

Only fields this platform takes:

```json
{
  "title": "<contents of <repo>.title>",
  "description": "<contents of <repo>.md, verbatim>",
  "source":      { "branch": { "name": "<work branch>" } },
  "destination": { "branch": { "name": "<destination>" } },
  "reviewers":   [ { "uuid": "{...}" } ],
  "draft": true,
  "close_source_branch": false
}
```

Reviewers are UUIDs, not names; omit the field when there are none. `draft: true` is the
default here — **verify it came back true** at call 4. If it reports `false`, say so and
ask the user to mark it draft in the browser. Never report a draft PR that is not one. If
call 5's commits do not match what you pushed, say so rather than reporting success.

## Screenshots

Bitbucket-hosted image URLs are minted only by uploading through the PR editor in the
browser; the API has no attachment endpoint. Include an image only when the user gives an
already-uploaded URL. Otherwise leave it out and tell them to attach it after the PR is
open. Never invent an image URL, point at a local path, or leave a placeholder.

Taking the picture is automated. It shoots the GraphQL Playground the backend serves, with
the query and its real response, exits non-zero on `errors`, and aborts if the token is on
screen. Shoot the ticket's own code on its own port:

```bash
# one-off on WSL: sudo apt install libasound2t64
NODE_PATH=<repo-with-playwright>/node_modules node .claude/hooks/pr-endpoint-shot.js \
  --endpoint http://localhost:<port>/graphql --spec .work/<KEY>/shots/spec.json \
  --out .work/<KEY>/shots --token-file <file holding a bearer token>
```
