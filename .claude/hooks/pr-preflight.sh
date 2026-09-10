#!/usr/bin/env bash
# Publish-state inspection ahead of a commit + push + pull request. Used by /create-pr.
#
# Why a script: "which worktree, which branch, what was it cut from, is it pushed, has the
# remote moved, what would the PR contain, is anything sensitive in it" is git plumbing.
# Getting it wrong is how a workflow pushes over someone else's commits or opens a PR
# against the wrong branch. It prints state and the exact follow-up commands; it never
# commits, never pushes, never writes anything, and never prints a diff.
#
#   pr-preflight.sh <KEY> [repo]              a ticket's worktrees (.work/<KEY>/<repo>/)
#   pr-preflight.sh --checkout <repo> [dest]  the user's own checkout, no ticket
#
# The destination is NOT guessed. For a worktree it is BASE_REF recorded at cut time —
# the branch the work actually descends from. For --checkout it must be given, or the
# script reports the candidates it can prove and stops.
#
# Exit: 0 ready | 1 a human must decide something first | 2 bad argument

set -uo pipefail
HOOKS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HOOKS/../.." && pwd)"
WORK="$ROOT/.work"
REPOS="fk-admin-panel-be fk-admin-panel-fe fk-mobile"

valid_repo() { for r in $REPOS; do [ "$r" = "$1" ] && return 0; done; return 1; }
valid_key()  { echo "$1" | grep -qE '^[A-Za-z][A-Za-z0-9]*-[0-9]+$'; }

STOP=0
halt() { echo "  ! $1"; STOP=1; }

