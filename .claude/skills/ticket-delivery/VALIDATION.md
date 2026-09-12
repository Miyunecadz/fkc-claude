# Validation — what actually exists here

There is effectively **no automated test coverage** in this workspace, and CI runs neither
lint nor tests: the pipelines run a deploy step, and the husky `pre-commit` hooks in the
clients do not run a suite. So validation is a small number of real commands plus honest
manual verification — and the failure mode to guard against is reporting a check that never
ran.

Run everything **from the ticket's worktree**, never from the user's checkout.

| Repo | Real checks | Do not rely on |
|---|---|---|
| `fk-admin-panel-be` | `node --check <changed file>` for every changed JS file; boot it (`yarn start`, or the `docker-compose.deps.yml` stack for mariadb+redis) — invalid SDL fails `mergeTypeDefs` and a bad permission name fails `assertValidPermission` at startup; `yarn db:status` after a migration | `yarn test` is `echo "Error: no test specified" && exit 1`. There is no ESLint or Prettier config in this repo at all — match the surrounding file |
| `fk-admin-panel-fe` | `yarn lint` (`eslint src`); `yarn build` (craco) | `yarn test` — `src/` holds a single test file; passing it proves nothing about a change elsewhere. `test:chrome`/`firefox`/`safari` are a `page.pause()` harness with no `playwright.config.*` — they open a browser and stop |
| `fk-mobile` | none runnable from a worktree | `yarn lint` and `yarn test` both need `node_modules`, which this repo does not have. Say so; do not promise the check and do not start a React Native install unprompted |

Preconditions to confirm before promising a check:

- `fk-admin-panel-be` and `fk-admin-panel-fe` have `node_modules` in the main checkout, and
  the worktree links to it — so their checks run. `fk-mobile` does not.
- Never fall back to `npx eslint` in an uninstalled repo: it fetches ESLint 9, which rejects
  these `.eslintrc.js` files with a flat-config migration error. That failure says nothing
  about the code.
- Never run an install inside a worktree (`WORKTREE.md` §3).

## After a build check — drop what it left behind

`yarn build` in `fk-admin-panel-fe` writes ~47M of craco output into the worktree, and
nothing used to remove it: it was the single largest thing a finished ticket workspace
held, long after anyone cared about it. Once the build's result is read and recorded,
the directory has done its job:

```bash
.claude/hooks/ticket-worktree.sh clean <KEY> [repo]
```

It deletes only untracked `build`/`dist`/`.next`/`coverage`, never anything git tracks, and
never source. Record the build's **result** first — the log line is the evidence, and a
cleaned directory is not a check that did not run.

## Recording

Full output goes to `.work/<KEY>/validate/<repo>.log`; the sidecar and the report get the
decisive lines only. Prepared and observed are recorded as two distinct things, because
this is exactly where an unrun check gets reported as a passing one:

```markdown
## Validate — <YYYY-MM-DD>
prepared: <the checks this change requires, per repo>
observed:
- fk-admin-panel-fe: yarn lint → "✖ 0 problems"        (.work/<KEY>/validate/fk-admin-panel-fe.log)
- fk-admin-panel-be: node --check src/resolvers/x.js → exit 0
not run: fk-mobile yarn lint — repo has no node_modules; it would have caught lint errors in the changed screen
manual:  <what a human must exercise, named specifically>
```

Beyond that, verification is manual: exercise the change in the running UI or the GraphQL
playground (`http://localhost:4000/graphql`) and state exactly what was exercised.

Three rules with no exceptions: never report a check as passing unless it ran and passed;
never let a tooling failure pass as a code result; never invent a command that is not in
that repo's `package.json`.
