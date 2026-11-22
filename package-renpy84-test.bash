#!/usr/bin/env bash
# Explicitly package the audited Python 3.12 + Ren'Py 8.4.1 link probe.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
WORK="$ROOT/build-renpy8/8.4.1"
export DEVKITPRO=${DEVKITPRO:-/opt/devkitpro}
bash "$ROOT/link-renpy84-probe.bash"
source "$DEVKITPRO/switch2vars.sh"
cmake -S "$ROOT/switch/python3" -B "$WORK/link-probe-audited" \
    -DRENONCE_PACKAGE_PROBE=ON
LINK_CMD="$WORK/link-probe-audited/CMakeFiles/renounce-python3.dir/link.txt"
for forbidden in \
    "$DEVKITPRO/libnx/lib/libnx.a" \
    "$DEVKITPRO/portlibs/switch/lib/libEGL.a" \
    "$DEVKITPRO/portlibs/switch/lib/libglapi.a" \
    "$DEVKITPRO/portlibs/switch/lib/libdrm_nouveau.a"; do
    if grep -Fq "$forbidden" "$LINK_CMD"; then
        echo "Unsafe Switch 1 library in link command: $forbidden" >&2
        exit 1
    fi
done
rm -f "$WORK/link-probe-audited/renounce-python3.nro"
cmake --build "$WORK/link-probe-audited" -j "$(nproc)"
OUTPUT="$WORK/renounce-renpy-8.4.1-boot-test.nro"
cp "$WORK/link-probe-audited/renounce-python3.nro" "$OUTPUT"
printf 'Boot-test NRO: %s\nLog: renounce/<ID>/Logs/python3-boot.log beside the NRO\n' "$OUTPUT"