# ---- one repo -----------------------------------------------------------------------
# inspect <dir> <repo> <destination-or-empty> <label>
inspect() {
  local d="$1" repo="$2" dest="${3:-}" label="$4"
  local g=(git -C "$d")

  echo "## $label"
  [ -d "$d/.git" ] || [ -f "$d/.git" ] || { halt "$d is not a git checkout."; return; }

  local branch head
  branch=$("${g[@]}" rev-parse --abbrev-ref HEAD)
  head=$("${g[@]}" rev-parse --short HEAD)
  echo "path:   $d"
  echo "branch: $branch @ $head"

  [ "$branch" = "HEAD" ] && halt "detached HEAD — no branch to push."
  { [ -d "$d/.git/rebase-merge" ] || [ -d "$d/.git/rebase-apply" ]; } && halt "a rebase is in progress — finish or abort it first."
  [ -f "$d/.git/MERGE_HEAD" ] && halt "a merge is in progress — resolve and commit it first."
  case "$branch" in
    master|staging|development) halt "$branch is a shared branch. A PR must come from a work branch." ;;
  esac

  # ---- destination -------------------------------------------------------------------
  if [ -z "$dest" ]; then
    echo "destination: UNKNOWN — none recorded and none given"
    echo "  provable candidates (branch descends from these):"
    local any=0 c
    for c in staging master; do
      if "${g[@]}" rev-parse --verify --quiet "origin/$c" >/dev/null &&
         "${g[@]}" merge-base --is-ancestor "origin/$c" HEAD 2>/dev/null; then
        echo "    origin/$c  ($("${g[@]}" rev-list --count "origin/$c..HEAD") commit(s) ahead)"
        any=1
      fi
    done
    [ "$any" = "0" ] && echo "    none — the branch descends from neither origin/staging nor origin/master"
    halt "destination not established. Ask; do not default to master."
  else
    echo "destination: $dest"
    if ! "${g[@]}" rev-parse --verify --quiet "origin/$dest" >/dev/null; then
      halt "origin/$dest does not exist in $repo."
    elif ! "${g[@]}" merge-base --is-ancestor "origin/$dest" HEAD 2>/dev/null; then
      local behind
      behind=$("${g[@]}" rev-list --count "HEAD..origin/$dest" 2>/dev/null || echo '?')
      echo "  note: origin/$dest has $behind commit(s) not in this branch — the PR diff is still"
      echo "        computed by Bitbucket against the merge base, but confirm this is the branch"
      echo "        the work was cut from."
    fi
  fi

  # ---- working tree ------------------------------------------------------------------
  local staged unstaged untracked
  staged=$("${g[@]}" diff --cached --name-only | grep -c . || true)
  unstaged=$("${g[@]}" diff --name-only | grep -c . || true)
  untracked=$("${g[@]}" ls-files --others --exclude-standard | grep -c . || true)
  echo "working tree: staged $staged | unstaged $unstaged | untracked $untracked"
  [ "$staged"    != "0" ] && "${g[@]}" diff --cached --name-only            | sed 's/^/  + /'
  [ "$unstaged"  != "0" ] && "${g[@]}" diff --name-only                     | sed 's/^/  M /'
  [ "$untracked" != "0" ] && "${g[@]}" ls-files --others --exclude-standard | sed 's/^/  ? /'

  # ---- commits and changed files this PR would carry -----------------------------------
  local range="" nfiles=0
  if [ -n "$dest" ] && "${g[@]}" rev-parse --verify --quiet "origin/$dest" >/dev/null; then
    range="origin/$dest...HEAD"
    echo "commits: $("${g[@]}" rev-list --count "origin/$dest..HEAD") on this branch"
    "${g[@]}" log --oneline --no-decorate "origin/$dest..HEAD" | head -20 | sed 's/^/  /'
    echo "changed files vs origin/$dest:"
    "${g[@]}" diff --name-only "$range" | sed 's/^/  /'
    nfiles=$("${g[@]}" diff --name-only "$range" | grep -c . || true)
    echo "read the diff once, in full, before staging anything:"
    echo "  git -C $d diff $range"
  fi

  # ---- sensitive material --------------------------------------------------------------
  local all flags=""
  all=$( { [ -n "$range" ] && "${g[@]}" diff --name-only "$range"
           "${g[@]}" diff --name-only
           "${g[@]}" diff --cached --name-only
           "${g[@]}" ls-files --others --exclude-standard; } | sort -u )
  echo "$all" | grep -qE '(^|/)\.env($|\.)'                     && flags="$flags env-file"
  echo "$all" | grep -qE '\.(pem|key|p12|pfx|jks|keystore)$'    && flags="$flags secret-file"
  echo "$all" | grep -qE '(^|/)(\.npmrc|credentials\.json)$'    && flags="$flags credentials"
  echo "$all" | grep -qE '(^|/)(yarn\.lock|package-lock\.json)$' && flags="$flags lockfile"
  echo "$all" | grep -qE '(^|/)db/migrations/'                  && flags="$flags migration"
  echo "$all" | grep -qE '(^|/)db/schema\.sql$'                 && flags="$flags dbmate-schema"
  if [ -n "$flags" ]; then
    echo "flags:$flags"
    case "$flags" in
      *env-file*|*secret-file*|*credentials*)
        halt "secret material is in scope. Stop and report it — do not commit it and do not 'git rm' it silently." ;;
    esac
  fi

  # ---- remote and publish state ---------------------------------------------------------
  local url path host platform rsha ahead behind
  url=$("${g[@]}" remote get-url origin 2>/dev/null)
  if [ -z "$url" ]; then
    halt "no 'origin' remote — cannot establish where to push."
  else
    host=$(echo "$url" | sed -E 's#^[a-z+]+://##; s#^[^@]*@##; s#[:/].*$##')
    path=$(echo "$url" | sed -E 's#^[a-z+]+://[^/]+/##; s#^[^:]*:##; s#\.git$##')
    case "$host" in
      *bitbucket.org*) platform="bitbucket-cloud" ;;
      *github*)        platform="github" ;;
      *gitlab*)        platform="gitlab" ;;
      *)               platform="UNKNOWN" ;;
    esac
    echo "remote:   origin $url"
    echo "platform: $platform"
    if [ "$platform" = "bitbucket-cloud" ]; then
      echo "bitbucket: $path      # workspace/repo_slug for the Bitbucket API"
    else
      halt "hosting platform is not Bitbucket Cloud per the remote. Do not guess it — stop and ask."
    fi

    rsha=$(git -C "$d" ls-remote --heads origin "$branch" 2>/dev/null | awk '{print substr($1,1,8)}')
    if [ -z "$rsha" ]; then
      echo "remote branch: absent — this push creates origin/$branch"
      echo "push: git -C $d push -u origin $branch"
    else
      echo "remote branch: origin/$branch @ $rsha"
      git -C "$d" fetch --quiet origin "$branch" 2>/dev/null
      ahead=$(git -C "$d" rev-list --count "origin/$branch..HEAD" 2>/dev/null || echo '?')
      behind=$(git -C "$d" rev-list --count "HEAD..origin/$branch" 2>/dev/null || echo '?')
      echo "push state: ahead $ahead | behind $behind"
      [ "$behind" != "0" ] && [ "$behind" != "?" ] &&
        halt "origin/$branch has $behind commit(s) you do not have. Investigate — never force, never overwrite remote work."
      [ "$ahead" = "0" ] && echo "  nothing to push — the remote branch already carries this commit."
      echo "push: git -C $d push origin $branch"
    fi

    if [ "$platform" = "bitbucket-cloud" ]; then
      echo "existing PR check (do this before creating one):"
      echo "  bb_get /repositories/$path/pullrequests  q=source.branch.name=\"$branch\""
    fi
  fi
  echo
}

