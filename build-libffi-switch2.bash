#!/usr/bin/env bash
# Build the static libffi dependency used by CPython's _ctypes module.
set -euo pipefail
unset VERSION MAKEFLAGS MFLAGS MAKEOVERRIDES
ROOT=$(cd "$(dirname "$0")" && pwd)
WORK="$ROOT/build-libffi"
LIBFFI_VERSION=3.4.6
SHA256=b0dea9df23c863a7a50e825440f3ebffabd65df1497108e5d437747843895a4e
export DEVKITPRO=${DEVKITPRO:-/opt/devkitpro}
mkdir -p "$WORK"
if [ ! -f "$WORK/libffi-$LIBFFI_VERSION.tar.gz" ]; then
    curl -fsSL "https://github.com/libffi/libffi/releases/download/v$LIBFFI_VERSION/libffi-$LIBFFI_VERSION.tar.gz" \
        -o "$WORK/libffi-$LIBFFI_VERSION.tar.gz"
fi
printf '%s  %s\n' "$SHA256" "$WORK/libffi-$LIBFFI_VERSION.tar.gz" | sha256sum -c -
if [ ! -d "$WORK/libffi-$LIBFFI_VERSION" ]; then
    tar -xzf "$WORK/libffi-$LIBFFI_VERSION.tar.gz" -C "$WORK"
fi
source "$DEVKITPRO/switch2vars.sh"
mkdir -p "$WORK/cross"
if [ ! -f "$WORK/prefix/lib/libffi.a" ]; then
    (cd "$WORK/cross" && \
        CC="$DEVKITPRO/devkitA64/bin/aarch64-none-elf-gcc" \
        CXX="$DEVKITPRO/devkitA64/bin/aarch64-none-elf-g++" \
        CFLAGS="${CFLAGS:-} -fPIC" \
        ../"libffi-$LIBFFI_VERSION"/configure --build=x86_64-pc-linux-gnu \
            --host=aarch64-none-elf --prefix="$WORK/prefix" \
            --disable-shared --enable-static --disable-multi-os-directory && \
        make -j "$(nproc)" && make install)
fi
test -f "$WORK/prefix/lib/libffi.a"
echo "$WORK/prefix/lib/libffi.a"
