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

pick_cmd() {
  local candidate
  for candidate in "$@"; do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

TARGET="${TARGET:-linx64-unknown-linux-musl}"
LLVM_BUILD="${LLVM_BUILD:-/Users/zhoubot/llvm-project/build-linxisa-clang}"
SYSROOT="${SYSROOT:-/Users/zhoubot/toolchains/cross/linx64/sysroot}"
MUSL_SRC="${MUSL_SRC:-$repo_root/lib/musl}"
OUT_ROOT="${OUT_ROOT:-$repo_root/out/libc/musl}"
BUILD_DIR="${BUILD_DIR:-$OUT_ROOT/build}"
INSTALL_DIR="${INSTALL_DIR:-$OUT_ROOT/install}"
LOG_DIR="${LOG_DIR:-$OUT_ROOT/logs}"
JOBS="${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 8)}"
MUSL_OPTIMIZE="${MUSL_OPTIMIZE:---disable-optimize}"

LLVM_BUILD="$(expand_path "$LLVM_BUILD")"
SYSROOT="$(expand_path "$SYSROOT")"
MUSL_SRC="$(expand_path "$MUSL_SRC")"
OUT_ROOT="$(expand_path "$OUT_ROOT")"
BUILD_DIR="$(expand_path "$BUILD_DIR")"
INSTALL_DIR="$(expand_path "$INSTALL_DIR")"
LOG_DIR="$(expand_path "$LOG_DIR")"

CLANG="$LLVM_BUILD/bin/clang"
CLANGXX="$LLVM_BUILD/bin/clang++"
LLVM_AR="$LLVM_BUILD/bin/llvm-ar"
LLVM_RANLIB="$LLVM_BUILD/bin/llvm-ranlib"

for tool in "$CLANG" "$CLANGXX" "$LLVM_AR" "$LLVM_RANLIB"; do
  [[ -x "$tool" ]] || { echo "error: missing required llvm tool: $tool" >&2; exit 2; }
done

GNU_MAKE="${GNU_MAKE:-$(pick_cmd gmake /opt/homebrew/bin/gmake make || true)}"
[[ -n "$GNU_MAKE" ]] || { echo "error: unable to locate gmake/make" >&2; exit 2; }

[[ -d "$MUSL_SRC" ]] || { echo "error: musl source dir missing: $MUSL_SRC" >&2; exit 2; }
if [[ ! -d "$SYSROOT" ]]; then
  fallback_sysroot="/Users/zhoubot/sysroots/linx64-linux-gnu"
  if [[ -d "$fallback_sysroot" ]]; then
    SYSROOT="$fallback_sysroot"
  else
    echo "error: sysroot dir missing: $SYSROOT" >&2
    exit 2
  fi
fi

mkdir -p "$OUT_ROOT" "$INSTALL_DIR/lib" "$LOG_DIR"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

configure_log="$LOG_DIR/01-configure.log"
m2_log="$LOG_DIR/02-m2-libc-a.log"
m3_log="$LOG_DIR/03-m3-shared.log"
summary_log="$LOG_DIR/summary.txt"

{
  echo "[musl] target: $TARGET"
  echo "[musl] source: $MUSL_SRC"
  echo "[musl] build: $BUILD_DIR"
  echo "[musl] install: $INSTALL_DIR"
  echo "[musl] sysroot: $SYSROOT"
  echo "[musl] jobs: $JOBS"
  echo "[musl] configure optimize flag: $MUSL_OPTIMIZE"
} > "$summary_log"

M1=FAIL
M2=FAIL
M3=FAIL

{
  echo "[M1] configure"
  cd "$BUILD_DIR"
  "$MUSL_SRC/configure" \
    --target="$TARGET" \
    --prefix=/usr \
    --syslibdir=/lib \
    "$MUSL_OPTIMIZE" \
    CC="$CLANG -target $TARGET --sysroot=$SYSROOT -fuse-ld=lld" \
    AR="$LLVM_AR" \
    RANLIB="$LLVM_RANLIB"
} 2>&1 | tee "$configure_log"
M1=PASS

echo "M1=$M1" | tee -a "$summary_log"

set +e
{
  echo "[M2] build static libc"
  cd "$BUILD_DIR"
  "$GNU_MAKE" -j"$JOBS" lib/libc.a
} 2>&1 | tee "$m2_log"
m2_rc=${PIPESTATUS[0]}
set -e

if [[ $m2_rc -eq 0 && -f "$BUILD_DIR/lib/libc.a" ]]; then
  cp -f "$BUILD_DIR/lib/libc.a" "$INSTALL_DIR/lib/libc.a"
  M2=PASS
else
  M2=BLOCKED
fi

echo "M2=$M2" | tee -a "$summary_log"

if [[ "$M2" != PASS ]]; then
  {
    echo "M2 blocker: static libc build failed."
    echo "Command exit code: $m2_rc"
    echo "See: $m2_log"
  } >> "$summary_log"
  echo "musl bring-up failed before mandatory gates completed" | tee -a "$summary_log"
  exit 1
fi

set +e
{
  echo "[M3] attempt shared libc"
  cd "$BUILD_DIR"
  "$GNU_MAKE" -j"$JOBS" lib/libc.so
} 2>&1 | tee "$m3_log"
m3_rc=${PIPESTATUS[0]}
set -e

if [[ $m3_rc -eq 0 && -f "$BUILD_DIR/lib/libc.so" ]]; then
  cp -f "$BUILD_DIR/lib/libc.so" "$INSTALL_DIR/lib/libc.so"
  M3=PASS
else
  M3=BLOCKED
  {
    echo "M3 blocker: shared libc build did not complete."
    echo "Command exit code: $m3_rc"
    echo "See: $m3_log"
  } >> "$summary_log"
fi

echo "M3=$M3" | tee -a "$summary_log"

echo "musl bring-up mandatory gates passed (M1+M2)." | tee -a "$summary_log"
if [[ "$M3" = BLOCKED ]]; then
  echo "musl shared-lib gate blocked; see $m3_log" | tee -a "$summary_log"
fi
