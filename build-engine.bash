#!/usr/bin/env bash
# Build an engine-only NRO for one version. The target manifest is authoritative.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
VERSION=${1:?Usage: build-engine.bash VERSION}
if [ "$VERSION" = 8.4.1 ]; then
    bash "$ROOT/build-renpy84-ci.bash"
    mkdir -p "$ROOT/dist/8.4.1"
    cp "$ROOT/build-renpy8/8.4.1/renounce-renpy-8.4.1.nro" \
       "$ROOT/dist/8.4.1/renounce-renpy-8.4.1.nro"
    exit 0
fi
[ -f "$ROOT/targets/$VERSION/target.env" ] || { echo "Unknown Ren'Py target: $VERSION" >&2; exit 2; }
# shellcheck source=/dev/null
source "$ROOT/targets/$VERSION/target.env"
if [ "$STATUS" != buildable ]; then
    echo "Ren'Py $VERSION needs a Python $PYTHON_MAJOR Switch 2 port; the current launcher and C modules use Python 2.7. No NRO will be published for this target." >&2
    exit 2
fi
cd "$ROOT"
[ -f raw/switch/romfs/Contents/lib.zip ] || { echo "Run setup.bash and build.bash first" >&2; exit 1; }
[ -f build-python27/source-build/libpython2.7-switch2.a ] || { echo "Run build-switch2-runtime.bash first" >&2; exit 1; }
[ -f build-python27/renpy-modules/librenpy-switch-modules.a ] || { echo "Run build-switch2-runtime.bash first" >&2; exit 1; }
export DEVKITPRO=${DEVKITPRO:-/opt/devkitpro}
source "$DEVKITPRO/switch2vars.sh"
WORK="$ROOT/build-engine-$VERSION"
rm -rf "$WORK"
mkdir -p "$WORK/romfs/Contents" "$ROOT/dist/$VERSION"
cp -a raw/switch/romfs/. "$WORK/romfs/"
rm -rf "$WORK/romfs/Contents/game"
rm -f "$WORK/romfs/Contents/renounce-game-id"
bash "$ROOT/prepare-libzip.bash" "$WORK/romfs/Contents/lib.zip" "$WORK/libzip"
cmake -S switch -B "$WORK/build" -DCMAKE_BUILD_TYPE=Release \
    -DRENONCE_PYTHON_ARCHIVE="$ROOT/build-python27/source-build/libpython2.7-switch2.a" \
    -DRENONCE_RENPY_ARCHIVE="$ROOT/build-python27/renpy-modules/librenpy-switch-modules.a" \
    -DSWITCH_APP_NAME="renOunce Ren'Py $VERSION" -DSWITCH_AUTHOR=renOunce \
    -DSWITCH_VERSION="$VERSION" -DSWITCH_GAME_ID="engine-$VERSION" \
    -DSWITCH_ROMFS="$WORK/romfs"
cmake --build "$WORK/build" -j "$(nproc)"
cp "$WORK/build/renpy-switch.nro" "$ROOT/dist/$VERSION/renounce-renpy-$VERSION.nro"
