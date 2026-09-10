#!/usr/bin/env bash
# Is the ticket's working base still current, and is the graph it will be reasoned from
# built from the code that is actually there?
#
# Two staleness risks are answered here, both of them silent failures otherwise:
#   1. the base branch moved after the worktree was cut, so "current behaviour" read at
#      cut time is no longer current behaviour;
#   2. the graphify map was built from the *default* branch of the *main* checkout, while
#      the work happens on a different branch — querying it then returns confident answers
#      about code the target branch does not contain.
#
#   ticket-freshness.sh check <KEY> [repo]        verdict per repo, no rebuild
#   ticket-freshness.sh graph <KEY> <repo>        build/refresh the worktree's own graph
#   ticket-freshness.sh sync  <KEY> <repo>        fast-forward the worktree onto its base
#
# The ticket half of staleness (the Jira issue changing under the work) is not git's to
# answer — the workflow re-reads the issue and compares the fingerprint in the sidecar.
#
# Exit: 0 fresh | 1 usage/failure | 3 stale (base moved, or graph does not match HEAD)

set -uo pipefail
HOOKS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HOOKS/../.." && pwd)"
WORK="$ROOT/.work"
MANIFEST="$ROOT/.claude/lodestar.manifest.json"
REPOS="fk-admin-panel-be fk-admin-panel-fe fk-mobile"

die() { echo "$1" >&2; exit 1; }

manifest_sha() { # manifest_sha <repo> -> lastMappedSha recorded for that repo
  python3 - "$MANIFEST" "$1" <<'PY' 2>/dev/null
import json,sys
try:
    m=json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
for r in m.get("repos",[]):
    if r.get("name")==sys.argv[2]:
        print((r.get("mapping") or {}).get("lastMappedSha") or "")
        break
PY
}

check_one() {
  local key="$1" repo="$2" wt="$WORK/$1/$2" rc=0
  [ -d "$wt" ] || { echo "- $repo: no worktree — nothing to check"; return 0; }
  local BASE_REF="" BASE_SHA="" BRANCH=""
  # shellcheck disable=SC1090
  [ -f "$WORK/$key/meta/$repo.env" ] && . "$WORK/$key/meta/$repo.env"
  git -C "$wt" fetch --prune --quiet origin 2>/dev/null

  local now head behind ahead
  now=$(git -C "$wt" rev-parse --short "$BASE_REF" 2>/dev/null)
  head=$(git -C "$wt" rev-parse --short HEAD)
  read -r behind ahead <<<"$(git -C "$wt" rev-list --left-right --count "$BASE_REF...HEAD" 2>/dev/null || echo '? ?')"

  echo "- $repo"
  echo "    branch:   $BRANCH @ $head (+$ahead ahead / -$behind behind $BASE_REF)"
  if [ "$now" != "$BASE_SHA" ]; then
    echo "    base:     STALE — $BASE_REF was $BASE_SHA at cut, is $now now ($behind commit(s) behind)"
    echo "              -> ticket-freshness.sh sync $key $repo, or re-read current behaviour at $now"
    rc=3
  else
    echo "    base:     fresh — $BASE_REF still $BASE_SHA"
  fi

  # Graph: which commit was it built from, and does that match what is checked out here?
  local gsha="" gfile="$wt/graphify-out/graph.json"
  [ -f "$WORK/$key/meta/$repo.graph" ] && gsha=$(sed -n 's/^GRAPH_SHA=//p' "$WORK/$key/meta/$repo.graph")
  if [ ! -f "$gfile" ]; then
    echo "    graph:    NONE in the worktree — queries would fall back to the workspace map,"
    echo "              which was built from ${repo}'s default branch, not this one."
    echo "              -> ticket-freshness.sh graph $key $repo"
    rc=3
  elif [ "$gsha" != "$(git -C "$wt" rev-parse HEAD)" ]; then
    echo "    graph:    STALE — built at ${gsha:0:7}, worktree is at $head"
    echo "              -> ticket-freshness.sh graph $key $repo"
    rc=3
  else
    echo "    graph:    fresh — built from $head, in the worktree"
  fi

  # The workspace-level map is a separate artefact with its own drift; say so, because a
  # stale one there is what makes docs/<repo>/architecture/graph.json untrustworthy.
  local msha main_head
  msha=$(manifest_sha "$repo"); main_head=$(git -C "$ROOT/$repo" rev-parse HEAD 2>/dev/null)
  if [ -n "$msha" ] && [ -n "$main_head" ] && [ "$msha" != "$main_head" ]; then
    echo "    docs map: drifted — docs/$repo/architecture built at ${msha:0:7}, $repo checkout is at ${main_head:0:7} (/lodestar-refresh)"
  fi
  return $rc
}

