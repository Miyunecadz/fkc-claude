#!/usr/bin/env bash
# Per-ticket git worktrees for the three fk-connect repos.
#
# Why a script: creating an isolated checkout, cutting the branch off the *fetched*
# remote base, linking the installed dependencies and recording what it was cut from is
# parsing and plumbing, not reasoning. Doing it deterministically keeps the model out of
# the loop and keeps its context free of git noise — it prints a fixed metadata block,
# never a diff and never file contents.
#
# ticket-worktree.sh prepare <KEY> <repo> <base-ref> [<branch>] create / reuse
# ticket-worktree.sh status <KEY> [repo] state of each worktree
# ticket-worktree.sh list every ticket workspace
# ticket-worktree.sh remove <KEY> [repo] [--force] tear down
# ticket-worktree.sh sidecar init <KEY> <summary> write the header, state NEW
# ticket-worktree.sh sidecar append <KEY> <Section> <STATE> body on stdin
# ticket-worktree.sh sidecar state <KEY> <STATE> [note] state change only
# ticket-worktree.sh sidecar show <KEY> [--header] read it back
#
# The sidecar subcommand exists so the main thread never needs Edit or Write. Appending a
# stage section used to be a read-modify-write of the whole file emitted as a heredoc —
# 1-2k output tokens per stage, permanently resident in context. 'sidecar append' takes
# only the new body, and updates the section, 'state:' and the '## Log' line in one
# atomic step, which is also the rule the workflow kept breaking by hand.
#
# Layout (workspace root is NOT a git repo — each repo has its own):
# .work/<KEY>/work.md state sidecar, written by the workflow
# .work/<KEY>/<repo>/ the worktree
# .work/<KEY>/meta/<repo>.env BASE_REF / BASE_SHA / BRANCH, recorded at prepare time
# .work/<KEY>/validate/ validator logs (kept out of model context)
# .work/<KEY>/review/ reviewer reports
#
# Exit: 0 ok | 1 usage / refused | 2 git failure

set -uo pipefail
HOOKS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HOOKS/../.." && pwd)"
WORK="$ROOT/.work"
REPOS="fk-admin-panel-be fk-admin-panel-fe fk-mobile"

die() { echo "$1" >&2; exit "${2:-1}"; }

valid_repo() { for r in $REPOS; do [ "$r" = "$1" ] && return 0; done; return 1; }
valid_key() { echo "$1" | grep -qE '^[A-Za-z][A-Za-z0-9]*-[0-9]+$'; }

meta_of() { echo "$WORK/$1/meta/$2.env"; }

