#!/usr/bin/env bash
# SessionStart hook: tell the session, once, that queryable architecture maps
# exist here, where they are, and whether they currently describe the code.
#
# Without this the maps are invisible: docs/<repo>/architecture/graph.json is a
# 1.8MB artefact nothing in a fresh session knows how to reach, so the session
# greps source instead and the map rots unused. Naming it here — with its
# freshness — is what turns it into something reached for rather than a file
# that happens to be on disk.
set -uo pipefail
HOOKS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "## Architecture maps (Graphify) — queryable, do not re-read source first"
echo
"$HOOKS/graph.sh" status 2>/dev/null | sed '1,2d'
cat <<'TXT'

**Use it like this**, from anywhere in the workspace:

```bash
.claude/hooks/graph.sh query    <path-you-are-working-in> "<question>"
.claude/hooks/graph.sh affected <path> "<symbol>"      # what breaks if this changes
.claude/hooks/graph.sh explain  <path> "<symbol>"      # node + neighbours
.claude/hooks/graph.sh path     <path> "<A>" "<B>"     # how A reaches B
```

`<path>` is any repo, ticket worktree, or file inside one. Never pass `--graph`
by hand: this workspace holds one map per repo **plus one per ticket worktree**,
they describe different commits, and picking the wrong one returns a confident,
well-formatted answer about code the current branch does not contain. `graph.sh`
resolves the right map from the path, rebuilds it if the code moved (including
uncommitted edits, ~3s), then queries it.

The map locates; the file confirms. Read `path:line` before asserting behaviour.
Cross-repo edges do not exist in any per-repo map — that boundary is
`docs/_shared/api-contract.md`.
TXT