cmd_check() {
  local key="${1:-}"; [ -n "$key" ] || die "usage: check <KEY> [repo]"
  [ -d "$WORK/$key" ] || die "no workspace at .work/$key"
  echo "## Freshness: $key"
  local rc=0
  if [ -n "${2:-}" ]; then check_one "$key" "$2" || rc=3
  else for r in $REPOS; do [ -d "$WORK/$key/$r" ] && { check_one "$key" "$r" || rc=3; }; done; fi
  if [ "$rc" = "3" ]; then echo "verdict: STALE — resolve the items above before implementing or reviewing."
  else echo "verdict: FRESH"; fi
  exit $rc
}

cmd_graph() {
  local key="${1:-}" repo="${2:-}"
  [ -n "$key" ] && [ -n "$repo" ] || die "usage: graph <KEY> <repo>"
  local wt="$WORK/$key/$repo"; [ -d "$wt" ] || die "no worktree at .work/$key/$repo"
  command -v graphify >/dev/null || die "graphify CLI not installed — say so; do not hand-write a graph."
  local head; head=$(git -C "$wt" rev-parse HEAD)
  mkdir -p "$WORK/$key/meta"

  # Cheap path: the workspace map already describes exactly this commit.
  local msha; msha=$(manifest_sha "$repo")
  if [ "$msha" = "$head" ] && [ -f "$ROOT/docs/$repo/architecture/graph.json" ]; then
    mkdir -p "$wt/graphify-out"
    cp "$ROOT/docs/$repo/architecture/graph.json" "$wt/graphify-out/graph.json"
    { echo "GRAPH_SHA=$head"; echo "GRAPH_SOURCE=docs-map-copy"; } > "$WORK/$key/meta/$repo.graph"
    echo "graph: reused docs/$repo/architecture/graph.json — built from this exact commit ($(git -C "$wt" rev-parse --short HEAD))"
    exit 0
  fi

  echo "graph: extracting $repo at $(git -C "$wt" rev-parse --short HEAD) (code-only, no LLM backend configured)…"
  if graphify extract "$wt" --force --code-only >"$WORK/$key/meta/$repo.graph.log" 2>&1; then
    { echo "GRAPH_SHA=$head"; echo "GRAPH_SOURCE=worktree-extract"; } > "$WORK/$key/meta/$repo.graph"
    echo "graph: built at .work/$key/$repo/graphify-out/graph.json"
    grep -iE 'nodes|edges|communities' "$WORK/$key/meta/$repo.graph.log" | tail -3
    echo "query it with: graphify query \"<question>\" --graph .work/$key/$repo/graphify-out/graph.json"
  else
    echo "graph: extraction FAILED — see .work/$key/meta/$repo.graph.log (tail below)"
    tail -5 "$WORK/$key/meta/$repo.graph.log"
    echo "Read the source instead; do not query the workspace map as if it described this branch."
    exit 1
  fi
}

cmd_sync() {
  local key="${1:-}" repo="${2:-}"
  [ -n "$key" ] && [ -n "$repo" ] || die "usage: sync <KEY> <repo>"
  local wt="$WORK/$key/$repo"; [ -d "$wt" ] || die "no worktree at .work/$key/$repo"
  local BASE_REF=""
  # shellcheck disable=SC1090
  . "$WORK/$key/meta/$repo.env" 2>/dev/null || true
  [ -n "$BASE_REF" ] || die "no recorded base for $repo — was it prepared by ticket-worktree.sh?"
  [ -z "$(git -C "$wt" status --porcelain)" ] || die "worktree has uncommitted changes — commit them before rebasing."
  git -C "$wt" fetch --prune --quiet origin || die "fetch failed"
  local new; new=$(git -C "$wt" rev-parse --short "$BASE_REF")
  if git -C "$wt" rebase "$BASE_REF" >/dev/null 2>&1; then
    sed -i "s/^BASE_SHA=.*/BASE_SHA=$new/" "$WORK/$key/meta/$repo.env"
    echo "sync: $repo rebased onto $BASE_REF @ $new — rebuild the graph (graph $key $repo) and re-run validation."
  else
    git -C "$wt" rebase --abort >/dev/null 2>&1
    echo "sync: REBASE CONFLICTS onto $BASE_REF @ $new — aborted, worktree untouched."
    echo "This is a stop condition: the base changed under the work. Report it and ask."
    exit 1
  fi
}

case "${1:-}" in
  check) shift; cmd_check "$@" ;;
  graph) shift; cmd_graph "$@" ;;
  sync)  shift; cmd_sync  "$@" ;;
  *) die "usage: ticket-freshness.sh {check|graph|sync} <KEY> [repo]" ;;
esac