# ---- prepare ----------------------------------------------------------------------
cmd_prepare() {
 local key="${1:-}" repo="${2:-}" base="${3:-}" branch="${4:-}"
 [ -n "$key" ] && [ -n "$repo" ] && [ -n "$base" ] || die "usage: prepare <KEY> <repo> <base-ref> [branch]"
 valid_key "$key" || die "'$key' is not a ticket key (expected e.g. FKC-123)."
 valid_repo "$repo" || die "'$repo' is not a repo in this workspace ($REPOS)."
 [ -d "$ROOT/$repo/.git" ] || die "$ROOT/$repo is not a git checkout." 2

 local wt="$WORK/$key/$repo"
 branch="${branch:-ticket/$key}"

 # Always fetch: the base must be the remote's current tip, not a local ref that has
 # been sitting here since the last time someone pulled.
 git -C "$ROOT/$repo" fetch --prune --quiet origin || die "fetch failed in $repo" 2

 # Resolve the base ref against the remote first, so 'staging' means origin/staging.
 local base_ref base_sha
 if git -C "$ROOT/$repo" rev-parse --verify --quiet "origin/$base" >/dev/null; then
 base_ref="origin/$base"
 elif git -C "$ROOT/$repo" rev-parse --verify --quiet "$base" >/dev/null; then
 base_ref="$base"
 else
 die "base ref '$base' does not exist in $repo (tried origin/$base and $base)." 2
 fi
 base_sha=$(git -C "$ROOT/$repo" rev-parse --short "$base_ref")

 if [ -d "$wt" ]; then
 echo "## Worktree: $key / $repo (existing — reused)"
 else
 mkdir -p "$WORK/$key/meta" "$WORK/$key/validate" "$WORK/$key/review"
 if git -C "$ROOT/$repo" rev-parse --verify --quiet "refs/heads/$branch" >/dev/null; then
 git -C "$ROOT/$repo" worktree add "$wt" "$branch" >/dev/null 2>&1 \
 || die "cannot add worktree for existing branch $branch (already checked out elsewhere?)" 2
 else
 git -C "$ROOT/$repo" worktree add -b "$branch" "$wt" "$base_ref" >/dev/null 2>&1 \
 || die "git worktree add failed for $repo" 2
 fi
 cat > "$(meta_of "$key" "$repo")" <<META
BASE_REF=$base_ref
BASE_SHA=$base_sha
BRANCH=$branch
CREATED=$(date -u +%Y-%m-%dT%H:%M:%SZ)
META
 echo "## Worktree: $key / $repo (created)"
 fi

 # Dependencies: link, never install. A worktree has no node_modules of its own and a
 # React Native install is slow; the link makes the repo's real checks runnable here.
 # Writing through it would mutate the main checkout, so installs are refused below.
 local linked="none"
 if [ ! -e "$wt/node_modules" ] && [ -d "$ROOT/$repo/node_modules" ]; then
 ln -s "$ROOT/$repo/node_modules" "$wt/node_modules" && linked="linked from $repo/node_modules"
 elif [ -L "$wt/node_modules" ]; then
 linked="linked from $repo/node_modules"
 elif [ -d "$ROOT/$repo/node_modules" ]; then
 linked="present"
 else
 linked="ABSENT — $repo has no node_modules; its yarn checks cannot run"
 fi

 # Untracked env files are not in the worktree; link them so a build reads the same
 # config as the main checkout. Contents are never printed by anything here.
 local envs=0
 for f in "$ROOT/$repo"/.env "$ROOT/$repo"/.env.*; do
 [ -f "$f" ] || continue
 local b; b=$(basename "$f")
 [ -e "$wt/$b" ] || { ln -s "$f" "$wt/$b" && envs=$((envs+1)); }
 done

 # shellcheck disable=SC1090
 . "$(meta_of "$key" "$repo")"
 cat <<OUT
path: ${wt#"$ROOT"/}
branch: $BRANCH
base: $BASE_REF @ $BASE_SHA
deps: $linked
env: $envs file(s) linked from $repo
next: edit only under ${wt#"$ROOT"/} — never under $repo/
OUT
}

# ---- status -----------------------------------------------------------------------
one_status() {
 local key="$1" repo="$2" wt="$WORK/$1/$2"
 [ -d "$wt" ] || { echo "- $repo: no worktree"; return; }
 local meta; meta=$(meta_of "$key" "$repo")
 local BASE_REF="?" BASE_SHA="?" BRANCH="?"
 # shellcheck disable=SC1090
 [ -f "$meta" ] && . "$meta"
 git -C "$wt" fetch --prune --quiet origin 2>/dev/null
 local head dirty ahead behind moved
 head=$(git -C "$wt" rev-parse --short HEAD 2>/dev/null)
 dirty=$(git -C "$wt" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
 read -r behind ahead <<<"$(git -C "$wt" rev-list --left-right --count "$BASE_REF...HEAD" 2>/dev/null || echo '? ?')"
 moved=$(git -C "$wt" rev-parse --short "$BASE_REF" 2>/dev/null)
 echo "- $repo: $BRANCH @ $head | base $BASE_REF cut@$BASE_SHA now@$moved | +$ahead/-$behind | dirty:$dirty"
 [ "$moved" != "$BASE_SHA" ] && [ "$moved" != "" ] && \
 echo " ! base branch moved since this worktree was cut — rebase or re-check before review"
 [ "$dirty" != "0" ] && echo " ! uncommitted changes in the worktree"
}

cmd_status() {
 local key="${1:-}"; [ -n "$key" ] || die "usage: status <KEY> [repo]"
 [ -d "$WORK/$key" ] || die "no workspace at .work/$key — run prepare first."
 echo "## Ticket workspace: $key"
 echo "sidecar: $( [ -f "$WORK/$key/work.md" ] && echo ".work/$key/work.md" || echo 'none — the workflow writes it' )"
 if [ -n "${2:-}" ]; then one_status "$key" "$2"; else
 for r in $REPOS; do [ -d "$WORK/$key/$r" ] && one_status "$key" "$r"; done
 fi
}

# ---- list -------------------------------------------------------------------------
cmd_list() {
 [ -d "$WORK" ] || { echo "No ticket workspaces (.work/ does not exist)."; exit 0; }
 local n=0
 for d in "$WORK"/*/; do
 [ -d "$d" ] || continue
 local key; key=$(basename "$d"); n=$((n+1))
 local state="-"
 [ -f "$d/work.md" ] && state=$(grep -m1 '^state:' "$d/work.md" | sed 's/^state:[[:space:]]*//')
 local repos=""
 for r in $REPOS; do [ -d "$d/$r" ] && repos="$repos $r"; done
 echo "- $key: state=${state:--}, repos:${repos:- none}"
 local blocked; blocked=$(grep '^blocked:' "$d/work.md" 2>/dev/null | sed 's/^blocked:[[:space:]]*//')
 [ -n "$blocked" ] && [ "$blocked" != "-" ] && echo " BLOCKED: $blocked"
 done
 [ "$n" = "0" ] && echo "No ticket workspaces yet."
 exit 0
}

# ---- remove -----------------------------------------------------------------------
cmd_remove() {
 local key="${1:-}" repo="" force=0
 shift || true
 for a in "$@"; do case "$a" in --force) force=1 ;; *) repo="$a" ;; esac; done
 [ -n "$key" ] || die "usage: remove <KEY> [repo] [--force]"
 [ -d "$WORK/$key" ] || die "no workspace at .work/$key"
 local targets="$REPOS"; [ -n "$repo" ] && targets="$repo"
 for r in $targets; do
 local wt="$WORK/$key/$r"; [ -d "$wt" ] || continue
 local dirty; dirty=$(git -C "$wt" status --porcelain | wc -l | tr -d ' ')
 local unpushed; unpushed=$(git -C "$wt" log --oneline @{upstream}..HEAD 2>/dev/null | wc -l | tr -d ' ')
 [ -z "$unpushed" ] && unpushed=$(git -C "$wt" rev-list --count HEAD ^origin/HEAD 2>/dev/null || echo 0)
 if [ "$force" = "0" ] && { [ "$dirty" != "0" ] || [ "$unpushed" != "0" ]; }; then
 echo "- $r: REFUSED — $dirty uncommitted, $unpushed unpushed commit(s). Push or discard first, or pass --force."
 continue
 fi
 git -C "$ROOT/$r" worktree remove --force "$wt" >/dev/null 2>&1 \
 && echo "- $r: worktree removed (branch kept)" \
 || echo "- $r: worktree remove failed"
 done
 echo "note: .work/$key/work.md and the branches are kept — delete them yourself when the ticket is closed."
}

# ---- sidecar ----------------------------------------------------------------------
# The state file is append-only by construction: no subcommand here can rewrite or
# delete a section that is already there. A repeated section name gets " (2)", " (3)".
VALID_STATES="NEW ANALYSED PLANNED APPROVED IMPLEMENTING IMPLEMENTED VERIFIED FAILED_VERIFICATION REVIEWED HANDED_OVER PR_OPEN BLOCKED NOT_NEEDED ALREADY_IMPLEMENTED NOT_APPROVED"

valid_state() { for v in $VALID_STATES; do [ "$v" = "$1" ] && return 0; done; return 1; }
sidecar_of() { echo "$WORK/$1/work.md"; }
now_utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }

