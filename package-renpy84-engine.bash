#!/usr/bin/env bash
# Package an engine-only Ren'Py 8.4.1 NRO from the bundled SDK assets.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
WORK="$ROOT/build-renpy8/8.4.1"
PYTHON="$ROOT/build-python312"
export DEVKITPRO=${DEVKITPRO:-/opt/devkitpro}
source "$DEVKITPRO/switch2vars.sh"
cmake -S "$ROOT/switch/python3" -B "$WORK/engine-boot" \
    -DRENONCE_PYTHON3_INCLUDE="$PYTHON/Python-3.12.8/Include" \
    -DRENONCE_PYTHON3_CONFIG_INCLUDE="$PYTHON/switch2-horizon" \
    -DRENONCE_PYTHON3_ARCHIVE="$PYTHON/switch2-horizon/libpython3.12.a" \
    -DRENONCE_PYTHON3_ROMFS="$PYTHON/romfs" \
    -DRENONCE_EXTENSION_ARCHIVE="$WORK/librenpy84-switch2.a" \
    -DRENONCE_MODULE_TABLE="$ROOT/build-module-tables/renpy84.c" \
    -DRENONCE_GAME_ID=renpy-8.4.1-engine \
    -DRENONCE_ENGINE_BOOT=ON -DRENONCE_PACKAGE_PROBE=ON
LINK_CMD="$WORK/engine-boot/CMakeFiles/renounce-python3.dir/link.txt"
grep -Fq -- "-specs=$DEVKITPRO/libounce/switch.specs" "$LINK_CMD"
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
rm -f "$WORK/engine-boot/renounce-python3.nro"
cmake --build "$WORK/engine-boot" -j "$(nproc)"
OUTPUT="$WORK/renounce-renpy-8.4.1-engine-test.nro"
cp "$WORK/engine-boot/renounce-python3.nro" "$OUTPUT"
printf 'Engine-test NRO: %s\n' "$OUTPUT"
