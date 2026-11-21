#!/usr/bin/env bash
# Compile CPython 2.7 and Ren'Py/pygame_sdl2 C modules for Switch 2.
# Run inside the configured build container, then use build-game.bash with
# RENONCE_PYTHON_ARCHIVE and RENONCE_RENPY_ARCHIVE printed at the end.
set -euo pipefail

REPO=$(cd "$(dirname "$0")" && pwd)
export DEVKITPRO="${DEVKITPRO:-/opt/devkitpro}"
WORK="$REPO/build-python27"
PYTHON_VERSION=2.7.18
PYTHON_SHA256=da3080e3b488f648a3d7a4560ddee895284c3380b11d6de75edb986526b9a814

mkdir -p "$WORK"
if [ ! -f "$WORK/Python-$PYTHON_VERSION.tgz" ]; then
    curl -fsSL "https://www.python.org/ftp/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tgz" \
        -o "$WORK/Python-$PYTHON_VERSION.tgz"
fi
printf '%s  %s\n' "$PYTHON_SHA256" "$WORK/Python-$PYTHON_VERSION.tgz" | sha256sum -c -
if [ ! -d "$WORK/Python-$PYTHON_VERSION" ]; then
    tar -xzf "$WORK/Python-$PYTHON_VERSION.tgz" -C "$WORK"
fi

source "$DEVKITPRO/switch2vars.sh"
python3 "$REPO/switch/python27/build.py" \
    --source "$WORK/Python-$PYTHON_VERSION" \
    --output "$WORK/source-build"

# setup.py creates gen-static before parsing commands; its final usage error
# is expected here. Check the generated C files explicitly.
if [ ! -f "$REPO/pygame_sdl2-source/gen-static/pygame_sdl2.color.c" ]; then
    (cd "$REPO/pygame_sdl2-source" && PYGAME_SDL2_STATIC=1 python2 setup.py) || true
fi
test -f "$REPO/pygame_sdl2-source/gen-static/pygame_sdl2.color.c"
if [ ! -f "$REPO/renpy-source/module/gen-static/_renpy.c" ]; then
    (cd "$REPO/renpy-source/module" && \
        RENPY_DEPS_INSTALL=/usr/lib/x86_64-linux-gnu:/usr:/usr/local \
        RENPY_STATIC=1 python2 setup.py) || true
fi
test -f "$REPO/renpy-source/module/gen-static/_renpy.c"

(cd "$REPO" && bash link_sources.bash)
cmake -S "$REPO" -B "$WORK/renpy-modules" \
    -DCMAKE_BUILD_TYPE=Release \
    -DRENONCE_PYTHON_ARCHIVE="$WORK/source-build/libpython2.7-switch2.a"
cmake --build "$WORK/renpy-modules" -j "$(nproc)"

echo "CPython: $WORK/source-build/libpython2.7-switch2.a"
echo "Ren'Py: $WORK/renpy-modules/librenpy-switch-modules.a"
