# Boards and servers — which Jira, which profile

This workspace raises tickets on more than one Jira site. This file owns the choice of
**board**, the **MCP server** that reaches it, and the **board profile** that sets which
sections the ticket carries and how its text and attachments are handled. SKILL.md §1 and
JIRA.md §1 defer here. No board is hardwired; the servers come from `.mcp.json`.

## 1. Resolve the target board — from config and the request

1. Read `.mcp.json` at the workspace root. Every server whose command runs `mcp-atlassian`
   is a board: take its tool namespace (`mcp__<server>__*`), the key after its
   `--jira-projects-filter`, and the path after its `--env-file` (that board's credentials,
   used only by the REST fallback in §3). On this machine, for illustration:

   | Server namespace | Key | `--env-file` |
   |---|---|---|
   | `mcp__jira__` | `FKC` | the path in that block |
   | `mcp__jira-247crm__` | `SUBC` | the path in that block |

   **`.mcp.json` is the only source of truth.** Never hardcode a server name, a key, a site
   or a credentials path — read each from the file at runtime, so the skill works for any
   user, any machine and whatever boards that file declares (one, both, or others). A board
   may be absent on a given machine; then it simply is not a choice.

2. **Named key wins.** The request names a key or board — an `FKC-*` / `SUBC-*` reference,
   or "on SUBC", "the subcontractor board" — → that board. Match the key prefix to a
   server's filter.
3. **One board only** in `.mcp.json` → use it.
4. **Nothing named and more than one board** → ask the requester which, offering the keys.
   Never default to the first.
5. A board's filter holds several comma-separated keys → ask which key, offering them.
6. **No `.mcp.json`, or it declares no `mcp-atlassian` server** → there is no board, so no
   ticket can be raised. Stop and say so in one line: *no Jira board is configured — this
   workspace has no `.mcp.json` with an `mcp-atlassian` server, so there is nowhere to raise
   the ticket.* Then point at the fix (add the server block, SKILL.md §1) and stop. Do **not**
   fall back to a user-level or plugin Jira server, and do not guess a key — that is the exact
   bias this file exists to prevent (SKILL.md §1 forbidden list).

`project_key` must match `^[A-Z][A-Z0-9_]+$`. From here "the server" means the resolved
board's namespace: every `mcp__jira__…` call in JIRA.md means `mcp__<resolved>__…`
(`mcp__jira-247crm__…` for SUBC).

## 2. Board profiles

A profile sets three things: the **fixed sections** appended after the build brief, whether
the board has **local code** in this workspace to inspect, and its **site quirks** (§3). The
first seven template sections — the build brief — are universal and never change per board.

Match the profile by the resolved board's key. A board that `.mcp.json` declares but that
has no profile below uses *An unknown board*. **No profile depends on another being present:**
with only SUBC on this machine the SUBC profile runs and FKC is irrelevant; with only FKC,
the reverse. The order here implies no default.

### FKC — the board whose code lives in this workspace

- Applies only when `.mcp.json` declares the `FKC` board; absent, skip this profile.
- Server `mcp__jira__`. **Local code: yes** — the three repos (`fk-admin-panel-be`,
  `fk-admin-panel-fe`, `fk-mobile`). Full triage, the inspection budget and the two
  technical sections apply.
- Fixed sections: `Affected System(s)`, `Other Info`, `Resolution` — TEMPLATE.md's last
  four, verbatim.
- Tier triggers: the full set, the repo-coupled ones included (TRIAGE.md §3).
- Attach: the MCP `attachments` input (JIRA.md §5).

### SUBC — the subcontractor board

- Server `mcp__jira-247crm__`. **Local code: none in this workspace** — do not inspect code,
  do not open the FK-Connect repos, and produce no file paths, branch, environment or
  `CODEBASE` severity. Skip the existence verdict (TRIAGE.md §2), omit `Files/areas to touch`
  and `Existing patterns to follow`, and build from the PO input and the screenshots only.
- **Stand-alone is a shape, not a wall.** The ticket carries no FKC key, path or code — that
  is *how it is written*, product-level and self-contained, never a reason to refuse or stall.
  You generate no FKC content for it, so there is nothing to block on. A genuine cross-site
  key, if one is unavoidable, gets an explicit link (JIRA.md §3). Work that also needs an FKC
  code change is a separate, optional FKC ticket — offered, never required, never blocking.
- Fixed sections: **none.** FKC's `Affected System(s)` / `Other Info` / `Resolution` are
  FK-Connect workflow, not this product. The ticket is Goal + numbered acceptance criteria
  + Decisions already made + Out of scope + Images.
- Tier triggers: the generic ones only (TRIAGE.md §3, marked "any board"); the repo-coupled
  triggers do not apply.
- Attach: no MCP upload tool — the REST fallback in §3.

### An unknown board

Build brief + `Images` only. Do not invent fixed sections and do not borrow FKC's. Tell the
owner the board has no profile, and ask which fixed sections it uses, or proceed with the
build brief alone. Add its profile here once known.

## 3. Site mechanics — text and attachments

Both sites today are Jira **Cloud**: the description goes up as Markdown and the server
converts it to ADF (JIRA.md §3). Per site:

- **FKC** — converter checked (JIRA.md §3 table). Attach through the MCP `attachments`
  input (JIRA.md §5).
- **SUBC (247crm)** — its converter parses `[...]` as a link everywhere, inline code and
  fenced blocks included (`[Foo!]` → a broken link), and turns a leading `# ` in inline code
  into a numbered-list item. So: keep `[` out of code spans, write list types in words, and
  read the issue back to check the body. No MCP upload tool — attach by sourcing the board's
  own credentials in a subshell and posting to the REST attachments endpoint. The creds file
  is the `--env-file` path from this board's `.mcp.json` block (§1); take it from there, never
  a fixed path:

  ```bash
  ENV_FILE="$(path after --env-file in the resolved board's .mcp.json block)"   # §1
  ( set +x; . "$ENV_FILE"
    curl -s -u "$JIRA_USERNAME:$JIRA_API_TOKEN" -H "X-Atlassian-Token: no-check" \
      -F "file=@<abs-path>;type=image/png" \
      "$JIRA_URL/rest/api/3/issue/<KEY>/attachments" )
  ```

  The env file supplies `JIRA_URL`, `JIRA_USERNAME` and `JIRA_API_TOKEN`. Never print the
  token. HTTP 200 returns the attachment id. Anything else → report the file as one to attach
  by hand, with the status line.
