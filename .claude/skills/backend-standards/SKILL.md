---
name: backend-standards
description: Use when writing, changing or reviewing code in fk-admin-panel-be — GraphQL typedefs, resolvers, graphql-shield permissions, raw SQL, dbmate migrations, Bull queues or cron. Load before writing backend code. Not for planning a change (planning-workflow), diagnosing a bug before the fix (bug-investigation), or finding which clients use a field (graphql-contract).
stacks: [graphql-apollo-server, node-dbmate]
---

# Backend standards (fk-admin-panel-be)

Write backend code that matches this repo and would pass a senior review: safe SQL,
honest errors, explicit permissions, reversible migrations. The rules below apply to
the lines you write or change. Never refactor or re-indent existing code the task
does not need. If legacy code in your path breaks a rule, leave it and name it in
your report.

## 1. Before you write

1. **Read `docs/fk-admin-panel-be/conventions.md`.** It holds what the code cannot show.
   It may lag. When it and the code disagree, the code wins: follow the code and name
   the stale line in your report. If the file is missing, say so and go on with this
   skill.
2. **Pick the path.** Inside a ticket, `<path>` is the worktree
   (`.work/<KEY>/fk-admin-panel-be`). Otherwise it is `fk-admin-panel-be`. Querying
   the wrong one describes the wrong branch.
3. **Find the pattern to copy** with the graph (section 2). Copy the shape of a model
   file (section 3), not of the nearest file, which may be legacy.
4. **Check the blast radius** of every shared file you will change:
   `graph.sh affected <path> "src/utils/<file>.js"`. List the callers in your report.
5. **API surface change** (typedef, argument, permission): also load `graphql-contract`.

## 2. Using the graph

All commands are `.claude/hooks/graph.sh <command> <path> ...` from the workspace root.
Each call rebuilds a stale map first (about 2–4s), so it always describes the current
code, including uncommitted edits.

| Need | Command |
|------|---------|
| Where does X live, what is near it | `query <path> "<exact file or function names>"` |
| What one file or function connects to | `explain <path> "src/utils/query.js"` |
| Who breaks if I change this | `affected <path> "src/utils/subcontractpackage-write.js"` |
| How A reaches B | `path <path> "subcontractpackage.resolver.js" "db.js"` |

Rules:

- **Name real things.** A vague phrase ("supplier stuff") returns hundreds of nodes.
  Use file names, function names or table names.
- **Prefer file paths to bare symbols.** Several files define local helpers with the
  same name. `explain "executeSqlQuery"` resolves to a copy in `src/cron/card-expire.js`.
  Check the `Source:` line matches the file you meant.
- **The graph locates; the code decides.** Read `path:line` before you state what code
  does. `INFERRED` edges are guesses (average confidence about 0.5).
- **No cross-repo edges.** For client usage, grep as `graphql-contract` says.
- **Never pass `--graph` and never run `graphify` by hand.** `graph.sh` picks the map.
- **If `graph.sh` exits 2** (graphify missing) or fails: say so, then use grep and read
  the files. Never write a graph by hand.
- `fk-admin-panel-be/graphify-out/GRAPH_REPORT.md` gives the overview. Ignore its
  "Built from commit" line; `graph.sh status` is the truth. The
  `architecture/graph.json` link in `conventions.md` is dead; the map lives in
  `graphify-out/` and is reached only through `graph.sh`.

## 3. Verified facts

- **Loading is automatic.** `src/utils/export.js` scans `src/typedefs/` and
  `src/resolvers/` and keys each file on `<name>` from `<name>.<kind>.js`. Add
  `<name>.typedef.js` + `<name>.resolver.js`; do not edit either `index.js`.
  (`conventions.md` says to register them by hand — it is wrong.)
- **Model files to copy:** `src/resolvers/noseries.resolver.js` (small, validated,
  `withTransaction`, `FOR UPDATE`) and `supplierCreate` onward in
  `src/resolvers/suppliers.resolver.js` (not `supplierArchive` above it, which
  destructures `executeSqlQuery` without checking `error`).
  **Do not copy:** `card.resolver.js`, `orderLine.resolver.js:65-104`,
  `auth.resolver.js:380-392` (raw interpolation, commit without begin).