sc_require() {
 local f; f="$(sidecar_of "$1")"
 [ -f "$f" ] || die "no sidecar at .work/$1/work.md — run 'sidecar init $1 <summary>' first."
 echo "$f"
}

# rewrite the single 'state:' header line, in place, leaving everything else untouched
sc_set_state() {
 local f="$1" st="$2"
 awk -v st="$st" '
 !done && /^state:[[:space:]]/ { sub(/^state:[[:space:]]*.*$/, "state:    " st); done=1 }
 { print }
 ' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
}

# Log lines go *inside* the '## Log' block, newest last — never at EOF, which would
# interleave them into whatever stage section happens to be last.
sc_log() {
 local f="$1" line="$2" entry
 entry="$(now_utc)  $line"
 grep -q '^## Log$' "$f" || printf '\n## Log\n' >> "$f"
 awk -v e="$entry" '
 /^## Log$/ { print; inlog=1; next }
 inlog && /^## / { print e; print ""; inlog=0; print; next }
 { print }
 END { if (inlog) print e }
 ' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
}

cmd_sidecar() {
 local sub="${1:-}"; shift || true
 case "$sub" in
 init)
 local key="${1:-}"; shift || true
 local summary="$*"
 [ -n "$key" ] || die "usage: sidecar init <KEY> <summary>"
 valid_key "$key" || die "'$key' is not a ticket key (expected e.g. FKC-123)."
 local f; f="$(sidecar_of "$key")"
 [ -f "$f" ] && die "sidecar already exists at .work/$key/work.md — it is append-only; use 'sidecar append'."
 mkdir -p "$WORK/$key/meta" "$WORK/$key/validate" "$WORK/$key/review"
 cat > "$f" <<SIDECAR
# Work — $key
ticket:   $key — ${summary:-<summary>}
jira:     updated=<ISO> status=<name> fields-sha=<8 hex>
state:    NEW
blocked:  -
repos:    -
graph:    -

