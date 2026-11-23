#!/usr/bin/env bash
# Complete a staged Ren'Py 7.6.1 lib.zip with Python-only runtime modules.
# Usage: bash prepare-libzip.bash LIB_ZIP WORK_DIR
set -euo pipefail
ZIP=$(realpath "$1")
mkdir -p "$2"
WORK=$(realpath "$2")
REPO=$(cd "$(dirname "$0")" && pwd)

PYGAME_PY="$REPO/pygame_sdl2-source/src/pygame_sdl2"
SDK_PY="$REPO/raw/renpy_clear/lib/python2.7"
if [ ! -f "$PYGAME_PY/__init__.py" ] || [ ! -f "$SDK_PY/builtins/__init__.pyo" ]; then
    echo "prepare-libzip: Python runtime sources missing; run setup.bash and build.bash first" >&2
    exit 1
fi
mkdir -p "$WORK/python2.7/pygame_sdl2/threads"
cp "$PYGAME_PY"/*.py "$WORK/python2.7/pygame_sdl2/"
cp "$PYGAME_PY"/threads/*.py "$WORK/python2.7/pygame_sdl2/threads/"
for package in builtins future past ecdsa requests certifi chardet idna urllib3 pyasn1 rsa copyreg html http ordlookup reprlib socketserver winreg; do
    if [ -d "$SDK_PY/$package" ]; then
        cp -r "$SDK_PY/$package" "$WORK/python2.7/"
    fi
done
for module in six.pyo typing.pyo pefile.pyo list2cmdline.pyo; do
    if [ -f "$SDK_PY/$module" ]; then
        cp "$SDK_PY/$module" "$WORK/python2.7/"
    fi
done
(cd "$WORK" && 7z a -tzip "$ZIP" python2.7) >/dev/null
unzip -tq "$ZIP" >/dev/null
unzip -Z1 "$ZIP" | grep -x 'python2.7/pygame_sdl2/__init__.py' >/dev/null
unzip -Z1 "$ZIP" | grep -x 'python2.7/builtins/__init__.pyo' >/dev/null
