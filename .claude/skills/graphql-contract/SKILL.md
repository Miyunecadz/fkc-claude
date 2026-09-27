---
name: graphql-contract
description: Use when changing the shared GraphQL API surface — typedefs, queries, mutations, subscriptions, inputs or permissions — that the admin web client and the mobile app depend on.
stacks: [graphql-apollo-server, graphql-apollo-client]
---

# GraphQL contract

`docs/_shared/api-contract.md` maps the surface and its rules. Use it to find your way.
The code on both sides is the truth, and wins when they disagree:

- **Server (truth):** `fk-admin-panel-be/src/typedefs/<name>.typedef.js`, merged in
  `fk-admin-panel-be/index.js`. Resolvers in `src/resolvers/`. Permissions per
  operation in `src/configs/shield.js`, helpers in `src/utils/permissions/`.
- **Consumers:** `gql` constants in `fk-admin-panel-fe/src/graphql/<area>.js` and
  `fk-mobile/src/graphql/<area>.js`.

**Find every consumer** before changing a field or argument:

```bash
grep -rn "<fieldOrOperation>" fk-admin-panel-fe/src fk-mobile/src
```

Graph maps have no cross-repo edges, so grep is the only reliable check.

**Rules:**

- **Additive first.** Add fields, types and optional arguments. Do not change existing ones.
- **Deprecate before removing.** Mark with `@deprecated`, move both clients off, then remove.
  The mobile app in users' hands cannot be updated at once.
- **Permission with the field.** A new Query or Mutation without a `shield.js` rule is a gap.
- **Done means every consumer.** Name each client file that changes, or say none do.
