---
name: architecture-overview
description: Use when you need the big picture of how the three repos connect, or to trace a flow across a repo boundary (client screen to backend resolver to database).
stacks: [all]
---

# Architecture overview

**Shape:** `fk-admin-panel-fe` (web) and `fk-mobile` (app) are Apollo clients of the
GraphQL API in `fk-admin-panel-be`. The backend owns the MariaDB database, auth,
Bull queues and cron.

Repos, branches and cross-repo docs: `docs/repo-map.md`. Surface and permissions:
`docs/_shared/api-contract.md`.

**Within one repo,** query its map rather than re-reading source:

```bash
.claude/hooks/graph.sh query    <repo-worktree-or-file> "<question>"
.claude/hooks/graph.sh affected <path> "<symbol>"   # what a change reaches
.claude/hooks/graph.sh explain  <path> "<symbol>"
```

Each map describes the branch its checkout is on. A ticket worktree under `.work/`
has its own. Confirm any `path:line` in source before asserting behaviour.

**Across repos,** the maps cannot help. The link is runtime GraphQL, not static
imports, so no map has a cross-repo edge. Trace it by hand:

1. Client operation: `gql` constant in `fk-admin-panel-fe/src/graphql/` or `fk-mobile/src/graphql/`.
2. Schema: `fk-admin-panel-be/src/typedefs/<name>.typedef.js`.
3. Permission: `fk-admin-panel-be/src/configs/shield.js`.
4. Resolver: `fk-admin-panel-be/src/resolvers/<name>.resolver.js`, then the SQL or queue it calls.

For changes to that surface, load `graphql-contract`.
