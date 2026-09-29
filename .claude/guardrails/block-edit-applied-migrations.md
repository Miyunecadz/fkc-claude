---
name: block-edit-applied-migrations
enabled: true
event: file
pattern: '(^|/)db/migrations/[^/]+\.sql$'
allow_if_untracked: true
severity: block
stacks: [node-dbmate]
surface: agent
---

This migration is already committed, so treat it as applied. dbmate records applied migrations in `schema_migrations` and will not run an edited one again, so the change never reaches any database that already has it. Do not edit it. Create a NEW migration instead (`dbmate new <name>` in `fk-admin-panel-be`, or copy the timestamped file-name style of the folder) and put the forward and rollback SQL there.

---

Installed from the catalogue's `block-edit-applied-migrations`. The root `CLAUDE.md` promises that applied migrations cannot be edited; before this file, nothing enforced it.

**New migrations are allowed.** `allow_if_untracked: true` skips the rule for a file git does not track yet, so a migration you have just created can be filled in. Once it is committed it is protected. Git-tracked status stands in for "applied": it cannot be checked offline, and anything committed is assumed to have run somewhere. If git cannot answer, the rule blocks, erring toward protection.

**Nested repos resolve correctly.** The engine asks git from the file's own folder (`git ls-files --error-unmatch` run in the nearest existing directory), so a path under `fk-admin-panel-be/` is answered by that repo, and a path under `.work/<KEY>/fk-admin-panel-be/` by that worktree. It is never answered by the root repo, which ignores the three product repos.

**Committed on a ticket branch but not merged?** It is still blocked. Fold the change into a new migration, or ask the user to approve editing it.

**Surface: `agent` only.** The catalogue rule also offers a `commit` surface, but `lodestar-precommit-check.py` is not installed in this workspace, so it is left out rather than promised.
