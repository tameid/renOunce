#!/usr/bin/env bash
# Compile official Ren'Py 8.4.1 + pygame_sdl2 Cython output for Switch 2.
# Run after extracting the official archives and generating static C modules.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
WORK="$ROOT/build-renpy8/8.4.1"
RENPY="$WORK/renpy-8.4.1-source"
PYGAME="$WORK/pygame_sdl2-2.1.0+renpy8.4.1"
PYTHON="$ROOT/build-python312"
SDK=${DEVKITPRO:-/opt/devkitpro}
CC="$SDK/devkitA64/bin/aarch64-none-elf-gcc"
CXX="$SDK/devkitA64/bin/aarch64-none-elf-g++"
AR="$SDK/devkitA64/bin/aarch64-none-elf-ar"
ASSIMP="$WORK/assimp/assimp-5.2.5"
test -f "$WORK/assimp/build-5.2.5/lib/libassimp.a"
test -f "$PYTHON/switch2-horizon/pyconfig.h"
grep -q $'^MACHDEP=\thorizon$' "$PYTHON/switch2-horizon/Makefile" || {
    echo "Python target platform is not horizon" >&2; exit 1;
}
test -d "$RENPY/tmp/gen3-static"
test -d "$PYGAME/gen3-static"
if ! test -f "$RENPY/src/libhydrogen/impl/random/switch2.h"; then
    patch -d "$RENPY" -p1 < "$ROOT/patches/renpy8-switch2-rng.patch"
fi
mkdir -p "$WORK/include/pygame_sdl2" "$WORK/objects" "$WORK/pygame-objects"
cp "$PYGAME"/gen3-static/*.h "$WORK/include/pygame_sdl2/"
flags=(-O2 -fPIC -D__SWITCH2__ -DSSIZE_MAX=0x7fffffffffffffffL
    -I"$PYTHON/Python-3.12.8/Include" -I"$PYTHON/switch2-horizon"
    -I"$WORK/include" -I"$RENPY/src" -I"$PYGAME/src"
    -I"$SDK/portlibs/switch/include" -I"$SDK/portlibs/switch/include/SDL2"
    -I"$SDK/portlibs/switch/include/freetype2" -I"$SDK/libounce/include")
for file in "$RENPY"/tmp/gen3-static/*.c; do
    name=$(basename "$file" .c)
    "$CC" "${flags[@]}" -I"$RENPY" -c "$file" -o "$WORK/objects/$name.o"
done
"$CXX" "${flags[@]}" -std=gnu++17 -I"$RENPY" \
    -I"$ASSIMP/include" -I"$WORK/assimp/build-5.2.5/include" \
    -c "$RENPY/tmp/gen3-static/renpy.gl2.assimp.cc" \
    -o "$WORK/objects/renpy.gl2.assimp.o"
"$CXX" "${flags[@]}" -std=gnu++17 -I"$RENPY" \
    -I"$ASSIMP/include" -I"$WORK/assimp/build-5.2.5/include" \
    -c "$RENPY/src/assimpio.cc" -o "$WORK/objects/native-assimpio.o"
for name in IMG_savepng.c core.c ffmedia.c ftsupport.c renpybidicore.c renpysound_core.c ttgsubtable.c; do
    "$CC" "${flags[@]}" -I"$RENPY" -c "$RENPY/src/$name" -o "$WORK/objects/native-${name//\//.}.o"
done
for file in "$PYGAME"/gen3-static/*.c; do
    name=$(basename "$file" .c)
    "$CC" "${flags[@]}" -I"$PYGAME" -c "$file" -o "$WORK/pygame-objects/$name.o"
done
for name in alphablit.c write_jpeg.c write_png.c SDL2_rotozoom.c SDL_gfxPrimitives.c; do
    "$CC" "${flags[@]}" -I"$PYGAME" -c "$PYGAME/src/$name" -o "$WORK/pygame-objects/native-$name.o"
done
"$AR" rcs "$WORK/librenpy84-switch2.a" "$WORK"/objects/*.o "$WORK"/pygame-objects/*.o
printf 'Built %s\n' "$WORK/librenpy84-switch2.a"
