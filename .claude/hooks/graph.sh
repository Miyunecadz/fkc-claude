#!/usr/bin/env bash
# Worktree-aware access to this workspace's Graphify maps.
#
# The problem this solves: there is not one graph in this workspace, there are
# 1 + N per repo — the workspace map in <repo>/graphify-out/ (whatever branch that
# checkout is on), plus one per ticket worktree under .work/<KEY>/<repo>/graphify-out/.
# They describe
# DIFFERENT commits. Passing --graph by hand is how an agent gets a confident,
# well-formatted answer about code the branch it is working on does not contain.
#
# So: never pass --graph. Pass a path you are working in, and let this resolve
# which map describes it, rebuild it if the code has moved under it, and then
# query it.
#
#   graph.sh status                          inventory: every repo + every worktree
#   graph.sh resolve <path>                  which map describes <path>, and is it current
#   graph.sh ensure  <path>                  rebuild that map if the code moved
#   graph.sh label   <path> [--full]         (re)name its communities
#   graph.sh query   <path> "<question>" [..] ensure, then BFS traversal
#   graph.sh affected <path> "<node>" [..]   ensure, then reverse traversal
#   graph.sh explain  <path> "<node>"        ensure, then neighbourhood explanation
#   graph.sh path     <path> "<A>" "<B>"     ensure, then shortest path
#
# <path> is anything inside a repo or a worktree: a repo dir, a worktree dir, a
# source file. "." works when the shell is already in the right place.
#
# Staleness is measured against HEAD *and* the dirty working tree, because a
# graph built before an uncommitted edit is exactly as wrong as one built on
# another branch. Rebuilds are incremental (~2-4s on this workspace), so ensure
# runs on every query rather than being something to remember.
#
# Freshness lives in a stamp beside each map (<repo>/graphify-out/.graph-stamp, or
# .work/<KEY>/meta/<repo>.graph). The tracked lodestar manifest is only read, as a
# fallback for maps built before stamps existed — never written, so a rebuild does
# not dirty the router repo.
#
# Exit: 0 ok | 1 usage/failure | 2 graphify CLI missing

set -uo pipefail

# networkx louvain iterates string-keyed sets whose order PYTHONHASHSEED randomizes
# per process, so community assignments churn run-to-run and a rebuild of the *same*
# commit produces a different-looking map. Pin it, as graphify's own hooks do, so
# "the graph changed" always means "the code changed".
export PYTHONHASHSEED=0

HOOKS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HOOKS/../.." && pwd)"
WORK="$ROOT/.work"
MANIFEST="$ROOT/.claude/lodestar.manifest.json"
REPOS="fk-admin-panel-be fk-admin-panel-fe fk-mobile"

die() { echo "$1" >&2; exit 1; }
need_cli() { command -v graphify >/dev/null || { echo "graphify CLI not installed — read the source instead; do not hand-write a graph." >&2; exit 2; }; }

# ---------------------------------------------------------------- resolution

# stamp <dir> -> "<head>:<hash of tracked dirty state>"; changes on commit AND on edit
stamp() {
  local d="$1" head dirty
  head=$(git -C "$d" rev-parse HEAD 2>/dev/null || echo none)
  dirty=$(git -C "$d" status --porcelain -uno 2>/dev/null | sha1sum | cut -c1-12)
  echo "$head:$dirty"
}

# primary_sha <repo> -> the commit the workspace map was built from (stamp, else manifest)
primary_sha() {
  local f="$ROOT/$1/graphify-out/.graph-stamp" s=""
  [ -f "$f" ] && s=$(sed -n 's/^GRAPH_SHA=//p' "$f")
  [ -n "$s" ] && echo "$s" || manifest_sha "$1"
}

manifest_sha() {
  python3 - "$MANIFEST" "$1" <<'PY' 2>/dev/null
import json,sys
try: m=json.load(open(sys.argv[1]))
except Exception: sys.exit(0)
for r in m.get("repos",[]):
    if r.get("name")==sys.argv[2]:
        print((r.get("mapping") or {}).get("lastMappedSha") or ""); break
PY
}