## Log
$(now_utc)  sidecar created, state NEW
SIDECAR
 echo "## Sidecar: $key (created) — .work/$key/work.md"
 echo "state: NEW"
 echo "next:  fill jira:/repos:/graph: with 'sidecar header', then append stages."
 ;;
 header)
 # sidecar header <KEY> <key>=<value> ...   — set header lines other than state:
 local key="${1:-}"; shift || true
 local f; f="$(sc_require "$key")" || exit 1
 [ "$#" -gt 0 ] || die "usage: sidecar header <KEY> jira=... repos=... graph=... blocked=..."
 for kv in "$@"; do
 local k="${kv%%=*}" v="${kv#*=}"
 case "$k" in
 jira|repos|graph|blocked|ticket) ;;
 state) die "use 'sidecar state' or 'sidecar append' to change state." ;;
 *) die "unknown header key '$k' (jira|repos|graph|blocked|ticket)." ;;
 esac
 awk -v k="$k" -v v="$v" '
 !done && $0 ~ "^" k ":[[:space:]]" { printf "%-9s %s\n", k ":", v; done=1; next }
 { print }
 END { if (!done) printf "%-9s %s\n", k ":", v }
 ' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
 done
 echo "## Sidecar: $key header updated"
 sed -n '1,8p' "$f"
 ;;
 append)
 # sidecar append <KEY> <Section> <STATE> [--note "<log line>"]   body on stdin
 local key="${1:-}" section="${2:-}" state="${3:-}"; shift 3 2>/dev/null || true
 local note=""
 while [ "$#" -gt 0 ]; do case "$1" in --note) note="${2:-}"; shift 2 ;; *) shift ;; esac; done
 [ -n "$key" ] && [ -n "$section" ] && [ -n "$state" ] \
 || die "usage: sidecar append <KEY> <Section> <STATE> [--note \"...\"]   (body on stdin)"
 local f; f="$(sc_require "$key")" || exit 1
 valid_state "$state" || die "'$state' is not a valid state ($VALID_STATES)."
 local body; body="$(cat)"
 [ -n "$body" ] || die "refusing to append an empty '$section' section — pipe the body on stdin."

 # never overwrite: a repeated section becomes "Section (2)"
 local title="$section" n=2
 while grep -qF "## $title — " "$f"; do title="$section ($n)"; n=$((n+1)); done

 # '## Log' stays the last section: insert this one above it when it is there.
 if grep -q '^## Log$' "$f"; then
 awk -v t="$title" -v d="$(date -u +%Y-%m-%d)" -v b="$body" '
 !done && /^## Log$/ { printf "## %s — %s\n\n%s\n\n", t, d, b; done=1 }
 { print }
 END { if (!done) printf "\n## %s — %s\n\n%s\n", t, d, b }
 ' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
 else
 { printf '\n## %s — %s\n\n' "$title" "$(date -u +%Y-%m-%d)"; printf '%s\n' "$body"; } >> "$f"
 fi
 sc_set_state "$f" "$state"
 sc_log "$f" "$title -> state $state${note:+ — $note}"
 echo "## Sidecar: $key += '## $title' — state now $state"
 echo "file: .work/$key/work.md ($(wc -l < "$f" | tr -d ' ') lines)"
 ;;
 state)
 local key="${1:-}" state="${2:-}"; shift 2 2>/dev/null || true
 local note="$*"
 [ -n "$key" ] && [ -n "$state" ] || die "usage: sidecar state <KEY> <STATE> [note]"
 local f; f="$(sc_require "$key")" || exit 1
 valid_state "$state" || die "'$state' is not a valid state ($VALID_STATES)."
 sc_set_state "$f" "$state"
 [ "$state" = "BLOCKED" ] && [ -n "$note" ] && \
 awk -v v="$note" '!d && /^blocked:[[:space:]]/ { printf "%-9s %s\n", "blocked:", v; d=1; next } { print }' \
 "$f" > "$f.tmp" && mv "$f.tmp" "$f"
 sc_log "$f" "state -> $state${note:+ — $note}"
 echo "## Sidecar: $key state now $state"
 ;;
 show)
 local key="${1:-}" what="${2:-}"
 [ -n "$key" ] || die "usage: sidecar show <KEY> [--header|--sections]"
 local f; f="$(sc_require "$key")" || exit 1
 case "$what" in
 --header) sed -n '1,8p' "$f" ;;
 --sections) grep -n '^## ' "$f" ;;
 *) cat "$f" ;;
 esac
 ;;
 *)
 die "usage: ticket-worktree.sh sidecar {init|header|append|state|show} <KEY> ..."
 ;;
 esac
 exit 0
}

case "${1:-}" in
 prepare) shift; cmd_prepare "$@" ;;
 status) shift; cmd_status "$@" ;;
 list) shift; cmd_list "$@" ;;
 remove) shift; cmd_remove "$@" ;;
 sidecar) shift; cmd_sidecar "$@" ;;
 *) die "usage: ticket-worktree.sh {prepare|status|list|remove|sidecar} ..." ;;
esac
