#!/usr/bin/env bash
# Cross-compile CPython 3.11 for Switch 2 (static core only).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
WORK="$ROOT/build-python3"
VERSION=3.11.9
export DEVKITPRO=${DEVKITPRO:-/opt/devkitpro}
mkdir -p "$WORK/host" "$WORK/switch2"
if [ ! -f "$WORK/Python-$VERSION.tgz" ]; then
    curl -fsSL "https://www.python.org/ftp/python/$VERSION/Python-$VERSION.tgz" \
        -o "$WORK/Python-$VERSION.tgz"
fi
if [ ! -d "$WORK/Python-$VERSION" ]; then
    tar -xzf "$WORK/Python-$VERSION.tgz" -C "$WORK"
fi
if [ ! -x "$WORK/host/python" ]; then
    (cd "$WORK/host" && ../"Python-$VERSION"/configure \
        --disable-shared --without-ensurepip && make -j "$(nproc)" python)
fi
source "$DEVKITPRO/switch2vars.sh"
export CFLAGS="$CFLAGS -DSSIZE_MAX=0x7fffffffffffffffL -Dtimezone=_timezone -Ddaylight=_daylight"
export CC="$DEVKITPRO/devkitA64/bin/aarch64-none-elf-gcc"
export AR="$DEVKITPRO/devkitA64/bin/aarch64-none-elf-ar"
export RANLIB="$DEVKITPRO/devkitA64/bin/aarch64-none-elf-ranlib"
export READELF="$DEVKITPRO/devkitA64/bin/aarch64-none-elf-readelf"
export ac_cv_file__dev_ptmx=no ac_cv_file__dev_ptc=no
export ac_cv_header_sys_resource_h=no ac_cv_func_statvfs=no
export ac_cv_func_chroot=no ac_cv_func_fchdir=no
export ac_cv_func_fdatasync=no ac_cv_func_setgroups=no
(cd "$WORK/switch2" && ../"Python-$VERSION"/configure \
    --build=x86_64-pc-linux-gnu --host=aarch64-none-linux-gnu \
    --with-build-python="$WORK/host/python" --disable-shared \
    --without-ensurepip --disable-ipv6 &&
    make -j "$(nproc)" libpython3.11.a)
printf 'Archive: %s\nHeaders: %s and %s\n' \
    "$WORK/switch2/libpython3.11.a" "$WORK/Python-$VERSION/Include" "$WORK/switch2"

# Keep the Python 3 probe romfs independent of the Ren'Py 7/Python 2 template.
mkdir -p "$WORK/romfs/Contents"
python3 - "$WORK/Python-$VERSION/Lib" "$WORK/romfs/Contents/lib.zip" <<'PYZIP'
from pathlib import Path
import sys
import zipfile
source, destination = map(Path, sys.argv[1:])
with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for file in source.rglob('*.py'):
        relative = file.relative_to(source)
        if any(part in {'test', 'tests', 'idlelib', 'tkinter', 'turtledemo'} for part in relative.parts):
            continue
        archive.write(file, relative.as_posix())
PYZIP
printf 'ROMFS: %s\n' "$WORK/romfs"
