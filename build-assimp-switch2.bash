#!/usr/bin/env bash
# Build Assimp's glTF importer for Ren'Py 8.4.1 on Switch 2.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
WORK="$ROOT/build-renpy8/8.4.1/assimp"
VERSION=5.2.5
export DEVKITPRO=${DEVKITPRO:-/opt/devkitpro}
mkdir -p "$WORK"
if [ ! -f "$WORK/assimp-$VERSION.tar.gz" ]; then
    curl -fsSL "https://github.com/assimp/assimp/archive/refs/tags/v$VERSION.tar.gz" \
        -o "$WORK/assimp-$VERSION.tar.gz"
fi
if [ ! -d "$WORK/assimp-$VERSION" ]; then
    tar -xzf "$WORK/assimp-$VERSION.tar.gz" -C "$WORK"
fi
source "$DEVKITPRO/switch2vars.sh"
cmake -S "$WORK/assimp-$VERSION" -B "$WORK/build-$VERSION" \
    -DCMAKE_TOOLCHAIN_FILE="$DEVKITPRO/libounce/cmake/Switch2.cmake" \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
    -DASSIMP_BUILD_TESTS=OFF -DASSIMP_BUILD_ASSIMP_TOOLS=OFF \
    -DASSIMP_BUILD_ALL_IMPORTERS_BY_DEFAULT=OFF \
    -DASSIMP_BUILD_GLTF_IMPORTER=ON \
    -DASSIMP_BUILD_ALL_EXPORTERS_BY_DEFAULT=OFF \
    -DASSIMP_BUILD_ZLIB=ON -DASSIMP_NO_EXPORT=ON \
    -DASSIMP_WARNINGS_AS_ERRORS=OFF
cmake --build "$WORK/build-$VERSION" -j "$(nproc)"
test -f "$WORK/build-$VERSION/lib/libassimp.a"
printf 'Assimp: %s\n' "$WORK/build-$VERSION/lib/libassimp.a"
