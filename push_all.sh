#!/usr/bin/env bash
set -euo pipefail

MSG="${1:-sync}"

OWNER_RE='github\.com[:/](CzokNorris)/'

say() { printf "%s\n" "$*"; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || { echo "Missing command: $1"; exit 1; }; }

need_cmd git
need_cmd date

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

say "[0/5] Superproject: sanity"
git rev-parse --is-inside-work-tree >/dev/null

say "[1/5] Sync submodule urls (from .gitmodules)"
git submodule sync --recursive || true

# list submodule paths from .gitmodules (prefer), else from git config
mapfile -t SUBS < <(git config -f .gitmodules --name-only --get-regexp '^submodule\..*\.path$' 2>/dev/null \
  | sed -E 's/^submodule\.([^.]*)\.path$/\1/' \
  | while read -r name; do
      path="$(git config -f .gitmodules --get "submodule.$name.path")"
      echo "$path"
    done)

if [ "${#SUBS[@]}" -eq 0 ]; then
  say "No submodules found in .gitmodules (ok)."
fi

push_if_owned() {
  local repo_dir="$1"

  # Get push URL for origin if exists
  local push_url=""
  if git -C "$repo_dir" remote get-url --push origin >/dev/null 2>&1; then
    push_url="$(git -C "$repo_dir" remote get-url --push origin || true)"
  fi

  if [[ -z "$push_url" ]]; then
    say "    * skipping push (no origin remote)"
    return 0
  fi

  if echo "$push_url" | grep -qE "$OWNER_RE"; then
    say "    * pushing (owned): $push_url"
    # Push current branch (must exist)
    git -C "$repo_dir" push
  else
    say "    * skipping push (not owned): $push_url"
  fi
}

commit_submodule_if_dirty() {
  local path="$1"
  local msg="$2"

  if [ ! -d "$path/.git" ] && [ ! -f "$path/.git" ]; then
    say "  - Submodule: $path (missing checkout) -> skipping"
    return 0
  fi

  say "  - Submodule: $path"

  # If clean, just optionally push (owned) the current checked-out ref (usually nothing)
  if git -C "$path" diff --quiet && git -C "$path" diff --cached --quiet; then
    say "    * clean (no commit)"
    # Only push if it's on a branch AND owned; detached clean shouldn't create branches
    if git -C "$path" symbolic-ref -q HEAD >/dev/null 2>&1; then
      push_if_owned "$path"
    else
      say "    * detached HEAD + clean -> skipping push"
    fi
    return 0
  fi

  # Dirty: ensure we are on a branch (not detached)
  if ! git -C "$path" symbolic-ref -q HEAD >/dev/null 2>&1; then
    local ts branch
    ts="$(date +%Y%m%d-%H%M%S)"
    branch="czok-auto-${ts}"
    say "    * Detached HEAD detected, creating branch: $branch"
    git -C "$path" switch -c "$branch"
  fi

  # Commit all changes in the submodule
  git -C "$path" add -A
  if git -C "$path" diff --cached --quiet; then
    say "    * nothing staged after add -A (unexpected), skipping commit"
  else
    git -C "$path" commit -m "$msg"
  fi

  # Push if owned; if owned but no upstream, set it
  local push_url=""
  push_url="$(git -C "$path" remote get-url --push origin 2>/dev/null || true)"
  if echo "$push_url" | grep -qE "$OWNER_RE"; then
    local br
    br="$(git -C "$path" branch --show-current)"
    # ensure upstream set
    if ! git -C "$path" rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then
      say "    * Setting upstream: origin/$br"
      git -C "$path" push -u origin "$br"
    else
      push_if_owned "$path"
    fi
  else
    say "    * not owned -> commit done locally, push skipped: $push_url"
  fi
}

say "[2/5] Commit + push dirty submodules (only owned remotes)"
for p in "${SUBS[@]}"; do
  [ -n "$p" ] || continue
  [ -d "$p" ] || continue
  commit_submodule_if_dirty "$p" "$MSG"
done

say "[3/5] Superproject: stage submodule pointer changes + local files"
git add -A

say "[4/5] Superproject: commit if needed"
if git diff --cached --quiet; then
  say "  * no superproject changes to commit"
else
  git commit -m "$MSG"
fi

say "[5/5] Superproject: push"
# push the superproject (assumes origin set)
git push

say "✅ Done."
