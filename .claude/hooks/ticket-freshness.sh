#!/usr/bin/env bash
# Is the ticket's base still current, and does the graph describe the code that is there?
#
# Two separate questions, with separate answers:
#   1. base  — did the base branch move after the ticket branch was cut? If so, what was
#              read as "current behaviour" is no longer current. This is a stop.
#   2. graph — does the map that answers queries for this tree describe this tree? Any
#              edit makes it drift, and graph.sh rebuilds it on the next query. This is
#              never a reason to stop, and never means the base is stale.
#
#   ticket-freshness.sh check <KEY> [repo]    verdict per repo, no rebuild
#   ticket-freshness.sh graph <KEY> <repo>    build or refresh the tree's map, and label it
#   ticket-freshness.sh sync  <KEY> <repo>    rebase the ticket branch onto its moved base
#
# The Jira half of freshness is not git's to answer: the workflow re-reads the issue and
# compares 'updated' and 'status' with the sidecar's jira: line (FRESHNESS.md §1).
#
# Exit (check):
#   0 FRESH          base unmoved, graph current
#   3 STALE BASE     the base moved since the cut — stop
#   4 GRAPH DRIFT    base fresh; the map is behind the tree (self-heals on next query)
#   5 UNKNOWN        nothing could be checked: not prepared, offline, or branch not checked out
#   1 usage / failure
# When repos disagree the worst wins, in the order 3, 5, 4, 0.
# Exit (graph): 0 built and labelled | 4 built but not labelled | 1 failed
# Exit (sync):  0 rebased | 1 refused or conflicts | 5 offline
#
# TICKET_WORK_DIR overrides .work/ (tests only).

set -uo pipefail
HOOKS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HOOKS/../.." && pwd)"
WORK="${TICKET_WORK_DIR:-$ROOT/.work}"
REPOS="fk-admin-panel-be fk-admin-panel-fe fk-mobile"

die() { echo "$1" >&2; exit "${2:-1}"; }

# Where the ticket's code lives is ticket-worktree.sh's answer, not ours — in-place mode
# puts it in the repo's own checkout and leaves no directory under .work/<KEY>/.
tree_of()  { "$HOOKS/ticket-worktree.sh" tree "$1" "$2" 2>/dev/null; }
mode_of()  { sed -n 's/^MODE=//p' "$WORK/$1/meta/$2.env" 2>/dev/null; }
repos_in_play() { local r; for r in $REPOS; do [ -f "$WORK/$1/meta/$r.env" ] && echo "$r"; done; }

# Recorded shas are full length now; older meta files hold 7-char ones. Compare by prefix.
sha_eq() {
  local a="$1" b="$2"
  [ -n "$a" ] && [ -n "$b" ] || return 1
  case "$a" in "$b"*) return 0 ;; esac
  case "$b" in "$a"*) return 0 ;; esac
  return 1
}

# git status, minus the node_modules and .env* symlinks prepare itself made in a worktree.
# git does not ignore a symlink with a 'node_modules/' rule, so without this every
# worktree reads as dirty.
real_porcelain() {
 git -C "$1" status --porcelain 2>/dev/null | while IFS= read -r l; do
  case "$l" in
   '?? node_modules'|'?? .env'|'?? .env.'*) [ -L "$1/${l#?? }" ] && continue ;;
  esac
  printf '%s\n' "$l"
 done
}

check_one() {
  local key="$1" repo="$2" rc=0 wt; wt=$(tree_of "$1" "$2")
  if [ -z "$wt" ] || [ ! -d "$wt" ]; then
    echo "- $repo: UNKNOWN — not prepared for $key, nothing checked"
    return 5
  fi
  local MODE="worktree" BASE_REF="" BASE_SHA="" BRANCH=""
  # shellcheck disable=SC1090
  [ -f "$WORK/$key/meta/$repo.env" ] && . "$WORK/$key/meta/$repo.env"

  # In-place shares the checkout with the user, so the first question is whether the
  # ticket's branch is even the one checked out. Nothing below means anything otherwise.
  if [ "$MODE" = "in-place" ] && [ "$(git -C "$wt" rev-parse --abbrev-ref HEAD 2>/dev/null)" != "$BRANCH" ]; then
    echo "- $repo (in-place)"
    echo "    branch:   UNKNOWN — $repo is on $(git -C "$wt" rev-parse --abbrev-ref HEAD 2>/dev/null), not $BRANCH"
    echo "              -> ticket-worktree.sh prepare $key $repo ${BASE_REF#origin/} $BRANCH --in-place"
    return 5
  fi

  local head behind ahead now
  head=$(git -C "$wt" rev-parse --short HEAD 2>/dev/null)
  echo "- $repo ($MODE)"

  if ! git -C "$wt" fetch --prune --quiet origin >/dev/null 2>&1; then
    echo "    branch:   $BRANCH @ $head"
    echo "    base:     UNKNOWN (offline) — fetch failed, so $BASE_REF cannot be compared"
    rc=5
  else
    now=$(git -C "$wt" rev-parse "$BASE_REF" 2>/dev/null)
    read -r behind ahead <<<"$(git -C "$wt" rev-list --left-right --count "$BASE_REF...HEAD" 2>/dev/null || echo '? ?')"
    echo "    branch:   $BRANCH @ $head (+$ahead ahead / -$behind behind $BASE_REF)"
    if [ -z "$now" ] || [ -z "$BASE_SHA" ]; then
      echo "    base:     UNKNOWN — cannot resolve $BASE_REF, or no BASE_SHA recorded"
      rc=5
    elif sha_eq "$now" "$BASE_SHA"; then
      echo "    base:     fresh — $BASE_REF still ${BASE_SHA:0:12}"
    else
      echo "    base:     STALE — $BASE_REF was ${BASE_SHA:0:12} at cut, is ${now:0:12} now ($behind commit(s) behind)"
      echo "              -> FRESHNESS.md §2 says what this forces at this stage"
      rc=3
    fi
  fi

  # Graph: graph.sh owns the question for both modes. Its stamp includes uncommitted
  # edits, so any edited tree reads as drift here. That is expected and not a base issue.
  local gstate grc=0
  gstate=$("$HOOKS/graph.sh" resolve "$wt" 2>/dev/null | sed -n 's/^state:[[:space:]]*//p')
  case "${gstate:-unknown}" in
    fresh)   echo "    graph:    fresh — describes $head$(git -C "$wt" status --porcelain -uno 2>/dev/null | grep -q . && echo ' + local edits')" ;;
    stale)   echo "    graph:    stale (self-heals on next query)"; grc=4 ;;
    missing) echo "    graph:    none yet (built on first query, or: ticket-freshness.sh graph $key $repo)"; grc=4 ;;
    *)       echo "    graph:    UNKNOWN — graph.sh could not resolve a map for $wt"; grc=4 ;;
  esac
  [ "$rc" = 0 ] && rc=$grc
  return $rc
}

