---
name: frontend-standards
description: Use when editing the frontend repo (fk-admin-panel-fe) — React/CRACO components, Apollo Client, ag-grid, or Tailwind.
stacks: [react-craco]
---

# Frontend standards (fk-admin-panel-fe)

Conventions live in the docs, not here. Read **`docs/fk-admin-panel-fe/conventions.md`** and **`docs/fk-admin-panel-fe/architecture/`** before editing.

**Key reminders:**

- **Data:** Apollo Client cache patterns (fetch policies, cache updates, normalization) are documented in `docs/fk-admin-panel-fe/`.
- **Grids:** ag-grid patterns are documented there too — follow them rather than inventing new grid wiring.
- Components are React on **CRACO**, styled with Tailwind.

Details and the actual component/module layout are in `docs/fk-admin-panel-fe/` — go there.
