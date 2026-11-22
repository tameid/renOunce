#!/usr/bin/env bash
# Fetch and verify the complete official SDK and sources for each Ren'Py 8 target.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
VERSION=${1:?Usage: prepare-renpy8-sdk.bash 8.4.1|8.6.1}
case "$VERSION" in 8.4.1|8.6.1) ;; *) exit 2 ;; esac
WORK="$ROOT/build-renpy8/$VERSION"
mkdir -p "$WORK"
BASE="https://www.renpy.org/dl/$VERSION"
fetch() {
    local filename=$1 output=$2 digest=$3
    if [ ! -f "$WORK/$output" ]; then
        curl -fsSL "$BASE/$filename" -o "$WORK/$output"
    fi
    printf '%s  %s\n' "$digest" "$WORK/$output" | sha256sum -c -
}
case "$VERSION" in
  8.4.1)
    fetch "renpy-8.4.1-source.tar.bz2" source.tar.bz2 29e185b090a59a2415beeaf29e4067471dfc5d4ff296eb53b63d3954e171f2a1
    fetch "renpy-8.4.1-sdk.tar.bz2" sdk.tar.bz2 7e398814f242b3c4e51b29b9edb7369d1c71434dacdeb2e83445f11addd55076
    fetch "pygame_sdl2-2.1.0+renpy8.4.1.tar.gz" pygame.tar.gz ac05762de19f2799784f23f474170b2dab0b63018b8b151291d6dc8afb8b93f8
    if [ ! -d "$WORK/pygame_sdl2-2.1.0+renpy8.4.1" ]; then
        tar -xzf "$WORK/pygame.tar.gz" -C "$WORK"
    fi
    ;;
  8.6.1)
    fetch "renpy-8.6.1-source.tar.bz2" source.tar.bz2 e270e5ad607cb7d75611621086fa32acb6b7c4785c98b192921e26ff42c6fa38
    fetch "renpy-8.6.1-sdk.tar.bz2" sdk.tar.bz2 4d76d88f690ff7d600218dad3941dfddb88e2104e107367a0600a17364335509
    ;;
esac
if [ ! -d "$WORK/renpy-$VERSION-source" ]; then
    tar -xjf "$WORK/source.tar.bz2" -C "$WORK"
fi
if [ ! -d "$WORK/renpy-$VERSION-sdk" ]; then
    tar -xjf "$WORK/sdk.tar.bz2" -C "$WORK"
fi
printf 'Official Ren\x27Py %s SDK and source ready: %s\n' "$VERSION" "$WORK"
