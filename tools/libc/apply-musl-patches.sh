#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd "$script_dir/../.." && pwd -P)"

expand_path() {
  local p="$1"
  case "$p" in
    "~") p="$HOME" ;;
    ~/*) p="$HOME/${p#~/}" ;;
  esac
  if [[ "$p" = /* ]]; then
    printf '%s\n' "$p"
  else
    printf '%s/%s\n' "$(pwd -P)" "$p"
  fi
}

die() {
  echo "error: $*" >&2
  exit 1
}

MUSL_SRC="${MUSL_SRC:-$repo_root/lib/musl}"
PATCH_DIR="${PATCH_DIR:-$repo_root/tools/libc/patches/musl}"
EXPECTED_BASE="${MUSL_EXPECTED_BASE:-1b76ff0767d01df72f692806ee5adee13c67ef88}"

MUSL_SRC="$(expand_path "$MUSL_SRC")"
PATCH_DIR="$(expand_path "$PATCH_DIR")"

[[ -d "$MUSL_SRC/.git" || -f "$MUSL_SRC/.git" ]] || die "musl source path is not a git checkout: $MUSL_SRC"
[[ -d "$PATCH_DIR" ]] || die "patch directory not found: $PATCH_DIR"

shopt -s nullglob
patches=("$PATCH_DIR"/*.patch)
(( ${#patches[@]} > 0 )) || die "no patch files found in $PATCH_DIR"

all_patches_already_applied() {
  local patch
  for patch in "${patches[@]}"; do
    git -C "$MUSL_SRC" apply --reverse --check "$patch" >/dev/null 2>&1 || return 1
  done
  return 0
}

if [[ -n "$(git -C "$MUSL_SRC" status --porcelain)" ]]; then
  if all_patches_already_applied; then
    echo "[skip] musl patch stack already present in dirty working tree"
    exit 0
  fi
  die "musl checkout is dirty ($MUSL_SRC). Commit/stash/reset before applying patches."
fi

git -C "$MUSL_SRC" cat-file -e "$EXPECTED_BASE^{commit}" 2>/dev/null || \
  die "expected base commit not found in musl checkout: $EXPECTED_BASE"

git -C "$MUSL_SRC" merge-base --is-ancestor "$EXPECTED_BASE" HEAD || \
  die "musl HEAD is outside expected base ancestry ($EXPECTED_BASE..HEAD)"

for patch in "${patches[@]}"; do
  name="$(basename "$patch")"
  if git -C "$MUSL_SRC" apply --reverse --check "$patch" >/dev/null 2>&1; then
    echo "[skip] $name already applied"
    continue
  fi

  if ! git -C "$MUSL_SRC" apply --check "$patch"; then
    die "failed pre-check for $name. Check patch ordering and musl base revision."
  fi

  git -C "$MUSL_SRC" apply "$patch"
  echo "[ok] applied $name"
done

echo "musl patch stack ready in $MUSL_SRC"
