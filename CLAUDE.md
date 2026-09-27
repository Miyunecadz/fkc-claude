# fk-connect — Workspace Router

A Lodestar workspace: three independent repos coordinated from one root. This file routes; skills hold the detail and load on demand.

## Repositories

- **fk-admin-panel-be** — GraphQL API, DB and auth owner (Node/Express, Apollo Server, MariaDB via dbmate, Redis/Bull, cron).
- **fk-admin-panel-fe** — Admin web client (React 18 on CRACO, Apollo Client, ag-grid, Tailwind).
- **fk-mobile** — Mobile app (React Native, Apollo Client, NativeWind, Firebase messaging).

The root is its own git repo that ignores the three repos. Always run git as `git -C <repo> …`.

## Cross-repo contract

Start at `docs/repo-map.md`. The contract doc is `docs/_shared/api-contract.md`; each repo has
`docs/<repo>/conventions.md`. Docs may lag the code. When they disagree, the code wins:

- Schema: `fk-admin-panel-be/src/typedefs/*.typedef.js`, resolvers in `src/resolvers/`, permissions in `src/configs/shield.js` and `src/utils/permissions/`.
- Client operations: `fk-admin-panel-fe/src/graphql/` and `fk-mobile/src/graphql/`.

## Loading policy

- Load a skill only when the task matches its description. Do not read ahead.
- Stay in the repo the task is in.
- Planning → planning skills. Writing code → the repo's standards skill.
- Architecture maps: query through the resolver, never with `--graph` by hand. Each repo and each ticket worktree under `.work/` has its own map on its own commit; `graph.sh` picks the right one and rebuilds it if the code moved.

  ```bash
  .claude/hooks/graph.sh status
  .claude/hooks/graph.sh query <repo-worktree-or-file> "<question>"
  ```

## Writing style

British English, plain words, short sentences, answer first. Rules: `.claude/skills/plain-uk-english/SKILL.md`.

## Enforcement

Guardrails in `.claude/guardrails/` are enforced, not advisory. They block commits to a default branch, destructive commands, edits to secret and `.env` files, hand edits to `db/schema.sql` and applied dbmate migrations. Follow the redirect a blocked action gives you.

## Onboarding a new repo

Run `/lodestar-onboard ./<new-repo>`.