- **DB:** raw SQL on a `mariadb` pool (`src/configs/db.js`). Helpers in
  `src/utils/query.js`:
  - `executeSqlQuery({ query, values })` returns rows, **or `{ error }` instead of
    throwing**. Check it every time.
  - `withTransaction(async (conn) => ...)` begins, commits, rolls back and releases.
  - `filterSqlBuilder` / `filterSqlBuilderv2` and `infiniteSqlBuilder` put values into
    the SQL text unescaped.
  - `buildTextSearchClause` / `sanitizeSearchWord` in `src/utils/search.js` are the
    escaped way to build a text search.
  - Stored procedures are common (`CALL supplier_create(?, ...)`); keep using one where
    the area already does.
- **Context:** the decoded JWT. `context.sessionId` is the user id. `errorCode` is
  unused; do not rely on it.
- **Permissions:** `src/configs/shield.js`. Rules: `isAuthenticated`,
  `requiresPermission(...)`, `requiresAnyPermission`, `requiresPermissionForArgs`,
  composed with `chain(...)`. Strings are `<web|mobile>.<name>.<action>`, checked at
  start-up by `assertValidPermission`, and granted from the `permissions` table.
  **Shield has no `fallbackRule`**, so a field without a rule is public, and there is
  no `Subscription` key at all.
- **Migrations:** dbmate SQL in `db/migrations/`. New file with `yarn db:new <name>`.
  Never edit an applied one. `db/schema.sql` is generated.
- **Queues:** Bull. `src/utils/queue.js` (pdf, payslip: hard-coded Redis, no retries)
  and `src/utils/tender-notifications/` (env Redis, `attempts`, exponential backoff,
  final-attempt handling in `worker.js`). Copy the second.
- **Cron:** `src/cron/`, auto-loaded, runs only when `NODE_ENV === 'production'`.
- **Pub/sub:** in-memory `PubSub` (`src/configs/pubsub.js`), one process only.
- **Style:** CommonJS, `async`/`await`. Indent and quotes vary by file (2 or 4 spaces;
  single or double). Match the file you are in.

## 4. Rules for new and changed code

Code shapes for each rule are in `references/patterns.md`. Read it when you write the
thing the rule covers.

**SQL**
- Every value goes through a `?` placeholder. Lists: `IN (${ids.map(() => '?').join(',')})`.
- Never put an argument, filter value or token into SQL text. Column or sort names that
  come from input must come from a fixed allow-list.
- Do not pass user text to `filterSqlBuilder`. For text search use `buildTextSearchClause`.
- Name the columns you select. No `SELECT *` in new queries (the model files still
  have some; do not copy that part).
- After `executeSqlQuery`, check `result.error` before using rows: throw it, or log it
  and throw a plain `GraphQLError` (as in `references/patterns.md`).

**Transactions**
- Two or more writes that must succeed together go in `withTransaction`. Inside it use
  `conn.query` only; `executeSqlQuery` takes another connection and escapes the transaction.
- Read-then-write on the same row (counters, number series, status changes) locks the row:
  `SELECT ... FOR UPDATE`.
- Side effects (email, S3, `queue.add`, `pubsub.publish`) run after the transaction
  returns, never inside it. A rollback cannot undo an email.
- Multi-row inserts use `conn.batch`, not a query per row.

**Errors and validation**
- Bad input: `throw new UserInputError('<what is wrong>', { field: '<argName>' })`.
- Business rule or not found: `throw new GraphQLError('<plain reason>')` with a message
  the client can show.
- Never swallow an error, never `catch (e) { throw e; }`, and never replace an error with
  a generic one that loses the cause. If you catch, log it and rethrow or wrap it.
- Validate and normalise at the top of the resolver, before any write. Reuse
  `src/utils/money.js` (`parseMoneyFromInput`) and `src/utils/number.js`.
- Money in new columns is whole pence as an integer (`*_pence`). Use `DECIMAL` only to
  match an existing table.

**Permissions**
- Every new Query and Mutation gets an explicit rule in `shield.js`, placed with its
  area. `isAuthenticated` is the minimum; add `requiresPermission('web.<area>.<action>')`
  when the action is limited to a role.
