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

GLIBC_SRC="${GLIBC_SRC:-$repo_root/lib/glibc}"
PATCH_DIR="${PATCH_DIR:-$repo_root/tools/libc/patches/glibc}"
EXPECTED_BASE="${GLIBC_EXPECTED_BASE:-04e750e75b73957cf1c791535a3f4319534a52fc}"

GLIBC_SRC="$(expand_path "$GLIBC_SRC")"
PATCH_DIR="$(expand_path "$PATCH_DIR")"

[[ -d "$GLIBC_SRC/.git" || -f "$GLIBC_SRC/.git" ]] || die "glibc source path is not a git checkout: $GLIBC_SRC"
[[ -d "$PATCH_DIR" ]] || die "patch directory not found: $PATCH_DIR"

shopt -s nullglob
patches=("$PATCH_DIR"/*.patch)
(( ${#patches[@]} > 0 )) || die "no patch files found in $PATCH_DIR"

all_patches_already_applied() {
  local patch
  for patch in "${patches[@]}"; do
    git -C "$GLIBC_SRC" apply --reverse --check "$patch" >/dev/null 2>&1 || return 1
  done
  return 0
}

if [[ -n "$(git -C "$GLIBC_SRC" status --porcelain)" ]]; then
  if all_patches_already_applied; then
    echo "[skip] glibc patch stack already present in dirty working tree"
    exit 0
  fi
  die "glibc checkout is dirty ($GLIBC_SRC). Commit/stash/reset before applying patches."
fi

git -C "$GLIBC_SRC" cat-file -e "$EXPECTED_BASE^{commit}" 2>/dev/null || \
  die "expected base commit not found in glibc checkout: $EXPECTED_BASE"

git -C "$GLIBC_SRC" merge-base --is-ancestor "$EXPECTED_BASE" HEAD || \
  die "glibc HEAD is outside expected base ancestry ($EXPECTED_BASE..HEAD)"

for patch in "${patches[@]}"; do
  name="$(basename "$patch")"
  if git -C "$GLIBC_SRC" apply --reverse --check "$patch" >/dev/null 2>&1; then
    echo "[skip] $name already applied"
    continue
  fi

  if ! git -C "$GLIBC_SRC" apply --check "$patch"; then
    die "failed pre-check for $name. Check patch ordering and glibc base revision."
  fi

  git -C "$GLIBC_SRC" apply "$patch"
  echo "[ok] applied $name"
done

echo "glibc patch stack ready in $GLIBC_SRC"