# ---- entry ----------------------------------------------------------------------------
case "${1:-}" in
  "" )
    echo "usage: pr-preflight.sh <KEY> [repo]"
    echo "       pr-preflight.sh --checkout <repo> [destination]"
    echo "repos: $REPOS"
    exit 2 ;;

  --checkout )
    repo="${2:-}"; dest="${3:-}"
    valid_repo "$repo" || { echo "unknown repo '$repo'. Expected one of: $REPOS"; exit 2; }
    echo "# PR preflight — $repo (user's own checkout, no ticket worktree)"
    echo "note: this is the user's working checkout. Nothing here may be staged, committed or"
    echo "      reset without their explicit say-so on the /create-pr approval gate."
    echo
    inspect "$ROOT/$repo" "$repo" "$dest" "$repo (checkout)"
    ;;

  * )
    key="$1"; only="${2:-}"
    valid_key "$key" || { echo "'$key' is not a ticket key (expected e.g. FKC-123)."; exit 2; }
    [ -d "$WORK/$key" ] || { echo "no ticket workspace at .work/$key — run /implement-ticket first, or use --checkout."; exit 2; }
    [ -n "$only" ] && { valid_repo "$only" || { echo "unknown repo '$only'."; exit 2; }; }

    echo "# PR preflight — $key"
    [ -f "$WORK/$key/work.md" ] && echo "sidecar: .work/$key/work.md  ($(grep -m1 '^state:' "$WORK/$key/work.md" | sed 's/  */ /g'))"
    grep -q '^## PR' "$WORK/$key/work.md" 2>/dev/null && echo "  note: the sidecar already has a '## PR' section — a PR was created in an earlier run. Verify it, do not create a second."
    echo

    found=0
    for repo in $REPOS; do
      [ -n "$only" ] && [ "$only" != "$repo" ] && continue
      wt="$WORK/$key/$repo"
      [ -d "$wt" ] || continue
      found=1
      dest=""
      meta="$WORK/$key/meta/$repo.env"
      if [ -f "$meta" ]; then
        # BASE_REF is recorded as e.g. origin/staging
        dest=$(sed -n 's/^BASE_REF=//p' "$meta" | sed 's#^origin/##' | head -1)
        echo "meta: $(tr '\n' ' ' < "$meta")"
      fi
      inspect "$wt" "$repo" "$dest" "$repo"
    done
    [ "$found" = "1" ] || { echo "no worktrees under .work/$key."; exit 2; }
    ;;
esac

if [ "$STOP" != "0" ]; then
  echo "## Verdict: STOP — a human must decide. See the ! lines above."
  exit 1
fi
echo "## Verdict: ready to read the diff and prepare the commit, title and description."
exit 0
