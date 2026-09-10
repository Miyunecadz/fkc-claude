---
name: architecture-overview
description: Use when you need the big picture of how the repos connect, or to trace a flow across a repo boundary.
stacks: [all]
---

# Architecture overview

Get the whole-system map, or follow one flow from repo to repo.

**Where to look:**

1. `docs/repo-map.md` — the registry of repos and how they relate.
2. `docs/_shared/api-contract.md` — the cross-repo spine.
3. Per-repo structure: **query the map, don't re-read source** — and query it through the
   resolver, which finds the map that matches the tree you are in and refreshes it first:

   ```bash
   .claude/hooks/graph.sh query    <repo-or-worktree-or-file> "<question>"
   .claude/hooks/graph.sh affected <path> "<symbol>"   # what a change to this reaches
   .claude/hooks/graph.sh explain  <path> "<symbol>"
   .claude/hooks/graph.sh status                       # what maps exist, and their freshness
   ```

   Never pass `--graph` yourself and never read `docs/<repo>/architecture/graph.json`
   directly: a ticket worktree under `.work/` has its **own** map on its own branch, and the
   workspace map describes the repo's default branch instead. Re-read source only when the
   map can't answer, and always to confirm a `path:line` before asserting behaviour.

**The one thing to remember:** cross-repo edges are **runtime** (repos talk over the API), not static imports. Graphify only draws static edges, so it will *not* show the connection between repos. The boundary between repos lives in `docs/_shared/api-contract.md` — that is where cross-repo flows are documented, not in any per-repo graph.
