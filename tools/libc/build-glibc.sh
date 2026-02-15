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

need_cmd() {
  local tool="$1"
  command -v "$tool" >/dev/null 2>&1 || {
    echo "error: missing required tool: $tool" >&2
    exit 2
  }
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

TARGET="${TARGET:-linx64-unknown-linux-gnu}"
LLVM_BUILD="${LLVM_BUILD:-/Users/zhoubot/llvm-project/build-linxisa-clang}"
SYSROOT="${SYSROOT:-/Users/zhoubot/toolchains/cross/linx64/sysroot}"
GLIBC_SRC="${GLIBC_SRC:-$repo_root/lib/glibc}"
OUT_ROOT="${OUT_ROOT:-$repo_root/out/libc/glibc}"
BUILD_DIR="${BUILD_DIR:-$OUT_ROOT/build}"
INSTALL_DIR="${INSTALL_DIR:-$OUT_ROOT/install}"
LOG_DIR="${LOG_DIR:-$OUT_ROOT/logs}"
linux_src_was_default=0
if [[ -z "${LINUX_SRC+x}" ]]; then
  linux_src_was_default=1
fi
LINUX_SRC="${LINUX_SRC:-$SYSROOT/src/linux-6.1}"
LINUX_HDRS="${LINUX_HDRS:-$OUT_ROOT/linux-headers}"
JOBS="${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 8)}"

LLVM_BUILD="$(expand_path "$LLVM_BUILD")"
SYSROOT="$(expand_path "$SYSROOT")"
GLIBC_SRC="$(expand_path "$GLIBC_SRC")"
OUT_ROOT="$(expand_path "$OUT_ROOT")"
BUILD_DIR="$(expand_path "$BUILD_DIR")"
INSTALL_DIR="$(expand_path "$INSTALL_DIR")"
LOG_DIR="$(expand_path "$LOG_DIR")"
LINUX_SRC="$(expand_path "$LINUX_SRC")"
LINUX_HDRS="$(expand_path "$LINUX_HDRS")"

if [[ ! -d "$SYSROOT" ]]; then
  fallback_sysroot="/Users/zhoubot/sysroots/linx64-linux-gnu"
  if [[ -d "$fallback_sysroot" ]]; then
    SYSROOT="$fallback_sysroot"
    if (( linux_src_was_default )); then
      LINUX_SRC="$fallback_sysroot/src/linux-6.1"
    fi
  else
    echo "error: sysroot dir missing: $SYSROOT" >&2
    exit 2
  fi
fi

CLANG="$LLVM_BUILD/bin/clang"
CLANGXX="$LLVM_BUILD/bin/clang++"
LLD="$LLVM_BUILD/bin/ld.lld"
LLVM_AR="$LLVM_BUILD/bin/llvm-ar"
LLVM_RANLIB="$LLVM_BUILD/bin/llvm-ranlib"
LLVM_NM="$LLVM_BUILD/bin/llvm-nm"
LLVM_OBJCOPY="$LLVM_BUILD/bin/llvm-objcopy"
LLVM_OBJDUMP="$LLVM_BUILD/bin/llvm-objdump"
LLVM_STRIP="$LLVM_BUILD/bin/llvm-strip"

for tool in "$CLANG" "$CLANGXX" "$LLD" "$LLVM_AR" "$LLVM_RANLIB" "$LLVM_NM" "$LLVM_OBJCOPY" "$LLVM_OBJDUMP" "$LLVM_STRIP"; do
  [[ -x "$tool" ]] || { echo "error: missing required llvm tool: $tool" >&2; exit 2; }
done

GNU_MAKE="${GNU_MAKE:-$(pick_cmd /opt/homebrew/bin/gmake gmake make || true)}"
GNU_SED="${GNU_SED:-$(pick_cmd /opt/homebrew/bin/gsed gsed sed || true)}"
BISON="${BISON:-$(pick_cmd /opt/homebrew/opt/bison/bin/bison bison || true)}"
READELF="${READELF:-$(pick_cmd /opt/homebrew/opt/binutils/bin/readelf readelf || true)}"

[[ -n "$GNU_MAKE" ]] || { echo "error: unable to locate gmake/make" >&2; exit 2; }
[[ -n "$GNU_SED" ]] || { echo "error: unable to locate gsed/sed" >&2; exit 2; }
[[ -n "$BISON" ]] || { echo "error: unable to locate bison" >&2; exit 2; }
[[ -n "$READELF" ]] || { echo "error: unable to locate readelf" >&2; exit 2; }

need_cmd "$GNU_MAKE"
need_cmd "$GNU_SED"
need_cmd "$BISON"
need_cmd "$READELF"

[[ -d "$GLIBC_SRC" ]] || { echo "error: glibc source dir missing: $GLIBC_SRC" >&2; exit 2; }
[[ -d "$LINUX_SRC" ]] || { echo "error: linux source dir missing: $LINUX_SRC" >&2; exit 2; }

mkdir -p "$OUT_ROOT" "$LOG_DIR" "$INSTALL_DIR/lib"
rm -rf "$BUILD_DIR" "$LINUX_HDRS"
mkdir -p "$BUILD_DIR" "$LINUX_HDRS"

tool_wrappers="$OUT_ROOT/tools"
mkdir -p "$tool_wrappers"
cat > "$tool_wrappers/gnumake" <<WRAP
#!/bin/sh
exec "$GNU_MAKE" "\$@"
WRAP
cat > "$tool_wrappers/sed" <<WRAP
#!/bin/sh
exec "$GNU_SED" "\$@"
WRAP
cat > "$tool_wrappers/bison" <<WRAP
#!/bin/sh
exec "$BISON" "\$@"
WRAP
cat > "$tool_wrappers/yacc" <<WRAP
#!/bin/sh
exec "$BISON" "\$@"
WRAP
cat > "$tool_wrappers/readelf" <<WRAP
#!/bin/sh
exec "$READELF" "\$@"
WRAP
chmod +x "$tool_wrappers/gnumake" "$tool_wrappers/sed" "$tool_wrappers/bison" "$tool_wrappers/yacc" "$tool_wrappers/readelf"

export PATH="$tool_wrappers:$PATH"
export MAKEINFO=:

headers_log="$LOG_DIR/01-linux-headers.log"
configure_log="$LOG_DIR/02-configure.log"
build_log="$LOG_DIR/03-build.log"
summary_log="$LOG_DIR/summary.txt"

{
  echo "[glibc] target: $TARGET"
  echo "[glibc] using linker flag: -fuse-ld=lld"
  echo "[glibc] source: $GLIBC_SRC"
  echo "[glibc] build: $BUILD_DIR"
  echo "[glibc] install: $INSTALL_DIR"
  echo "[glibc] sysroot: $SYSROOT"
  echo "[glibc] linux source: $LINUX_SRC"
  echo "[glibc] linux headers output: $LINUX_HDRS"
  echo "[glibc] jobs: $JOBS"
} > "$summary_log"

{
  echo "[1/4] Installing Linux UAPI headers (ARCH=riscv stand-in)"
  "$GNU_MAKE" -C "$LINUX_SRC" ARCH=riscv headers_install INSTALL_HDR_PATH="$LINUX_HDRS"
} 2>&1 | tee "$headers_log"

host_triple="$($CLANG -dumpmachine)"

set +e
{
  echo "[2/4] Configuring glibc"
  cd "$BUILD_DIR"
  "$GLIBC_SRC/configure" \
    --host="$TARGET" \
    --build="$host_triple" \
    --prefix=/usr \
    --with-headers="$LINUX_HDRS/include" \
    --disable-werror \
    --disable-nscd \
    --disable-timezone-tools \
    CC="$CLANG -target $TARGET --sysroot=$SYSROOT -fuse-ld=lld" \
    CXX="$CLANGXX -target $TARGET --sysroot=$SYSROOT -fuse-ld=lld" \
    LD="$LLD" \
    AR="$LLVM_AR" \
    RANLIB="$LLVM_RANLIB" \
    NM="$LLVM_NM" \
    OBJCOPY="$LLVM_OBJCOPY" \
    OBJDUMP="$LLVM_OBJDUMP" \
    STRIP="$LLVM_STRIP" \
    READELF="$READELF" \
    CFLAGS="-O2 -g" \
    CPPFLAGS="-U_FORTIFY_SOURCE" \
    LDFLAGS="-fuse-ld=lld"
} 2>&1 | tee "$configure_log"
configure_rc=${PIPESTATUS[0]}
set -e

if [[ $configure_rc -ne 0 ]]; then
  {
    echo "glibc gate G1 blocked during configure"
    echo "Command exit code: $configure_rc"
    echo "See: $configure_log"
  } | tee -a "$summary_log"
  exit 1
fi

set +e
{
  echo "[3/4] Building glibc gate targets"
  cd "$BUILD_DIR"
  "$GNU_MAKE" -j"$JOBS" csu/subdir_lib
  "$GNU_MAKE" -j"$JOBS" csu/crt1.o
  "$GNU_MAKE" -j"$JOBS" libc.so
} 2>&1 | tee "$build_log"
build_rc=${PIPESTATUS[0]}
set -e

if [[ $build_rc -ne 0 ]]; then
  {
    echo "glibc gate G1 blocked during build"
    echo "Command exit code: $build_rc"
    echo "See: $build_log"
  } | tee -a "$summary_log"
  exit 1
fi

echo "[4/4] Collecting gate artifacts" | tee -a "$summary_log"
mkdir -p "$INSTALL_DIR/lib"
if [[ -f "$BUILD_DIR/libc.so" ]]; then
  cp -f "$BUILD_DIR/libc.so" "$INSTALL_DIR/lib/"
fi
for crt in crt1.o Scrt1.o rcrt1.o crti.o crtn.o; do
  if [[ -f "$BUILD_DIR/csu/$crt" ]]; then
    cp -f "$BUILD_DIR/csu/$crt" "$INSTALL_DIR/lib/$crt"
  fi
done

missing=0
if [[ ! -f "$INSTALL_DIR/lib/libc.so" ]]; then
  echo "missing artifact: $INSTALL_DIR/lib/libc.so" | tee -a "$summary_log"
  missing=1
fi
if [[ ! -f "$INSTALL_DIR/lib/crt1.o" ]]; then
  echo "missing artifact: $INSTALL_DIR/lib/crt1.o" | tee -a "$summary_log"
  missing=1
fi

if (( missing != 0 )); then
  echo "glibc gate G1 failed; see logs in $LOG_DIR" | tee -a "$summary_log"
  exit 1
fi

echo "glibc gate G1 passed" | tee -a "$summary_log"
