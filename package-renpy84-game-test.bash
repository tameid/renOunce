#!/usr/bin/env bash
# Bundle a minimal game into a separate Ren'Py 8.4.1 hardware-test NRO.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
WORK="$ROOT/build-renpy8/8.4.1"
PYTHON="$ROOT/build-python312"
ROMFS="$WORK/game-test-romfs"
export DEVKITPRO=${DEVKITPRO:-/opt/devkitpro}
rm -rf "$ROMFS"
mkdir -p "$ROMFS/Contents/game"
cp -a "$PYTHON/romfs/Contents/." "$ROMFS/Contents/"
cp -a "$ROOT/switch/python3/test-game/." "$ROMFS/Contents/game/"
source "$DEVKITPRO/switch2vars.sh"
cmake -S "$ROOT/switch/python3" -B "$WORK/game-test" \
    -DRENONCE_PYTHON3_INCLUDE="$PYTHON/Python-3.12.8/Include" \
    -DRENONCE_PYTHON3_CONFIG_INCLUDE="$PYTHON/switch2-horizon" \
    -DRENONCE_PYTHON3_ARCHIVE="$PYTHON/switch2-horizon/libpython3.12.a" \
    -DRENONCE_PYTHON3_ROMFS="$ROMFS" \
    -DRENONCE_EXTENSION_ARCHIVE="$WORK/librenpy84-switch2.a" \
    -DRENONCE_MODULE_TABLE="$ROOT/build-module-tables/renpy84.c" \
    -DRENONCE_GAME_ID=renpy-8.4.1-test \
    -DRENONCE_ENGINE_BOOT=ON -DRENONCE_PACKAGE_PROBE=ON
LINK_CMD="$WORK/game-test/CMakeFiles/renounce-python3.dir/link.txt"
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
rm -f "$WORK/game-test/renounce-python3.nro"
cmake --build "$WORK/game-test" -j "$(nproc)"
OUTPUT="$WORK/renounce-renpy-8.4.1-game-test.nro"
cp "$WORK/game-test/renounce-python3.nro" "$OUTPUT"
printf 'Game-test NRO: %s\n' "$OUTPUT"
