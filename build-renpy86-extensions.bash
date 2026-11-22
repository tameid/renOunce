#!/usr/bin/env bash
# Compile official Ren'Py 8.6.1 Cython output for Switch 2.
# Assimp is deliberately omitted until its target library is available.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
WORK="$ROOT/build-renpy8/8.6.1"
RENPY="$WORK/renpy-8.6.1-source"
PYTHON="$ROOT/build-python312"
SDK=${DEVKITPRO:-/opt/devkitpro}
SDL3="$ROOT/build-renpy8/SDL3-3.4.20"
SDL3_IMAGE="$ROOT/build-renpy8/SDL3_image-3.4.8"
CC="$SDK/devkitA64/bin/aarch64-none-elf-gcc"
AR="$SDK/devkitA64/bin/aarch64-none-elf-ar"
test -f "$PYTHON/switch2-horizon/pyconfig.h"
grep -q $'^MACHDEP=\thorizon$' "$PYTHON/switch2-horizon/Makefile" || {
    echo "Python target platform is not horizon" >&2; exit 1;
}
test -f "$SDL3/include/SDL3/SDL.h"
test -f "$SDL3_IMAGE/include/SDL3_image/SDL_image.h"
test -d "$RENPY/tmp/gen"
if ! test -f "$RENPY/src/libhydrogen/impl/random/switch2.h"; then
    patch -d "$RENPY" -p1 < "$ROOT/patches/renpy8-switch2-rng.patch"
fi
mkdir -p "$WORK/objects"
flags=(-O2 -fPIC -D__SWITCH2__ -DSSIZE_MAX=0x7fffffffffffffffL
    -I"$PYTHON/Python-3.12.8/Include" -I"$PYTHON/switch2-horizon"
    -I"$SDL3/include" -I"$SDL3_IMAGE/include" -I"$RENPY"
    -I"$RENPY/src" -I"$RENPY/tmp/gen" -I"$SDK/portlibs/switch/include"
    -I"$SDK/portlibs/switch/include/fribidi"
    -I"$SDK/portlibs/switch/include/freetype2" -I"$SDK/libounce/include")
while IFS= read -r file; do
    case "$file" in */renpy/gl2/assimp.c) continue ;; esac
    name=${file#"$RENPY/tmp/gen/"}
    name=${name//\//.}
    name=${name%.c}
    "$CC" "${flags[@]}" -c "$file" -o "$WORK/objects/$name.o"
done < <(find "$RENPY/tmp/gen" -name '*.c' | sort)
for name in core.c ffmedia.c ftsupport.c pygame/SDL3_gfxPrimitives.c \
    pygame/SDL3_rotozoom.c pygame/surface_deallocation.c pygame/write_png.c \
    renpybidicore.c renpysound_core.c ttgsubtable.c; do
    output=${name//\//.}
    "$CC" "${flags[@]}" -c "$RENPY/src/$name" -o "$WORK/objects/native-$output.o"
done
"$AR" rcs "$WORK/librenpy86-core-switch2.a" "$WORK"/objects/*.o
printf 'Built %s (Assimp module and SDL3 libraries still pending)\n' \
    "$WORK/librenpy86-core-switch2.a"
