#!/usr/bin/env bash
# Worktree-aware access to this workspace's Graphify maps.
#
# The problem this solves: there is not one graph in this workspace, there are
# 1 + N per repo — the workspace map under docs/<repo>/architecture/, plus one
# per ticket worktree under .work/<KEY>/<repo>/graphify-out/. They describe
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
      GRAPH="$ROOT/docs/$REPO/architecture/graph.json"
      STAMPFILE="$ROOT/docs/$REPO/architecture/.graph-stamp"
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
  # can copy it — same content, no extraction.
  if [ "$SCOPE" = worktree ] && [ -z "$(git -C "$TREE" status --porcelain -uno 2>/dev/null)" ] \
     && [ "$(manifest_sha "$REPO")" = "$(git -C "$TREE" rev-parse HEAD 2>/dev/null)" ] \
     && [ -f "$ROOT/docs/$REPO/architecture/graph.json" ]; then
    mkdir -p "$TREE/graphify-out"
    cp "$ROOT/docs/$REPO/architecture/graph.json" "$TREE/graphify-out/graph.json"
    write_stamp docs-map-copy
    echo "graph: reused docs/$REPO/architecture/graph.json — built from this exact commit"
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
  write_stamp "$SCOPE-$mode"
  grep -iE 'nodes|edges|communities|updated' "$log" | tail -2

  # The workspace map is the artefact other docs and skills point at, so keep it
  # in step with its own checkout rather than letting it drift silently.
  if [ "$SCOPE" = primary ]; then
    mkdir -p "$ROOT/docs/$REPO/architecture"
    # The label/analysis sidecars travel with graph.json or community names are lost:
    # `query` reads labels from .graphify_labels.json beside the graph, so a copy without
    # them answers with bare integers ("community=57") instead of "community=auth.js".
    for f in graph.json graph.html GRAPH_REPORT.md              .graphify_labels.json .graphify_labels.json.sig .graphify_analysis.json; do
      [ -f "$TREE/graphify-out/$f" ] && cp "$TREE/graphify-out/$f" "$ROOT/docs/$REPO/architecture/$f"
    done
    python3 - "$MANIFEST" "$REPO" "$(git -C "$TREE" rev-parse HEAD)" <<'PY'
import json,sys,datetime
p,repo,sha=sys.argv[1],sys.argv[2],sys.argv[3]
try: m=json.load(open(p))
except Exception: sys.exit(0)
for r in m.get("repos",[]):
    if r.get("name")==repo:
        mp=r.setdefault("mapping",{})
        mp["lastMappedSha"]=sha
        mp["lastMappedAt"]=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        mp["lastMappedBy"]="graph.sh ensure"
        json.dump(m,open(p,"w"),indent=2); print(f"manifest: {repo}.mapping.lastMappedSha -> {sha[:7]}")
        break
PY
  fi
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

cmd_status() {
  echo "## Graphify maps in this workspace"
  echo
  echo "### Workspace maps — docs/<repo>/architecture/ (the repo's own checkout)"
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
  query)    shift; run_q query "$@" ;;
  affected) shift; run_q affected "$@" ;;
  explain)  shift; run_q explain "$@" ;;
  path)     shift; run_q path "$@" ;;
  *) die "usage: graph.sh {status|resolve|ensure|query|affected|explain|path} [<path>] [args]" ;;
esac
