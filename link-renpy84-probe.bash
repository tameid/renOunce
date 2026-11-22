#!/usr/bin/env bash
# Link Python 3.12 and statically registered Ren'Py 8.4.1 extensions.
# This is a link probe, not a bootable Ren'Py game engine.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
WORK="$ROOT/build-renpy8/8.4.1"
PYTHON="$ROOT/build-python312"
grep -q $'^MACHDEP=\thorizon$' "$PYTHON/switch2-horizon/Makefile" || {
    echo "Python target platform is not horizon" >&2; exit 1;
}
export DEVKITPRO=${DEVKITPRO:-/opt/devkitpro}
python3 "$ROOT/switch/python3/generate_module_table.py" 8.4.1 \
    "$ROOT/build-module-tables/renpy84.c"
source "$DEVKITPRO/switch2vars.sh"
cmake -S "$ROOT/switch/python3" -B "$WORK/link-probe-audited" \
    -DRENONCE_PYTHON3_INCLUDE="$PYTHON/Python-3.12.8/Include" \
    -DRENONCE_PYTHON3_CONFIG_INCLUDE="$PYTHON/switch2-horizon" \
    -DRENONCE_PYTHON3_ARCHIVE="$PYTHON/switch2-horizon/libpython3.12.a" \
    -DRENONCE_PYTHON3_ROMFS="$PYTHON/romfs" \
    -DRENONCE_EXTENSION_ARCHIVE="$WORK/librenpy84-switch2.a" \
    -DRENONCE_MODULE_TABLE="$ROOT/build-module-tables/renpy84.c" \
    -DRENONCE_PACKAGE_PROBE=OFF
# Reject any accidental Switch 1 libnx/Mesa object before producing an NRO.
LINK_CMD="$WORK/link-probe-audited/CMakeFiles/renounce-python3.dir/link.txt"
COMPILE_FLAGS="$WORK/link-probe-audited/CMakeFiles/renounce-python3.dir/flags.make"
grep -Fq -- "-specs=$DEVKITPRO/libounce/switch.specs" "$LINK_CMD" || {
    echo "Missing libounce linker specs" >&2; exit 1;
}
grep -Fq -- "-D__SWITCH2__" "$COMPILE_FLAGS" || {
    echo "Missing Switch 2 compile definition" >&2; exit 1;
}
for forbidden in \
    "$DEVKITPRO/libnx/lib/libnx.a" \
    "$DEVKITPRO/portlibs/switch/lib/libEGL.a" \
    "$DEVKITPRO/portlibs/switch/lib/libglapi.a" \
    "$DEVKITPRO/portlibs/switch/lib/libdrm_nouveau.a"; do
    if grep -Fq "$forbidden" "$LINK_CMD"; then
        echo "Unsafe Switch 1 library in link command: $forbidden" >&2
        exit 1
    fi
done
cmake --build "$WORK/link-probe-audited" -j "$(nproc)"
cp "$WORK/link-probe-audited/renounce-python3.elf" \
    "$WORK/renounce-renpy-8.4.1-link-only.elf"