# resolve <path> -> sets SCOPE REPO KEY TREE GRAPH STAMPFILE WANT HAVE STATE
resolve() {
  local p _r _rel _s _m
  p=$(cd "${1:-.}" 2>/dev/null && pwd) || p=$(cd "$(dirname "${1:-.}")" && pwd)
  case "$p" in
    "$WORK"/*)
      _rel="${p#"$WORK"/}"
      KEY="${_rel%%/*}"; _rel="${_rel#"$KEY"}"; _rel="${_rel#/}"
      REPO="${_rel%%/*}"
      [ -n "$REPO" ] || die "path is inside .work/$KEY but not inside a repo worktree"
      SCOPE=worktree
      TREE="$WORK/$KEY/$REPO"
      GRAPH="$TREE/graphify-out/graph.json"
      STAMPFILE="$WORK/$KEY/meta/$REPO.graph"
      ;;
    *)
      SCOPE=primary; KEY=""
      REPO=""
      for _r in $REPOS; do case "$p" in "$ROOT/$_r"|"$ROOT/$_r"/*) REPO="$_r";; esac; done
      [ -n "$REPO" ] || die "path is not inside a known repo or worktree: $p"
      TREE="$ROOT/$REPO"
      GRAPH="$TREE/graphify-out/graph.json"
      STAMPFILE="$TREE/graphify-out/.graph-stamp"
      ;;
  esac
  [ -d "$TREE" ] || die "no tree at $TREE"
  WANT=$(stamp "$TREE")
  HAVE=""
  if [ -f "$STAMPFILE" ]; then
    HAVE=$(sed -n 's/^GRAPH_STAMP=//p' "$STAMPFILE")
    # Pre-existing sidecars record only GRAPH_SHA; treat that as a clean-tree stamp.
    [ -n "$HAVE" ] || { _s=$(sed -n 's/^GRAPH_SHA=//p' "$STAMPFILE"); [ -n "$_s" ] && HAVE="$_s:$(printf '' | sha1sum | cut -c1-12)"; }
  fi
  if [ "$SCOPE" = primary ] && [ -z "$HAVE" ]; then
    _m=$(manifest_sha "$REPO")
    [ -n "$_m" ] && HAVE="$_m:$(printf '' | sha1sum | cut -c1-12)"
  fi
  if [ ! -f "$GRAPH" ]; then STATE=missing
  elif [ "$WANT" = "$HAVE" ]; then STATE=fresh
  else STATE=stale; fi
}

# ------------------------------------------------------------------- labelling
# A code-only extract produces communities numbered 0..N and nothing else. `query` reads
# their names from .graphify_labels.json beside the graph, so an unlabelled map answers
# with bare integers and BFS has nothing to anchor a question like "where do subcontract
# order task lines live" to — it matches raw identifiers only and lands in a plausible
# neighbouring region. That is the difference between a worktree map and the workspace
# map, and it is why implementations built from worktree maps drifted off target.
#
# Naming needs an LLM but not an API key: graphify's claude-cli backend shells out to the
# installed claude CLI. Measured on fk-admin-panel-be (2094 nodes, 359 communities):
# ~32s for a full pass, 0.7s for --missing-only when nothing is missing — cheap enough to
# run after every rebuild rather than being something to remember.
label_tree() { # label_tree <tree> <log> [--full]
  local tree="$1" log="$2" full="${3:-}" backend=()
  command -v graphify >/dev/null || return 0
  # A configured key wins; claude-cli is the fallback that needs none. graphify's own
  # auto-detection deliberately never picks claude-cli, so name it explicitly.
  if [ -z "${GEMINI_API_KEY:-}${GOOGLE_API_KEY:-}${ANTHROPIC_API_KEY:-}${OPENAI_API_KEY:-}" ]; then
    command -v claude >/dev/null || {
      echo "graph: NOT LABELLED — no LLM backend and no claude CLI. Community names will be" >&2
      echo "       bare integers; treat query results as structural only." >&2
      return 0
    }
    backend=(--backend=claude-cli)
  fi
  local args=(--missing-only)
  [ "$full" = "--full" ] && args=()
  if graphify label "$tree" "${args[@]}" "${backend[@]}" >>"$log" 2>&1; then
    grep -iE 'communities' "$log" | tail -1
  else
    echo "graph: labelling failed — map is usable but community names are missing (see $log)" >&2
  fi
}

write_stamp() {
  mkdir -p "$(dirname "$STAMPFILE")"
  { echo "GRAPH_SHA=$(git -C "$TREE" rev-parse HEAD 2>/dev/null)"
    echo "GRAPH_STAMP=$(stamp "$TREE")"
    echo "GRAPH_SOURCE=${1:-graph.sh}"
    echo "GRAPH_BUILT_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } > "$STAMPFILE"
}

# ------------------------------------------------------------------ commands

cmd_resolve() {
  resolve "${1:-.}"
  echo "scope:  $SCOPE${KEY:+ (ticket $KEY)}"
  echo "repo:   $REPO"
  echo "tree:   ${TREE#"$ROOT"/}"
  echo "graph:  ${GRAPH#"$ROOT"/}"
  echo "state:  $STATE"
  [ "$STATE" = fresh ] || { echo "want:   $WANT"; echo "have:   ${HAVE:-<none>}"; }
  [ "$STATE" = fresh ] || echo "        -> graph.sh ensure ${1:-.}  (or just query; query ensures first)"
}

cmd_ensure() {
  resolve "${1:-.}"
  [ "$STATE" = fresh ] && { echo "graph: fresh — ${GRAPH#"$ROOT"/} describes $(git -C "$TREE" rev-parse --short HEAD 2>/dev/null)$(git -C "$TREE" status --porcelain -uno 2>/dev/null | grep -q . && echo ' + local edits')"; return 0; }
  need_cli
  local log="${TMPDIR:-/tmp}/graph-ensure-$REPO${KEY:+-$KEY}.log"

  # A worktree whose HEAD is exactly the commit the workspace map was built from
  # can copy it — same content, no extraction. The label/analysis sidecars travel
  # with graph.json or `query` answers with bare community integers.
  local src="$ROOT/$REPO/graphify-out" f
  if [ "$SCOPE" = worktree ] && [ -z "$(git -C "$TREE" status --porcelain -uno 2>/dev/null)" ] \
     && [ "$(primary_sha "$REPO")" = "$(git -C "$TREE" rev-parse HEAD 2>/dev/null)" ] \
     && [ -f "$src/graph.json" ]; then
    mkdir -p "$TREE/graphify-out"
    for f in graph.json GRAPH_REPORT.md .graphify_labels.json .graphify_labels.json.sig .graphify_analysis.json; do
      [ -f "$src/$f" ] && cp "$src/$f" "$TREE/graphify-out/$f"
    done
    write_stamp workspace-map-copy
    echo "graph: reused $REPO/graphify-out/graph.json — built from this exact commit"
    return 0
  fi

  local mode verb
  if [ "$STATE" = missing ]; then mode=extract; verb="extracting"; else mode=update; verb="updating"; fi
  echo "graph: $verb $REPO at $(git -C "$TREE" rev-parse --short HEAD 2>/dev/null)$(git -C "$TREE" status --porcelain -uno 2>/dev/null | grep -q . && echo ' + local edits') (code-only)…"
  local ok=1
  if [ "$mode" = extract ]; then
    graphify extract "$TREE" --force --code-only >"$log" 2>&1 && ok=0
  else
    graphify update "$TREE" --force >"$log" 2>&1 && ok=0
  fi
  if [ "$ok" != 0 ]; then
    echo "graph: rebuild FAILED — $log"; tail -5 "$log"
    echo "Read the source instead. Do NOT query a stale map as if it described this tree."
    return 1
  fi
  # Name the communities before the stamp: a map recorded as current must be a map that
  # can actually answer by name. A fresh extract has no labels at all; an update carries
  # the old ones forward and only needs the communities the new code created.
  label_tree "$TREE" "$log" "$( [ "$mode" = extract ] && echo --full )"

  write_stamp "$SCOPE-$mode"
  grep -iE 'nodes|edges|communities|updated' "$log" | tail -2

  echo "graph: ${GRAPH#"$ROOT"/} now describes this tree"
}

# run <subcommand> <path> <args...>
run_q() {
  local sub="$1"; shift
  local p="${1:-.}"; shift || true
  resolve "$p"
  cmd_ensure "$p" >&2 || return 1
  need_cli
  echo "# $sub against ${GRAPH#"$ROOT"/} ($SCOPE${KEY:+ $KEY} · $REPO · $(git -C "$TREE" rev-parse --short HEAD 2>/dev/null))"
  graphify "$sub" "$@" --graph "$GRAPH"
}

cmd_label() {
  resolve "${1:-.}"
  need_cli
  [ -f "$GRAPH" ] || die "no map at ${GRAPH#"$ROOT"/} yet — graph.sh ensure ${1:-.} first"
  label_tree "$TREE" "${TMPDIR:-/tmp}/graph-label-$REPO${KEY:+-$KEY}.log" "${2:-}"
  echo "graph: ${GRAPH#"$ROOT"/} labelled"
}

cmd_status() {
  echo "## Graphify maps in this workspace"
  echo
  echo "### Workspace maps — <repo>/graphify-out/ (the repo's own checkout)"
  for r in $REPOS; do
    [ -d "$ROOT/$r" ] || continue
    resolve "$ROOT/$r" 2>/dev/null || continue
    printf -- "- %-20s %-8s %s @ %s%s\n" "$r" "$STATE" "$(git -C "$TREE" rev-parse --abbrev-ref HEAD 2>/dev/null)" "$(git -C "$TREE" rev-parse --short HEAD 2>/dev/null)" "$(git -C "$TREE" status --porcelain -uno 2>/dev/null | grep -q . && echo ' +edits')"
  done
  echo
  echo "### Ticket maps — .work/<KEY>/<repo>/graphify-out/ (the ticket's own branch)"
  local any=0
  for d in "$WORK"/*/; do
    [ -d "$d" ] || continue
    local k; k=$(basename "$d")
    for r in $REPOS; do
      [ -d "$d$r" ] || continue
      any=1
      resolve "$d$r" 2>/dev/null || continue
      printf -- "- %-10s %-20s %-8s %s @ %s%s\n" "$k" "$r" "$STATE" "$(git -C "$TREE" rev-parse --abbrev-ref HEAD 2>/dev/null)" "$(git -C "$TREE" rev-parse --short HEAD 2>/dev/null)" "$(git -C "$TREE" status --porcelain -uno 2>/dev/null | grep -q . && echo ' +edits')"
    done
  done
  [ "$any" = 1 ] || echo "- none"
  echo
  echo "Query without choosing a map: .claude/hooks/graph.sh query <path-you-are-working-in> \"<question>\""
  echo "Any 'stale' above self-heals on the next query; 'ensure' forces it now."
}

case "${1:-}" in
  status)   shift; cmd_status "$@" ;;
  resolve)  shift; cmd_resolve "$@" ;;
  ensure)   shift; cmd_ensure "$@" ;;
  label)    shift; cmd_label  "$@" ;;
  query)    shift; run_q query "$@" ;;
  affected) shift; run_q affected "$@" ;;
  explain)  shift; run_q explain "$@" ;;
  path)     shift; run_q path "$@" ;;
  *) die "usage: graph.sh {status|resolve|ensure|label|query|affected|explain|path} [<path>] [args]" ;;
esac
