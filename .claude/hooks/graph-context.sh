#!/usr/bin/env bash
# SessionStart hook: name the queryable architecture maps once, with freshness, so a
# fresh session reaches for them instead of grepping source. The "why never --graph"
# reasoning lives in CLAUDE.md; this only states the usage.
set -uo pipefail
HOOKS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "## Architecture maps (Graphify)"
"$HOOKS/graph.sh" status 2>/dev/null | sed -e '1,2d' -e '/^Query without choosing/d' -e '/^Any .stale. above/d' | cat -s
cat <<'TXT'
Use: `.claude/hooks/graph.sh query|affected|explain <path> "<question|symbol>"` or `path <path> "<A>" "<B>"`.
<path> = the repo, worktree or file you work in. Stale maps rebuild on query. Never pass --graph.
The map locates; read `path:line` before asserting behaviour. No map has cross-repo edges.
TXT
