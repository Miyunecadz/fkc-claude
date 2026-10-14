---
description: Capture UI evidence that a delivered ticket works — drive the running app with Playwright, screenshot the ticket's screens, and save them to .work/<KEY>/shots/ for a human to upload to the pull request
argument-hint: <FKC-123 | ticket key> (the app must be running at :3000 and :4000)
allowed-tools: Bash, Read, AskUserQuestion, Skill, mcp__jira__jira_get_issue, mcp__plugin_playwright_playwright__browser_navigate, mcp__plugin_playwright_playwright__browser_snapshot, mcp__plugin_playwright_playwright__browser_type, mcp__plugin_playwright_playwright__browser_fill_form, mcp__plugin_playwright_playwright__browser_click, mcp__plugin_playwright_playwright__browser_press_key, mcp__plugin_playwright_playwright__browser_wait_for, mcp__plugin_playwright_playwright__browser_take_screenshot, mcp__plugin_playwright_playwright__browser_navigate_back, mcp__plugin_playwright_playwright__browser_handle_dialog, mcp__plugin_playwright_playwright__browser_close
effort: medium
---

Capture evidence that the change works for:

$ARGUMENTS

This runs **after `/create-pr`**, once the PR is open. It drives the running app, screenshots
the screens that prove the ticket's goal, and saves them to `.work/<KEY>/shots/`. It uploads
nothing — the Bitbucket API cannot attach a PR image, so a human uploads the files to the PR.

It never edits source, never commits, never pushes, never touches Jira. Screens only.

## 1. Resolve and gate

```bash
.claude/hooks/ticket-worktree.sh list
.claude/hooks/ticket-worktree.sh sidecar show <KEY> --last Evidence PR
```

No argument: relay the list, ask which ticket, stop.

Read the Jira issue once with `mcp__jira__jira_get_issue` (`fields="*all"`, `include="comments"`).
The **goal and acceptance criteria** say what "working" looks like; the sidecar's `## Evidence`
image rows say what the screens should show.

`state:` should be `PR_OPEN` (or `HANDED_OVER`). Earlier → say the change is not delivered yet
and stop: evidence is for a delivered ticket. Note the PR URL from `## PR` for the report.

A backend-only ticket with no screen: there is nothing to photograph. Say so plainly, name
the API evidence instead (the query answering with real data, captured by the human from a
GraphQL client), and stop — do not invent a screen.

## 2. The app must be running

```bash
curl -fsS -o /dev/null -w "%{http_code}\n" http://localhost:3000 || echo DOWN
curl -fsS -o /dev/null -w "%{http_code}\n" http://localhost:4000/graphql || echo DOWN
```

Either `DOWN` → stop and ask the human to start the FE (`:3000`) and the GraphQL API
(`:4000`). This command never starts the stack. The URLs match `automation-testing/.env`
(`QA_BASE_URL`, `QA_API_URL`).

## 3. Decide what to shoot

From the goal, the acceptance criteria and the `## Evidence` rows, list the **screens and
states** that prove the change — most are 1–4 shots:

- the screen the ticket changes, in its new state;
- each distinct state an acceptance criterion names (empty vs populated, a permission allowed
  vs refused, before vs after a save);
- the signed-in landing page as the "logged in" proof, always first.

Confirm the list and the route(s) with the user if the ticket does not name them. Keep it to
what proves the goal; do not tour the app.

## 4. Sign in

Credentials are not read here (the `.env` guard blocks it). Ask the user for the admin email
and password with `AskUserQuestion`, or ask them to sign in themselves in the browser this
opens. Then, with the Playwright tools (selectors are `automation-testing/src/pages/LoginPage.ts`,
the source of truth — read it if the form has moved):

1. `browser_navigate` to `http://localhost:3000/login`.
2. `browser_fill_form` the **Email** and **Password** textboxes, then `browser_click` the
   **Login** button.
3. The one-time **Privacy Policy** gate may appear: tick **I have read…** and click
   **Continue**. If it does not appear in a few seconds, carry on.
4. `browser_wait_for` the URL to leave `/login`, then shoot the landing page (step 5) as
   `00-logged-in`.

## 5. Capture, one screen at a time

```bash
mkdir -p .work/<KEY>/shots
```

Per target screen, in order:

1. `browser_navigate` to its route, or click through the UI to reach it.
2. `browser_wait_for` the element that proves the state is really there (a row, a message, a
   value) — never a fixed sleep.
3. `browser_take_screenshot`, saving to `.work/<KEY>/shots/NN-<kebab-label>.png`
   (`00-logged-in.png`, `01-<screen>.png`, …). Full page when the proof is below the fold.

Never photograph a bearer token, a password field with a value, or a failing/error response
dressed up as a pass. If the only way to show a state exposes a secret, note it in the report
instead of shooting it.

Close the browser with `browser_close` when done.

## 6. Report and hand off

```bash
ls -la .work/<KEY>/shots/
```

Report: the ticket key and the PR URL; each saved file with one line on what it proves; any
acceptance criterion you could **not** capture and why. Then the handover line:

> Evidence is in `.work/<KEY>/shots/`. Upload these to the pull request by hand — open the PR,
> add them as attachments or in a comment. The Bitbucket API cannot attach a PR image, so this
> step is manual.

Never call the ticket done here; evidence is a record, not a gate.
