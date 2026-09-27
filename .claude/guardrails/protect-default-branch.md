---
name: protect-default-branch
enabled: true
event: bash
pattern: '(^|[\s;&|(])git(\s+-{1,2}[A-Za-z][A-Za-z-]*(=\S+)?(\s+[^\s-]\S*)?)*\s+push\b[^|;&]*(\s-[a-zA-Z]*f[a-zA-Z]*(\s|$)|--force(?![-\w])|\s\+\S|\s(\S*:)?(refs/heads/)?(master|main)(\s|$))'
severity: block
stacks: [all]
match: argv
surface: agent
---

This push would rewrite shared history or land straight on `master`/`main`. Both are blocked:

- **Force push** (`-f`, `--force`, or a `+branch` refspec) overwrites remote history and can erase other people's commits. To overwrite your OWN feature branch after a rebase, use `git push --force-with-lease`.
- **Push to `master` or `main`** (`push origin master`, `push origin HEAD:master`) skips review. Push your feature branch and open a PR into `staging` with `/create-pr <KEY>`. `master` is a release decision for the user, not a push.

---

**What it matches.** A `git … push` (git's global options such as `-C <dir>` allowed in between) that has, in the same command segment:

- a force flag: `-f`, a combined short flag holding `f` (`-uf`), `--force` (but not `--force-with-lease`), or a `+refspec`;
- or a destination of `master`/`main`: a bare word, `<src>:master`, `:master` (delete), or `refs/heads/master`. A branch that only *contains* the word (`feat/main-menu`) does not match.

It does not try to resolve an implicit destination (`git push` with no refspec while tracking `master`). [[block-commit-to-default-branch]] covers pushing while you stand on the default branch. `match: argv` tests unquoted words only, so an echoed mention does not block, and a quoted refspec (`"HEAD:master"`) is not seen.

**Surface: `agent` only.** The git-layer twin would be a `pre-push` hook. Server-side branch protection in Bitbucket is the real enforcement for everyone.
