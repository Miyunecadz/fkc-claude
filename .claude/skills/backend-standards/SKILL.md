---
name: backend-standards
description: Use when editing fk-admin-panel-be — GraphQL typedefs, resolvers, graphql-shield permissions, dbmate migrations, Bull queues or cron. Load before writing backend code.
stacks: [graphql-apollo-server, node-dbmate]
---

# Backend standards (fk-admin-panel-be)

**Read `docs/fk-admin-panel-be/conventions.md` first.** It holds the rules the code cannot show. It was
written from the code on a date and may lag: when it and the code disagree, the code wins,
and you fix the doc in the same change.

**Find the pattern first.** Locate the nearest similar file and copy its shape:
`.claude/hooks/graph.sh query fk-admin-panel-be "<feature>"`. For an overview, read
`fk-admin-panel-be/graphify-out/GRAPH_REPORT.md`.

**Verified facts:**

- **Schema:** one `src/typedefs/<name>.typedef.js` per area, paired with
  `src/resolvers/<name>.resolver.js`. Every file in those folders is loaded
  (`src/utils/export.js`), keyed on `<name>` — keep the `<name>.<kind>.js` form.
- **Permissions:** every Query and Mutation needs a rule in `src/configs/shield.js`
  (helpers in `src/utils/permissions/`). A resolver without a rule is a gap.
- **Migrations:** dbmate SQL in `db/migrations/` (`dbmate.yml`). New file via
  `yarn db:new <name>`; never edit one already applied. `db/schema.sql` is generated.
- **Background work:** Bull queues in `src/utils/queue.js`; cron jobs in `src/cron/`.
- **Checks:** no tests (`yarn test` exits 1) and no lint config. Say so; do not
  claim a check passed.

API surface changes: also load `graphql-contract`.
