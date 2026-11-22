#!/usr/bin/env bash
# Rebuild the Python 3.12 runtime, official SDK assets, extensions and boot NRO.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
CONTAINER=${RENONCE_CONTAINER:-renounce-dev}
HOST_PYTHON=${RENONCE_HOST_PYTHON:-"$ROOT/build-renpy8/venv315/bin/python"}
HOST_CYTHON=${RENONCE_HOST_CYTHON:-/usr/bin/cython}
test -x "$HOST_PYTHON" || { echo "Host Python with setuptools required: $HOST_PYTHON" >&2; exit 1; }
test -x "$HOST_CYTHON" || { echo "Host Cython required: $HOST_CYTHON" >&2; exit 1; }

podman exec -w /work "$CONTAINER" bash prepare-renpy8-sdk.bash 8.4.1
podman exec "$CONTAINER" chmod -R a+rwX \
    /work/build-renpy8/8.4.1/renpy-8.4.1-source \
    /work/build-renpy8/8.4.1/pygame_sdl2-2.1.0+renpy8.4.1

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
(cd "$RENPY" && RENPY_STATIC=1 RENPY_CYTHON_SINGLETHREAD=1 \
    RENPY_CYTHON="$HOST_CYTHON" "$HOST_PYTHON" setup.py --help >/dev/null)
(cd "$PYGAME" && PATH="$ROOT/build-renpy8/tool-bin:$PATH" \
    VIRTUAL_ENV=$(dirname "$(dirname "$HOST_PYTHON")") \
    PYGAME_SDL2_STATIC=1 "$HOST_PYTHON" setup.py --help >/dev/null)

podman exec -w /work "$CONTAINER" bash build-python312-runtime.bash
python3 "$ROOT/stage-renpy84-sdk.py"
podman exec -w /work "$CONTAINER" bash -lc \
    'export PATH=/opt/devkitpro/pacman/bin:$PATH; pacman -S --needed --noconfirm switch-harfbuzz switch-freetype'
podman exec -w /work "$CONTAINER" bash build-assimp-switch2.bash
podman exec -w /work "$CONTAINER" bash build-renpy84-extensions.bash
python3 "$ROOT/stage-renpy84-sdk.py"
podman exec -w /work "$CONTAINER" python3 switch/python3/generate_module_table.py 8.4.1 build-module-tables/renpy84.c
python3 "$ROOT/audit-renpy84-imports.py"
podman exec -w /work "$CONTAINER" bash package-renpy84-test.bash
podman exec -w /work "$CONTAINER" bash package-renpy84-engine.bash
podman exec -w /work "$CONTAINER" bash package-renpy84-game-test.bash
