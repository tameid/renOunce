#!/usr/bin/env bash
# Build the Ren'Py 8.4.1 release in the CI container.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
cd "$ROOT"
export DEVKITPRO=${DEVKITPRO:-/opt/devkitpro}
HOST_PYTHON=${RENONCE_HOST_PYTHON:-python3}
HOST_CYTHON=${RENONCE_HOST_CYTHON:-/usr/bin/cython3}
bash prepare-renpy8-sdk.bash 8.4.1
RENPY="$ROOT/build-renpy8/8.4.1/renpy-8.4.1-source"
PYGAME="$ROOT/build-renpy8/8.4.1/pygame_sdl2-2.1.0+renpy8.4.1"
mkdir -p "$ROOT/build-renpy8/tool-bin"
cat > "$ROOT/build-renpy8/tool-bin/sdl2-config" <<'CONFIG'
#!/bin/sh
case "$1" in
    --cflags) echo -I/opt/devkitpro/portlibs/switch/include/SDL2 ;;
    --libs) echo -lSDL2 ;;
esac
CONFIG
chmod +x "$ROOT/build-renpy8/tool-bin/sdl2-config"
(cd "$RENPY" && RENPY_STATIC=1 RENPY_CYTHON_SINGLETHREAD=1 RENPY_CYTHON="$HOST_CYTHON" "$HOST_PYTHON" setup.py --help >/dev/null)
(cd "$PYGAME" && PATH="$ROOT/build-renpy8/tool-bin:$PATH" PYGAME_SDL2_STATIC=1 "$HOST_PYTHON" setup.py --help >/dev/null)
bash build-python312-runtime.bash
python3 stage-renpy84-sdk.py
export PATH="$DEVKITPRO/pacman/bin:$PATH"
pacman -S --needed --noconfirm switch-harfbuzz switch-freetype
bash build-assimp-switch2.bash
bash build-renpy84-extensions.bash
python3 stage-renpy84-sdk.py
python3 switch/python3/generate_module_table.py 8.4.1 build-module-tables/renpy84.c
python3 audit-renpy84-imports.py
bash package-renpy84-release.bash
