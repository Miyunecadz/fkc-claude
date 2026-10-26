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

**Code craft (the lines you write)**

- Shape the control flow of code you write or change; spacing, quotes and naming still
  match the file. Applies to your new lines and to junior code in a block you are
  already editing; never a shared helper or an untouched file (report those).
- `const` by default; `let` only when you reassign. A simple either/or is a ternary,
  not `let` + `if`/`else`. Never nest ternaries.
- Return early for loading, error and empty states before the main JSX; no deep ternary
  tree inside the returned markup. No `else` after a branch that returns.
- Derive, don't mirror: compute a value from props or state during render instead of
  copying it into another `useState` + `useEffect`.
- Destructure props and hook results at the top. Keys come from ids, never the array index.
- `useMemo`/`useCallback` only for a real referential-stability need, not by reflex.

**Best practices (new code)**

- Same scope as Code craft above: your new or changed lines only.
- One component, one job. Split a component that grows past ~150 lines or handles two
  unrelated concerns; keep a small, focused one whole.
- Lift state only as high as it is shared; colocate it with the component that uses it.
- Guard query data before you read it: `data?.thing ?? fallback`, and render the loading
  and error states first (as in Code craft).
- Event handlers are named `handleX`. In a list row, don't pass a freshly built function
  or object prop each render if it drives re-renders — hoist it or memoise it.
- Inputs have labels; a clickable thing is a `<button>`, not a `<div>` with `onClick`.
- `===` and `!==` only. Destructure the props and hook results you use at the top.

**Readability and house style**

- Match the nearest similar file: its naming, casing, import style, file shape and
  comment density. Copy the pattern; do not invent one.
- Full words for names — `index`, `response`, `connection` — unless the surrounding file
  already uses the short form. The file's own idiom wins.
- A comment says *why*, and only where the nearby code already comments. Never a comment
  that restates what the line does. No commented-out code, no `TODO`/`FIXME`, no
  `console.log` left behind.
- Nothing the task did not need: no scaffolding, no example code, no narration of the work.
- Re-read the diff as a stranger. Delete any line that only explains the code, or shortens
  a name the file spells out.
