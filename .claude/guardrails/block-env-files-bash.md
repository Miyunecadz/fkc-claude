---
name: block-env-files-bash
enabled: true
event: bash
pattern: '((^|[\s;&|(`])(cat|less|more|head|tail|grep|egrep|fgrep|rg|ag|sed|awk|cp|mv|scp|rsync|bat|nl|strings|xxd|hexdump|od|base64|tac|sort|uniq|cut|diff|vi|vim|nano|code|open|python3?|node)(?=\s)[^;&|\n]*?[\s'"=/:<]|<\s*['"]?(\S*/)?)\.env(rc)?(\.[\w-]+)*(?<!\.example)(?<!\.sample)(?<!\.template)(?<!\.dist)(?<!\.defaults)(?=$|[\s'";&|)])'
severity: block
stacks: [all]
surface: agent
---

This shell command reads or copies a real `.env` file (`.env`, `.env.local`, `.env.staging`, `.envrc` and so on). Those hold live credentials and must not enter the conversation. Use the committed template instead (`.env.example`, `.env.*.example`, `.env.sample`) to learn which variables exist. If you need to know whether a value is set, ask the user.

---

Sibling of [[block-env-files]]. That rule stops `Edit`/`Write`, and `permissions.deny` stops the `Read` tool, but neither sees `cat fk-admin-panel-be/.env` run through Bash. This rule closes that gap.

**What it matches.** A reading or copying tool (`cat`, `grep`, `head`, `tail`, `less`, `sed`, `awk`, `cp`, `mv`, `diff`, editors, `python`, `node` and similar), then a real env file name later in the same command segment. Input redirection (`< .env`) is caught too. A name counts as real when it is `.env` or `.envrc`, or `.env.<tier>` that does not end in `.example`, `.sample`, `.template`, `.dist` or `.defaults`. So `.env.local.example` is allowed and `.env.staging` is blocked.

It matches the **raw command string**, not argv, because paths are often quoted (`cat "$BE/.env"`). The cost is a rare false positive when a quoted argument only mentions `cat .env`. Listing (`ls -la .env`) and existence checks (`test -f .env`) are not reading, so they pass. So does `source .env`, which loads values without printing them.

It cannot catch a read that never names the file (`grep -r DB_PASS .`). It is a mistake-catcher, not a sandbox.

**Surface: `agent` only.**
