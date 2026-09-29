---
name: block-destructive-commands
enabled: true
event: bash
pattern: '((^|[\s;&|(])rm(?=\s)(?=[^;&|]*\s(-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)(\s|$))(?=[^;&|]*\s(-[a-zA-Z]*f[a-zA-Z]*|--force)(\s|$))|(^|[\s;&|(])git(\s+-{1,2}[A-Za-z][A-Za-z-]*(=\S+)?(\s+[^\s-]\S*)?)*\s+reset\b[^;&|]*\s--hard\b|(^|[\s;&|(])git(\s+-{1,2}[A-Za-z][A-Za-z-]*(=\S+)?(\s+[^\s-]\S*)?)*\s+clean\b[^;&|]*\s(-[a-zA-Z]*f[a-zA-Z]*|--force)(\s|$)|(^|[\s;&|(])git(\s+-{1,2}[A-Za-z][A-Za-z-]*(=\S+)?(\s+[^\s-]\S*)?)*\s+(checkout|restore)\s+(--\s+)?\./?(\s|$)|(^|[\s;&|(])git(\s+-{1,2}[A-Za-z][A-Za-z-]*(=\S+)?(\s+[^\s-]\S*)?)*\s+branch\b[^;&|]*\s(-[a-zA-Z]*D[a-zA-Z]*|--delete\s+--force|--force\s+--delete)(\s|$)|(^|[\s;&|(])git(\s+-{1,2}[A-Za-z][A-Za-z-]*(=\S+)?(\s+[^\s-]\S*)?)*\s+worktree\s+remove\b[^;&|]*\s(-f|--force)(\s|$)|(^|[\s;&|(])find\s[^;&|]*\s-delete(\s|$)|(^|[\s;&|(])dbmate\b[^;&|]*\sdrop(\s|$)|\bdd\s+if=|\bmkfs\b|\bshred\b|\btruncate\s+-s|(?i:\bdrop\s+(database|table|schema)\b)|>\s*/dev/(sd|nvme|disk))'
severity: block
stacks: [all]
match: argv
ignore_case: false
allow_paths: ['^/tmp/', '^/var/tmp/', '^/var/folders/']
surface: agent
---

This command destroys work with no undo (`rm -rf`, `git reset --hard`, `git clean -f`, `git checkout/restore .`, `git branch -D`, `git worktree remove --force`, `find -delete`, `dbmate drop`, `dd`, `mkfs`, `shred`, `truncate`, `DROP DATABASE/TABLE`, writing to a raw device). Stop and confirm with the user before you run it. Try a recoverable option first:

- Discarding changes? `git stash` instead of `reset --hard` or `clean`. A stash can be got back.
- Removing tracked files? `git rm` (staged, reversible) instead of `rm -rf`.
- Deleting a folder of real work? List it first and confirm the exact path.
- Deleting a branch? `git branch -d` refuses when the branch is not merged. That is the check you want.
- Removing a ticket worktree? Use `.claude/hooks/ticket-worktree.sh`, which keeps the branch.
- Dropping database objects? Take a dump first. Never run it against a shared database without approval.

---

This catches mistakes, not a determined adversary. It is a stop-and-redirect, not a sandbox.

**What it matches.** `match: argv` tests the command's unquoted words, so a destructive string that runs nothing (inside a JSON argument, an `echo`, a commit message) does not trip it. Quoted payloads for a nested shell (`bash -c "…"`, `eval "…"`) are still tested. Git subcommands are matched after git's own global options, so `git -C <dir> reset --hard` is caught like a bare `git reset --hard`.

**`rm` needs both recursive and force** (`-rf`, `-fr`, `-r -f`, `--recursive --force`). A lone `rm -f notes.txt` or `rm -r dir` is allowed. The first removes only the named file; the second still prompts on protected files.

**Case matters** (`ignore_case: false`), so `git branch -d` (safe) is not mistaken for `-D`. SQL keywords are matched in any case.

**Temp paths are exempt.** `allow_paths` skips a delete when every operand is an absolute path under `/tmp`, `/var/tmp` or `/var/folders`. A compound command (`&&`, `;`, `|`, `$(…)`) never gets the exemption. So `tmp=$(mktemp -d); rm -rf "$tmp"` still blocks: the engine cannot expand a variable, and a quoted operand is invisible to argv matching. Run it as `rm -rf /tmp/<exact path>` instead.

**SQL sent through a client** (`mysql -e "DROP TABLE x"`) is quoted, so this rule cannot see it. [[block-destructive-sql]] covers that case.

**Surface: `agent` only.** It guards shell commands, not commit contents.
