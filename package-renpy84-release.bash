#!/usr/bin/env bash
# Package the game-free Ren'Py 8.4.1 engine for distribution.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
WORK="$ROOT/build-renpy8/8.4.1"
PYTHON="$ROOT/build-python312"
ROMFS="$WORK/release-romfs"
export DEVKITPRO=${DEVKITPRO:-/opt/devkitpro}
rm -rf "$ROMFS"
mkdir -p "$ROMFS/Contents"
cp -a "$PYTHON/romfs/Contents/." "$ROMFS/Contents/"
RENONCE_RELEASE_ZIP="$ROMFS/Contents/lib.zip" python3 - <<'PY'
import os
from pathlib import Path
from zipfile import ZipFile
path = Path(os.environ["RENONCE_RELEASE_ZIP"])
temporary = path.with_suffix(".release.zip")
with ZipFile(path) as source, ZipFile(temporary, "w") as output:
    for item in source.infolist():
        if item.filename == "renounce_import_probe.py":
            continue
        output.writestr(item, source.read(item))
temporary.replace(path)
PY
source "$DEVKITPRO/switch2vars.sh"
cmake -S "$ROOT/switch/python3" -B "$WORK/release" \
    -DRENONCE_PYTHON3_INCLUDE="$PYTHON/Python-3.12.8/Include" \
    -DRENONCE_PYTHON3_CONFIG_INCLUDE="$PYTHON/switch2-horizon" \
    -DRENONCE_PYTHON3_ARCHIVE="$PYTHON/switch2-horizon/libpython3.12.a" \
    -DRENONCE_LIBFFI_ARCHIVE="$ROOT/build-libffi/prefix/lib/libffi.a" \
    -DRENONCE_PYTHON3_ROMFS="$ROMFS" \
    -DRENONCE_EXTENSION_ARCHIVE="$WORK/librenpy84-switch2.a" \
    -DRENONCE_MODULE_TABLE="$ROOT/build-module-tables/renpy84.c" \
    -DRENONCE_GAME_ID=renpy-8.4.1-engine \
    -DRENONCE_ENGINE_BOOT=ON -DRENONCE_RELEASE=ON -DRENONCE_PACKAGE_PROBE=ON
LINK_CMD="$WORK/release/CMakeFiles/renounce-python3.dir/link.txt"
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
rm -f "$WORK/release/renounce-python3.nro"
cmake --build "$WORK/release" -j "$(nproc)"
OUTPUT="$WORK/renounce-renpy-8.4.1.nro"
cp "$WORK/release/renounce-python3.nro" "$OUTPUT"
(
    cd "$WORK"
    sha256sum "$(basename "$OUTPUT")" > "$(basename "$OUTPUT").sha256"
)
printf 'Release candidate: %s\n' "$OUTPUT"
