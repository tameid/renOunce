#!/usr/bin/env bash
# Official SDL3 headers used while compiling Ren'Py 8.6.1 extensions.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
WORK="$ROOT/build-renpy8"
mkdir -p "$WORK"
fetch() {
    local url=$1 archive=$2 digest=$3 directory=$4
    if [ ! -f "$WORK/$archive" ]; then curl -fsSL "$url" -o "$WORK/$archive"; fi
    printf '%s  %s\n' "$digest" "$WORK/$archive" | sha256sum -c -
    if [ ! -d "$WORK/$directory" ]; then tar -xzf "$WORK/$archive" -C "$WORK"; fi
}
fetch https://github.com/libsdl-org/SDL/releases/download/release-3.4.20/SDL3-3.4.20.tar.gz \
    SDL3-3.4.20.tar.gz f3bb06f55bed9557227a700af2ea62e49497ebdf58037732a731a5fb3ef8581f SDL3-3.4.20
fetch https://github.com/libsdl-org/SDL_image/releases/download/release-3.4.8/SDL3_image-3.4.8.tar.gz \
    SDL3_image-3.4.8.tar.gz e8223b424bc7541cf84ffff5cf7e4f24ec3711c60462cb1bd6dc1d7bd7f25477 SDL3_image-3.4.8
