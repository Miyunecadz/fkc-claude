# Backend code shapes (fk-admin-panel-be)

Shapes for the rules in `SKILL.md` section 4, taken from the model files. Match the
indentation and quote style of the file you are editing; these use 2 spaces.

## Resolver skeleton

From `src/resolvers/noseries.resolver.js` (the imports) and `src/resolvers/forecast.resolver.js:103-112` (the `IN` list).

```js
const { executeSqlQuery, withTransaction } = require('../utils/query');
const { camelCaseKeys } = require('../utils/format');
const { GraphQLError } = require('graphql');
const { UserInputError } = require('apollo-server-core');
const { pubsub } = require('../configs/pubsub');

const areaResolver = {
  Query: {
    getThings: async (_, { ids }, { sessionId }) => {
      if (!ids?.length) return [];

      const rows = await executeSqlQuery({
        query: `
          SELECT id, name, is_active
          FROM things
          WHERE is_active = 1
            AND id IN (${ids.map(() => '?').join(',')})
        `,
        values: ids,
      });

      if (rows.error) {
        console.error('[things] getThings failed', rows.error);
        throw new GraphQLError('Failed to load things, please try again.');
      }

      return rows.map((row) => camelCaseKeys({ ...row }));
    },
  },
};

module.exports = areaResolver;
```

## Validate first, then write in one transaction

From `noseries.resolver.js:36-100`: input checks before the transaction, row lock
inside it. Imports as in the skeleton above.

```js
thingUpdate: async (_, { id, fields }, { sessionId }) => {
  const name = fields?.name?.trim();
  if (!name) throw new UserInputError('Name cannot be blank', { field: 'name' });

  const updated = await withTransaction(async (conn) => {
    const [current] = await conn.query(
      'SELECT id, status FROM things WHERE id = ? FOR UPDATE',
      [id]
    );
    if (!current) throw new UserInputError('Thing not found', { field: 'id' });
    if (current.status === 'Closed')
      throw new GraphQLError('A closed thing cannot be changed.');

    await conn.query(
      'UPDATE things SET name = ?, updated_at = NOW(), updated_by = ? WHERE id = ?',
      [name, sessionId, id]
    );
    await conn.batch(
      'INSERT INTO thing_history (thing_id, name, created_by) VALUES (?, ?, ?)',
      [[id, name, sessionId]]
    );

    const [row] = await conn.query('SELECT id, name, status FROM things WHERE id = ?', [id]);
    return row;
  });

  // Side effects only after commit.
  await pubsub.publish('THING_UPDATED', { thingUpdated: camelCaseKeys({ ...updated }) });
  return camelCaseKeys({ ...updated });
},
```

## Allow-listed sort column

Input never becomes SQL text. Map it through a fixed object.

```js
const SORT_COLUMNS = { name: 'things.name', createdAt: 'things.created_at' };
const column = SORT_COLUMNS[sortBy] || SORT_COLUMNS.createdAt;
const direction = sortDir === 'ASC' ? 'ASC' : 'DESC';
const sql = `SELECT id, name FROM things ORDER BY ${column} ${direction} LIMIT ? OFFSET ?`;
```

## Text search

`src/utils/search.js` escapes each word. `filterSqlBuilder` does not.

```js
const { buildTextSearchClause } = require('../utils/search');

const searchClause = buildTextSearchClause({
  term: filter.search,
  columns: ['things.name', 'things.reference'],
});
const where = searchClause ? `AND ${searchClause}` : '';
```

## Children without N+1

One query for all parents, grouped in JS. No field resolver that queries per parent.

```js
const parentIds = parents.map((p) => p.id);
const lines = parentIds.length
  ? await executeSqlQuery({
      query: `SELECT id, thing_id, label FROM thing_lines
              WHERE thing_id IN (${parentIds.map(() => '?').join(',')})`,
      values: parentIds,
    })
  : [];
if (lines.error) throw lines.error;

const byParent = new Map();
lines.forEach((line) => {
  const list = byParent.get(line.thing_id) || [];
  list.push(camelCaseKeys({ ...line }));
  byParent.set(line.thing_id, list);
});
return parents.map((p) => ({ ...p, lines: byParent.get(p.id) || [] }));
```

## Shield rule

`src/configs/shield.js`, placed beside the area's other fields.

```js
thingUpdate: isAuthenticated,
thingApprove: chain(isAuthenticated, requiresPermission('web.things.approve')),
```

## Migration

Conventions from `db/migrations/20260922100200_subcontract_package_bids.sql` and
`20260723060906_hrm_hr_admin_tab_permissions.sql`.

```sql
-- migrate:up
CREATE TABLE `thing_lines` (
  `id` BIGINT(20) NOT NULL AUTO_INCREMENT,
  `thing_id` BIGINT(20) NOT NULL,
  `label` VARCHAR(255) NOT NULL,
  `amount_pence` INT NOT NULL DEFAULT 0,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_by` BIGINT(20) NULL,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `updated_by` BIGINT(20) NULL,
  PRIMARY KEY (`id`),
  KEY `idx_thing_lines_thing_id` (`thing_id`),
  CONSTRAINT `fk_thing_lines_thing_id` FOREIGN KEY (`thing_id`)
    REFERENCES `things` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci;

INSERT INTO permissions (type, name, label, action, is_active)
VALUES ('web', 'things', 'Things', 'approve', 1);

-- migrate:down
DELETE FROM permissions WHERE type = 'web' AND name = 'things' AND action = 'approve';
DROP TABLE IF EXISTS `thing_lines`;
```

## Queue with retries

From `src/utils/tender-notifications/queue.js` and `worker.js:82-89`.

```js
const Queue = require('bull');

const thingQueue = new Queue('thingExport', {
  redis: { host: process.env.REDIS_HOST || '127.0.0.1', port: 6379 },
  defaultJobOptions: {
    attempts: 4,
    backoff: { type: 'exponential', delay: 30000 },
    removeOnComplete: 1000,
    removeOnFail: 5000,
  },
});

// Job data holds ids only. The handler re-reads the row, so a retry is safe.
thingQueue.process(async (job) => {
  const finalAttempt = job.attemptsMade + 1 >= (job.opts.attempts || 1);
  try {
    await exportThing(job.data.thingId);
  } catch (error) {
    await markExport(job.data.thingId, finalAttempt ? 'Failed' : 'Pending', error.message);
    throw error;
  }
});
```
