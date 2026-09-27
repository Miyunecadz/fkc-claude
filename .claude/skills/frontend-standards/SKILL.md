---
name: frontend-standards
description: Use when editing fk-admin-panel-fe — React components, pages and routes, Apollo Client queries, ag-grid tables or Tailwind styling. Load before writing frontend code.
stacks: [react-craco]
---

# Frontend standards (fk-admin-panel-fe)

**Read `docs/fk-admin-panel-fe/conventions.md` first.** It holds the rules the code cannot show. It was
written from the code on a date and may lag: when it and the code disagree, the code wins,
and you fix the doc in the same change.

**Find the pattern first.** Locate the nearest similar file and copy its shape:
`.claude/hooks/graph.sh query fk-admin-panel-fe "<feature>"`. For an overview, read
`fk-admin-panel-fe/graphify-out/GRAPH_REPORT.md`.

**Verified facts:**

- **Stack:** React 18 on CRACO (`craco.config.js`), Tailwind (`tailwind.config.js`),
  React Router 6, `@apollo/client` 3.
- **Layout:** components are atomic — `src/components/atoms|molecules|organisms|templates`.
  Pages are templates, wired to URLs in `src/config/routes.js`; menu in `src/config/menu.js`.
- **Data:** Apollo client set up in `src/config/apollo.js`. Operations are `gql`
  constants in `src/graphql/<area>.js`. Shared state in `src/context/`.
- **Grids:** ag-grid 34. Reuse an existing table wrapper such as
  `src/components/molecules/custom-table.jsx` rather than new grid wiring.
- **Checks:** `yarn lint` (`.eslintrc.js`), `yarn build`. Prettier config in
  `.prettierrc.js`. Tests are thin: one unit test plus Playwright `browser.test.ts`.