- A new permission string needs a row: insert it into `permissions` in a migration, and
  delete it in the down block.
- A new Subscription is not covered by shield. Check `sessionId` in its `withFilter` or
  `subscribe`.
- Scope user-owned data by `sessionId`. Never trust an id from args to prove ownership.

**Performance**
- No query inside a loop, and no field resolver that queries once per parent. Fetch the
  children in one query (`JOIN` + `JSON_ARRAYAGG`, or one `IN (?)` batch) and attach them.
- A new column you filter or join on gets an index in the same migration.

**Migrations**
- One change per file. Write both `-- migrate:up` and `-- migrate:down`; down undoes up
  exactly (drop the foreign key before the column). Leave down empty only for a data
  backfill, with a comment saying so.
- New tables: plural `snake_case`, `id BIGINT NOT NULL AUTO_INCREMENT`, `created_at`,
  `updated_at`, `*_by` for actors, `is_active` for soft delete, named keys
  (`uq_`, `idx_`, `fk_<table>_<col>`), `ENGINE = InnoDB DEFAULT CHARSET = utf8mb4`.
- Additive first: new columns are nullable or have a default. Never rename or drop a
  column a client still reads (see `graphql-contract`).

**Queues, cron, pub/sub**
- Slow or bulk work (PDF, Excel, email batches) goes to a Bull queue, not the resolver.
- A new queue copies `src/utils/tender-notifications/queue.js`: Redis host from env,
  `attempts`, backoff, bounded `removeOnComplete`/`removeOnFail`.
- Job data holds ids, not whole rows. Handlers are idempotent, because retries run them
  again.
- Cron jobs must be safe to run twice and must not overlap themselves.
- Publish to pub/sub after the write commits.

**Logging and secrets**
- `console.error('[<area>] <what failed>', error)` with a tag, as in
  `src/utils/tender-notifications/`.
- Never log tokens, passwords, bank details or national insurance numbers.
- Never hard-code a per-environment value; read `process.env`.

**Shared legacy helpers**
- Do not change `executeSqlQuery`, `filterSqlBuilder`, `shield.js` options or
  `src/utils/queue.js` unless the task asks. Report problems you see in them instead.

## 5. Before you say done

1. Run `node --check <file>` on every changed `.js` file. It checks syntax only.
2. There are no tests (`yarn test` exits 1) and no lint config. Say so. Never claim a
   check passed that did not run.
3. Re-run `graph.sh affected` on each shared file you changed and confirm every caller
   still fits the new behaviour.
4. Walk the checklist: placeholders only; `result.error` checked; writes in one
   transaction; side effects after commit; shield rule for each new operation;
   permission row seeded; migration down block; no query in a loop; nothing logged
   that is secret.
5. Report: files changed, callers checked, the checks that ran, anything skipped, and
   any legacy problem you saw but did not touch.

When reviewing someone else's change, use the same checklist and cite `path:line`
for each finding.

## Example

Task: "let admins restore an archived supplier" in `.work/FKC-310/fk-admin-panel-be`.

1. `graph.sh query .work/FKC-310/fk-admin-panel-be "suppliers.resolver.js supplierArchive"`
   finds the resolver, `src/typedefs/suppliers.typedef.js` and the `suppliers` table
   (`is_active`, `archived_at`, `archived_by`).
2. Name it as the area does: `supplierRestore(id: ID!): Supplier!` beside
   `supplierArchive` in the typedef.
3. Resolver: `withTransaction`; `SELECT id, is_active FROM suppliers WHERE id = ? FOR UPDATE`;
   `UserInputError('Supplier not found', { field: 'id' })` when there is no row;
   `UPDATE suppliers SET is_active = 1, archived_at = NULL, archived_by = NULL,
   updated_at = NOW(), updated_by = ? WHERE id = ?`; return through `formatSupplier`.
4. `shield.js`: `supplierRestore: isAuthenticated`, beside `supplierArchive`. Use
   `requiresPermission` only if the ticket limits it to a role, and then seed the row.
5. Load `graphql-contract` and grep both clients. `node --check` both files. Report
   that no tests exist, and that `supplierArchive` does not check `result.error`
   (seen, not touched).
