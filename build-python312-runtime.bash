#!/usr/bin/env bash
# Cross-compile CPython 3.11 for Switch 2 (static core only).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
WORK="$ROOT/build-python312"
VERSION=3.12.8
export DEVKITPRO=${DEVKITPRO:-/opt/devkitpro}
mkdir -p "$WORK/host" "$WORK/switch2-horizon"
if [ ! -f "$WORK/Python-$VERSION.tgz" ]; then
    curl -fsSL "https://www.python.org/ftp/python/$VERSION/Python-$VERSION.tgz" \
        -o "$WORK/Python-$VERSION.tgz"
fi
if [ ! -d "$WORK/Python-$VERSION" ]; then
    tar -xzf "$WORK/Python-$VERSION.tgz" -C "$WORK"
fi
if ! grep -q 'The console has no /dev/urandom' \
    "$WORK/Python-$VERSION/Python/bootstrap_hash.c"; then
    patch -d "$WORK/Python-$VERSION" -p1 < \
        "$ROOT/patches/cpython312-switch2-rng.patch"
fi
if ! grep -q '"wasi", "horizon"' "$WORK/Python-$VERSION/Lib/subprocess.py"; then
    patch -d "$WORK/Python-$VERSION" -p1 < \
        "$ROOT/patches/cpython312-horizon-subprocess.patch"
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
export MACHDEP=horizon ac_cv_func_fork=no ac_cv_func_sem_open=no
export ac_cv_func_pthread_getcpuclockid=no
export ac_cv_func_chroot=no ac_cv_func_fchdir=no
export ac_cv_func_fdatasync=no ac_cv_func_setgroups=no
(cd "$WORK/switch2-horizon" && ../"Python-$VERSION"/configure \
    --build=x86_64-pc-linux-gnu --host=aarch64-none-linux-gnu \
    --with-build-python="$WORK/host/python" --disable-shared \
    --without-ensurepip --disable-ipv6 &&
    cat > Modules/Setup.local <<'MODULES'
*static*
array arraymodule.c
_bisect _bisectmodule.c
_csv _csv.c
_heapq _heapqmodule.c
_json _json.c
_opcode _opcode.c
_pickle _pickle.c
_queue _queuemodule.c
_random _randommodule.c
_struct _struct.c
audioop audioop.c
math mathmodule.c
cmath cmathmodule.c
_statistics _statisticsmodule.c
_datetime _datetimemodule.c
binascii binascii.c
zlib zlibmodule.c -lz
_bz2 _bz2module.c -lbz2
unicodedata unicodedata.c
select selectmodule.c
_socket socketmodule.c
_md5 md5module.c -I$(srcdir)/Modules/_hacl/include _hacl/Hacl_Hash_MD5.c -D_BSD_SOURCE -D_DEFAULT_SOURCE
_sha1 sha1module.c -I$(srcdir)/Modules/_hacl/include _hacl/Hacl_Hash_SHA1.c -D_BSD_SOURCE -D_DEFAULT_SOURCE
_sha2 sha2module.c -I$(srcdir)/Modules/_hacl/include _hacl/Hacl_Hash_SHA2.c -D_BSD_SOURCE -D_DEFAULT_SOURCE
_sha3 sha3module.c -I$(srcdir)/Modules/_hacl/include _hacl/Hacl_Hash_SHA3.c -D_BSD_SOURCE -D_DEFAULT_SOURCE
_blake2 _blake2/blake2module.c _blake2/blake2b_impl.c _blake2/blake2s_impl.c
MODULES
    make -j "$(nproc)" libpython3.12.a)
printf 'Archive: %s\nHeaders: %s and %s\n' \
    "$WORK/switch2-horizon/libpython3.12.a" "$WORK/Python-$VERSION/Include" "$WORK/switch2-horizon"

# Keep the Python 3 probe romfs independent of the Ren'Py 7/Python 2 template.
mkdir -p "$WORK/romfs/Contents"
python3 - "$WORK/Python-$VERSION/Lib" "$WORK/romfs/Contents/lib.zip" <<'PYZIP'
from pathlib import Path
import sys
import zipfile
source, destination = map(Path, sys.argv[1:])
# zipimport starts before optional zlib is available in the static interpreter.
with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_STORED) as archive:
    for file in source.rglob('*.py'):
        relative = file.relative_to(source)
        if any(part in {'test', 'tests', 'idlelib', 'tkinter', 'turtledemo'} for part in relative.parts):
            continue
        archive.write(file, relative.as_posix())
PYZIP
printf 'ROMFS: %s\n' "$WORK/romfs"