cmd_check() {
  local key="${1:-}"; [ -n "$key" ] || die "usage: check <KEY> [repo]"
  [ -d "$WORK/$key" ] || die "no workspace at .work/$key"
  echo "## Freshness: $key"
  local targets="${2:-}" r c n=0 s3=0 s5=0 s4=0
  [ -n "$targets" ] || targets=$(repos_in_play "$key")
  for r in $targets; do
    n=$((n+1))
    check_one "$key" "$r"; c=$?
    case "$c" in 3) s3=1 ;; 5) s5=1 ;; 4) s4=1 ;; esac
  done
  if [ "$n" = 0 ]; then
    echo "verdict: UNKNOWN: nothing checked — no repo is prepared for $key"; exit 5
  elif [ "$s3" = 1 ]; then
    echo "verdict: STALE BASE — a base moved; see FRESHNESS.md §2"; exit 3
  elif [ "$s5" = 1 ]; then
    echo "verdict: UNKNOWN — see the lines above; do not treat this as fresh"; exit 5
  elif [ "$s4" = 1 ]; then
    echo "verdict: FRESH BASE, graph drift only — continue; the next query rebuilds the map"; exit 4
  fi
  echo "verdict: FRESH"
  exit 0
}

cmd_graph() {
  local key="${1:-}" repo="${2:-}"
  [ -n "$key" ] && [ -n "$repo" ] || die "usage: graph <KEY> <repo>"
  local wt; wt=$(tree_of "$key" "$repo")
  [ -n "$wt" ] && [ -d "$wt" ] || die "$repo is not prepared for $key — run ticket-worktree.sh prepare first."

  # graph.sh owns building, reuse of the repo's own map, the stamp and PYTHONHASHSEED.
  # In-place, the tree is the repo checkout and this is simply its own map.
  "$HOOKS/graph.sh" ensure "$wt" || die "graph: build FAILED for $wt — read the source instead; do not query a map that describes another commit."

  # Names come from graphify's labelling pass (claude CLI backend). It can fail or be
  # unavailable; the map then answers with bare community numbers.
  local labels="$wt/graphify-out/.graphify_labels.json"
  [ -f "$labels" ] || "$HOOKS/graph.sh" label "$wt" --full >/dev/null 2>&1
  echo "query it with: $HOOKS/graph.sh query \"$wt\" \"<question>\""
  if [ ! -f "$labels" ]; then
    echo "graph: built but NOT LABELLED — community names are missing; treat answers as structural only"
    exit 4
  fi
  echo "graph: labelled"
}

cmd_sync() {
  local key="${1:-}" repo="${2:-}"
  [ -n "$key" ] && [ -n "$repo" ] || die "usage: sync <KEY> <repo>"
  local wt; wt=$(tree_of "$key" "$repo")
  [ -n "$wt" ] && [ -d "$wt" ] || die "$repo is not prepared for $key."
  local BASE_REF="" BRANCH="" MODE=""
  # shellcheck disable=SC1090
  . "$WORK/$key/meta/$repo.env" 2>/dev/null || true
  [ -n "$BASE_REF" ] || die "no recorded base for $repo — was it prepared by ticket-worktree.sh?"
  [ "$(git -C "$wt" rev-parse --abbrev-ref HEAD 2>/dev/null)" = "$BRANCH" ] \
    || die "$wt is not on $BRANCH — refusing to rebase whatever is checked out there."
  # A dirty tree is refused, not stashed. At /implement-review the tree nearly always holds
  # the dev's edits, so a moved base there is a stop to report, not a sync to run.
  [ -z "$(real_porcelain "$wt")" ] \
    || die "sync refused: $wt has uncommitted changes. Commit them first, or report the moved base and ask."
  git -C "$wt" fetch --prune --quiet origin >/dev/null 2>&1 || die "sync: UNKNOWN (offline) — fetch failed; nothing changed." 5
  local new; new=$(git -C "$wt" rev-parse "$BASE_REF")
  if git -C "$wt" rebase "$BASE_REF" >/dev/null 2>&1; then
    sed -i "s/^BASE_SHA=.*/BASE_SHA=$new/" "$WORK/$key/meta/$repo.env"
    echo "sync: $repo rebased onto $BASE_REF @ ${new:0:12} — re-run validation; the next graph query rebuilds the map."
  else
    git -C "$wt" rebase --abort >/dev/null 2>&1
    echo "sync: REBASE CONFLICTS onto $BASE_REF @ ${new:0:12} — aborted, tree untouched."
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
