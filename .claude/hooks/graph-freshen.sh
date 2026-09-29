#!/usr/bin/env bash
# UserPromptSubmit: when the prompt asks for code work (implement, investigate, debug,
# fix, trace, a ticket key...), rebuild any stale map in the background and point the
# agent at the map before it greps. Without this a map only rebuilt when the agent
# happened to run graph.sh query, so a branch switch left it stale all session.
set -uo pipefail
HOOKS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -n "${GRAPH_REFRESH_ACTIVE:-}" ] && exit 0

prompt=$(python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("prompt",""))
except Exception: pass' 2>/dev/null)

grep -qiE '\b(implement|investigat|debug|diagnos|fix|bug|trace|refactor|where (is|does)|how does|affect|impact|review|analy[sz]|ticket|raise (this|it|a|an)|write (this|it) up|log (this|it|a|an)|story|requirement|subc-[0-9]+|fkc-[0-9]+)|/(implement-ticket|implement-review|create-ticket)' <<<"$prompt" || exit 0

stale=$("$HOOKS/graph.sh" status 2>/dev/null | grep -E '  (stale|missing) ' | sed -E 's/^- +//; s/ +/ /g' | cut -d' ' -f1-3)
if [ -n "$stale" ]; then
  "$HOOKS/graph.sh" refresh --background
  echo "Architecture maps rebuilding in the background (was stale: $(echo "$stale" | paste -sd ';' -))."
fi
# Ticket commands delegate all code reading to their agents (ticket-delivery §5), which
# query the map themselves; a "query it yourself" hint would pull the main thread off that.
grep -qiE '^\s*/(implement-ticket|implement-review|create-pr|create-ticket)\b' <<<"$prompt" && exit 0
echo "Code task: locate with \`.claude/hooks/graph.sh query <repo-or-worktree> \"<question>\"\` before grep; confirm at path:line."
exit 0
