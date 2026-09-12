---
name: block-commit-to-default-branch
enabled: true
event: bash
pattern: '(^|[;&|]\s*)git(\s+-{1,2}[A-Za-z][A-Za-z-]*(=\S+)?(\s+[^\s-]\S*)?)*\s+(commit|push)\b'
severity: block
stacks: [all]
only_on_default_branch: true
match: argv
surface: both
commit_check: default-branch
---

You are on the repository's **default branch** (`main`/`master`), so this commit or push would land straight on trunk — bypassing review, CI, and any branch protection the team relies on. Create a feature branch first and commit there:

```
git switch -c feat/<short-name>
```

Already staged? The branch switch carries staged changes with it — `git switch -c` then commit as normal. Already committed to the default branch by accident? Move the commit onto a branch before pushing: `git branch feat/<name> && git reset --hard @~1` (from the default branch), then `git switch feat/<name>`.

---

How this knows: `only_on_default_branch: true` asks the engine for the current branch (`git symbolic-ref --short HEAD`) and the repo's default (`origin/HEAD`, falling back to `init.defaultBranch`, then an existing local `main`/`master`) — **in the directory the command actually targets**. A `git -C <path> commit` is asked about `<path>`, not about the invocation cwd; only a command with no `-C` (or `--git-dir`/`--work-tree`) is asked about the cwd. That distinction is the whole rule in this workspace: the root is itself a repo on `main` while the delivery workflow commits inside `.work/<KEY>/<repo>` on a feature branch, and resolving against the cwd denied every one of those commits. A command naming several repos stays protective — one of them on its default branch is enough to fire. The rule fires **only** when both branches are known and equal — a detached HEAD, a shallow checkout with no `origin/HEAD`, or no git at all leaves it silent rather than blocking legitimate work, so treat it as a mistake-catcher and not a substitute for server-side branch protection. Sibling of [[protect-default-branch]], which covers force-push on any branch.

**Surface: `both`.** The commit-time check (`commit_check: default-branch`) is the stronger half — it stops a direct trunk commit from *anyone*, not just Claude, which is what this rule was always trying to do. Still not a substitute for server-side branch protection, which is the only version a determined committer cannot bypass with `--no-verify`.
