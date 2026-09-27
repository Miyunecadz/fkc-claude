# Validation — what actually exists here

There is almost no automated test coverage in this workspace. CI runs a deploy step, not
lint or tests, and the clients' husky hooks run no suite. So validation is a few real
commands plus named manual checks. The failure to guard against is reporting a check that
never ran.

Run everything from the ticket's tree (`ticket-worktree.sh tree <KEY> <repo>`).

| Repo | Real checks | Not a check |
|---|---|---|
| `fk-admin-panel-be` | `node --check <file>` for every changed JS file; the boot below when typedefs or permissions changed; `yarn db:status` after a migration | `yarn test` is `echo "Error: no test specified" && exit 1`. There is no ESLint or Prettier config |
| `fk-admin-panel-fe` | `yarn lint` (`eslint src`); `yarn build` (craco) | `yarn test` — one test file in `src/`, proves nothing about a change elsewhere. `test:chrome`/`firefox`/`safari` open a browser and pause |
| `fk-mobile` | none runnable: no `node_modules` | `yarn lint` and `yarn test` need an install. Never start one |

## Backend boot

`yarn start` runs nodemon and never exits, and the server needs MariaDB and Redis from the
checkout's `.env`. Bound it and read the log:

```bash
(cd "$tree" && timeout -k 5 60 yarn start >> "$log" 2>&1); echo "exit=$?"
grep -m1 -E 'Graphql is ready on port|Invalid permission|Error' "$log"
```

| Log shows | Record |
|---|---|
| `Graphql is ready on port` | `BOOT OK` — typedefs merged and permissions passed `assertValidPermission` |
| `Invalid permission "<name>"`, or a GraphQL schema error | `BOOT FAILED` with that line |
| a database or Redis connection error, a port already in use, or neither line within 60s | `BOOT UNCHECKED` — the check could not run; say why |

Never record `BOOT OK` without the ready line.

## Verdicts and states

| Validator verdict | Means | Sidecar state |
|---|---|---|
| `VERIFIED` | at least one applicable check ran, and every applicable check passed | `VERIFIED` |
| `FAILED_VERIFICATION` | a check ran and failed on the code | `FAILED_VERIFICATION` |
| `INCONCLUSIVE` | no applicable check could run, or those that ran cannot speak to the change | `UNVERIFIED` |

Across repos the worst wins: any failure is `FAILED_VERIFICATION`; else any inconclusive is
`UNVERIFIED`; else `VERIFIED`. **Zero checks run is never `VERIFIED`.** An `fk-mobile`-only
ticket is always `UNVERIFIED`. The human sees `UNVERIFIED — no automated check covered this
change` plus the manual list, and review still runs.

## Recording

Full output goes to `.work/<KEY>/validate/<repo>.log` by absolute path. The sidecar gets
decisive lines only, with prepared and observed kept apart:

```markdown
prepared: <the checks this change needs, per repo>
observed:
- fk-admin-panel-fe: yarn lint → exit 0, "Done in 41.2s"
- fk-admin-panel-be: node --check src/resolvers/x.js → exit 0; boot → BOOT UNCHECKED (redis refused)
not run: fk-mobile yarn lint — no node_modules; it would have caught lint errors in the screen
manual:  <what a human must exercise, named: screen, mutation, role>
verdict: VERIFIED | UNVERIFIED | FAILED_VERIFICATION
```

After a `yarn build`, record the result, then `ticket-worktree.sh clean <KEY> <repo>` drops
the ~47M of output.

Rules: never report a check as passing unless it ran and passed; never let a tooling failure
pass as a code result; never run `npx eslint` in an uninstalled repo (it fetches ESLint 9,
which rejects these configs); never invent a command that is not in the repo's
`package.json`. Manual checks go through the running UI or the GraphQL playground at
`http://localhost:4000/graphql`.
