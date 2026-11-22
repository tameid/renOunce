#!/usr/bin/env bash
# Build an engine-only NRO for one version. The target manifest is authoritative.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
VERSION=${1:?Usage: build-engine.bash VERSION}
case "$VERSION" in
    7.6.1|8.4.1|8.6.1) ;;
    *) echo "Unknown Ren'Py target: $VERSION" >&2; exit 2 ;;
esac
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
mkdir -p "$WORK/romfs/Contents" "$ROOT/dist/$VERSION"
cp -a raw/switch/romfs/. "$WORK/romfs/"
rm -rf "$WORK/romfs/Contents/game"
cmake -S switch -B "$WORK/build" -DCMAKE_BUILD_TYPE=Release \
    -DRENONCE_PYTHON_ARCHIVE="$ROOT/build-python27/source-build/libpython2.7-switch2.a" \
    -DRENONCE_RENPY_ARCHIVE="$ROOT/build-python27/renpy-modules/librenpy-switch-modules.a" \
    -DSWITCH_APP_NAME="renOunce Ren'Py $VERSION" -DSWITCH_AUTHOR=renOunce \
    -DSWITCH_VERSION="$VERSION" -DSWITCH_GAME_ID="engine-$VERSION" \
    -DSWITCH_ROMFS="$WORK/romfs"
cmake --build "$WORK/build" -j "$(nproc)"
cp "$WORK/build/renpy-switch.nro" "$ROOT/dist/$VERSION/renounce-renpy-$VERSION.nro"
