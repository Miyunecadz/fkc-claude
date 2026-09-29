#!/usr/bin/env bash
# SessionStart hook: name the queryable architecture maps once, with freshness, so a
# fresh session reaches for them instead of grepping source. The "why never --graph"
# reasoning lives in CLAUDE.md; this only states the usage.
set -uo pipefail
HOOKS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The claude-cli labelling pass of a refresh starts a session too; stay quiet there.
[ -n "${GRAPH_REFRESH_ACTIVE:-}" ] && exit 0

echo "## Architecture maps (Graphify)"
"$HOOKS/graph.sh" status 2>/dev/null | sed -e '1,2d' -e '/^Query without choosing/d' -e '/^Any .stale. above/d' | cat -s
cat <<'TXT'
Use: `.claude/hooks/graph.sh query|affected|explain <path> "<question|symbol>"` or `path <path> "<A>" "<B>"`.
<path> = the repo, worktree or file you work in. Stale maps rebuild on query. Never pass --graph.
The map locates; read `path:line` before asserting behaviour. No map has cross-repo edges.
TXT
# Rebuild stale maps now, off the hook's clock, so the first query finds them current.
status=$("$HOOKS/graph.sh" status 2>/dev/null)
if grep -qE '  (stale|missing) ' <<<"$status"; then
  "$HOOKS/graph.sh" refresh --background
  echo "Stale maps are rebuilding in the background now (a query waits for the rebuild)."
fi
