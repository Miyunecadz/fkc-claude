---
name: block-destructive-sql
enabled: true
event: bash
pattern: '(^|[\s;&|(])(mysql|mariadb)\b[^\n]*\b(drop\s+(table|database|schema)|truncate)\b'
severity: block
stacks: [all]
surface: agent
---

This runs `DROP` or `TRUNCATE` through a database client. That data does not come back. Stop and confirm with the user first. Take a dump before you run it (`mysqldump <db> <table> > /tmp/<table>.sql`), and never run it against a shared database without explicit approval. To change the schema, write a new dbmate migration instead.

---

Sibling of [[block-destructive-commands]]. That rule uses `match: argv`, which skips quoted text, so the SQL inside `mysql -e "…"` was invisible to it. This rule matches the raw command string on purpose. The cost is a rare false positive when a command only mentions `mysql … DROP TABLE` in an argument. That is a fair trade against data loss.

It cannot see SQL fed from a file (`mysql db < drop.sql`) or a heredoc. It is a mistake-catcher, not a sandbox.

**Surface: `agent` only.**
