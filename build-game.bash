# Builds one game as its own branded Switch 2 NRO.
#
# Usage:
#   ./build-game.bash <game-dir> [--name TITLE] [--author AUTHOR]
#                     [--version VER] [--id SAVE_ID] [--icon ICON.JPG]
#                     [--out DIR]
#
# <game-dir> is a Ren'Py project directory containing a game/ subdirectory.
# The result is dist/<SAVE_ID>.nro with:
#   - the game's files embedded at romfs:/Contents/game/
#   - the game's title/author/icon on the Switch 2 home menu (nacp)
#   - all saves/logs/cache/persistent data in sdmc:/renOunce/<SAVE_ID>/
#
# Name/version default to config.name/config.version from game/options.rpy;
# SAVE_ID defaults to the name with every character outside
# [A-Za-z0-9._-] turned into '_'. Two games must not share a SAVE_ID or
# they will share a save folder.
#
# Requires a prior run of build.bash (engine under raw/switch/romfs and the
# switch/ source tree) and the ounce-devkit installed in $DEVKITPRO
# (see setup.bash).

set -e

export DEVKITPRO="${DEVKITPRO:-/opt/devkitpro}"

GAME_DIR=""
NAME=""
AUTHOR=""
VERSION=""
ICON=""
GAME_ID=""
OUT="dist"

while [ $# -gt 0 ]; do
    case "$1" in
        --name)    NAME="$2"; shift 2;;
        --author)  AUTHOR="$2"; shift 2;;
        --version) VERSION="$2"; shift 2;;
        --icon)    ICON="$2"; shift 2;;
        --id)      GAME_ID="$2"; shift 2;;
        --out)     OUT="$2"; shift 2;;
        -h|--help) grep '^# ' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
        *)
            if [ -z "$GAME_DIR" ]; then
                GAME_DIR="$1"; shift
            else
                echo "build-game.bash: unexpected argument '$1'" >&2
                exit 1
            fi
            ;;
    esac
done

if [ -z "$GAME_DIR" ] || [ ! -d "$GAME_DIR/game" ]; then
    echo "Usage: build-game.bash <game-dir> [--name T] [--author A] [--version V] [--id ID] [--icon I] [--out D]" >&2
    echo "  <game-dir> must be a Ren'Py project directory containing game/" >&2
    exit 1
fi
GAME_DIR=$(realpath "$GAME_DIR")

REPO=$(realpath "$(dirname "$0")")

if [ ! -f "$REPO/raw/switch/romfs/Contents/lib.zip" ] || [ ! -f "$REPO/switch/CMakeLists.txt" ]; then
    echo "build-game.bash: engine not found." >&2
    echo "  Run build.bash first (it produces raw/switch/romfs and the switch/ tree)." >&2
    exit 1
fi

if [ ! -f "$DEVKITPRO/switch2vars.sh" ]; then
    echo "build-game.bash: $DEVKITPRO/switch2vars.sh not found." >&2
    echo "  Install the ounce-devkit (see setup.bash)." >&2
    exit 1
fi

# Best-effort metadata from the game's own options.rpy (--name/--version win).
OPTIONS_RPY="$GAME_DIR/game/options.rpy"
if [ -f "$OPTIONS_RPY" ]; then
    if [ -z "$NAME" ]; then
        NAME=$(grep -m1 -oE "define[[:space:]]+config\.name[[:space:]]*=[[:space:]]*_?\(?(\"[^\"]*\"|'[^']*')" "$OPTIONS_RPY" | sed -E "s/.*[\"'](.*)[\"']$/\1/")
    fi
    if [ -z "$VERSION" ]; then
        VERSION=$(grep -m1 -oE "define[[:space:]]+config\.version[[:space:]]*=[[:space:]]*_?\(?(\"[^\"]*\"|'[^']*')" "$OPTIONS_RPY" | sed -E "s/.*[\"'](.*)[\"']$/\1/")
    fi
fi
[ -n "$NAME" ]    || NAME=$(basename "$GAME_DIR")
[ -n "$VERSION" ] || VERSION="1.0"
[ -n "$AUTHOR" ]  || AUTHOR="renOunce"

# Save folder id: same charset the toolchain bakes into main.c.
if [ -z "$GAME_ID" ]; then
    GAME_ID=$(printf '%s' "$NAME" | tr -c 'A-Za-z0-9._-' '_')
fi
[ -n "$GAME_ID" ] || GAME_ID="game"

if [ -n "$ICON" ]; then
    ICON=$(realpath "$ICON")
    if [ ! -f "$ICON" ]; then
        echo "build-game.bash: icon '$ICON' not found" >&2
        exit 1
    fi
fi

echo "=== building '$NAME' ($VERSION) by $AUTHOR"
echo "    save folder: sdmc:/renOunce/$GAME_ID/"

# Stage the per-game romfs: engine base + this game's files.
WORK="$REPO/build-$GAME_ID"
rm -rf "$WORK"
mkdir -p "$WORK/romfs/Contents/game"
cp -r "$REPO/raw/switch/romfs/." "$WORK/romfs/"
cp -r "$GAME_DIR/game/." "$WORK/romfs/Contents/game/"

# The NRO embeds the romfs at link time, so reconfigure per game.
source "$DEVKITPRO/switch2vars.sh"

rm -rf "$WORK/build"
cmake -S "$REPO/switch" -B "$WORK/build" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DSWITCH_APP_NAME="$NAME" \
    -DSWITCH_AUTHOR="$AUTHOR" \
    -DSWITCH_VERSION="$VERSION" \
    -DSWITCH_GAME_ID="$GAME_ID" \
    -DSWITCH_ROMFS="$WORK/romfs" \
    ${ICON:+-DSWITCH_ICON="$ICON"}
cmake --build "$WORK/build"

mkdir -p "$OUT"
cp "$WORK/build/renpy-switch.nro" "$OUT/$GAME_ID.nro"

echo "=== built $OUT/$GAME_ID.nro"
echo "    (home menu: '$NAME' — saves in sdmc:/renOunce/$GAME_ID/ on the console)"
