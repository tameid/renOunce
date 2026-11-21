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

# A compiled release cannot be recompiled with a different Ren'Py bytecode
# format. Fail before staging gigabytes of assets or linking an unusable NRO.
if [ -f "$GAME_DIR/game/script_version.txt" ]; then
    python3 - "$GAME_DIR/game/script_version.txt" <<'PY'
import ast
import sys
try:
    version = ast.literal_eval(open(sys.argv[1]).read().strip())
except (SyntaxError, ValueError):
    sys.exit('build-game.bash: invalid game/script_version.txt')
if not isinstance(version, (tuple, list)) or len(version) < 2:
    sys.exit('build-game.bash: invalid Ren\'Py version')
if version[0] != 7 or tuple(version[:2]) > (7, 6):
    sys.exit('build-game.bash: compiled game uses Ren\'Py %s; this runtime is Ren\'Py 7.6.1' %
             '.'.join(map(str, version)))
PY
fi

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
if [ "$GAME_DIR" = "$WORK" ] || [[ "$GAME_DIR" == "$WORK/"* ]]; then
    echo "build-game.bash: game source must be outside $WORK" >&2
    exit 1
fi
rm -rf "$WORK"
mkdir -p "$WORK/romfs/Contents/game"
cp -r "$REPO/raw/switch/romfs/." "$WORK/romfs/"
cp -r "$GAME_DIR/game/." "$WORK/romfs/Contents/game/"

# Keep the pointer in the game framebuffer: the Switch SDL video backend does
# not provide a desktop window manager cursor.
cp "$REPO/switch/assets/renounce-cursor.png" \
    "$WORK/romfs/Contents/game/_renounce_cursor.png"
cp "$REPO/switch/assets/renounce-cursor.rpy" \
    "$WORK/romfs/Contents/game/_renounce_cursor.rpy"

# Older engine templates did not embed the SDK fonts. The Question and other
# Ren'Py examples reference SourceHanSansLite.ttf by its bare filename.
if [ ! -f "$WORK/romfs/Contents/renpy/common/SourceHanSansLite.ttf" ]; then
    SDK_FONTS="$REPO/renpy-source/sdk-fonts"
    if [ -d "$SDK_FONTS" ]; then
        cp -r "$SDK_FONTS/." "$WORK/romfs/Contents/renpy/common/"
    fi
fi

# Older engine templates omit pygame_sdl2's pure-Python package. Its compiled
# extensions are linked into the NRO, but Python still needs __init__.py and
# the helpers in lib.zip to import the package.
if ! unzip -Z1 "$WORK/romfs/Contents/lib.zip" | grep -qx 'python2.7/pygame_sdl2/__init__.py'; then
    PYGAME_PY="$REPO/pygame_sdl2-source/src/pygame_sdl2"
    if [ ! -f "$PYGAME_PY/__init__.py" ]; then
        echo "build-game.bash: pygame_sdl2 Python sources missing; run setup.bash first" >&2
        exit 1
    fi
    mkdir -p "$WORK/libzip/python2.7/pygame_sdl2/threads"
    cp "$PYGAME_PY"/*.py "$WORK/libzip/python2.7/pygame_sdl2/"
    cp "$PYGAME_PY"/threads/*.py "$WORK/libzip/python2.7/pygame_sdl2/threads/"
    (cd "$WORK/libzip" && 7z a -tzip "$WORK/romfs/Contents/lib.zip" python2.7/pygame_sdl2) >/dev/null
fi

# Existing engine templates may lack SDK Python-only dependencies. Overlay all
# platform-neutral packages rather than waiting for one import to fail at boot.
SDK_PY="$REPO/raw/renpy_clear/lib/python2.7"
if [ ! -f "$SDK_PY/builtins/__init__.pyo" ]; then
    echo "build-game.bash: Ren'Py SDK Python dependencies missing; run build.bash first" >&2
    exit 1
fi
mkdir -p "$WORK/libzip/python2.7"
for package in builtins future past ecdsa requests certifi chardet idna urllib3 pyasn1 rsa copyreg html http ordlookup reprlib socketserver winreg; do
    if [ -d "$SDK_PY/$package" ]; then
        cp -r "$SDK_PY/$package" "$WORK/libzip/python2.7/"
    fi
done
for module in six.pyo typing.pyo pefile.pyo list2cmdline.pyo; do
    if [ -f "$SDK_PY/$module" ]; then
        cp "$SDK_PY/$module" "$WORK/libzip/python2.7/"
    fi
done
(cd "$WORK/libzip" && 7z a -tzip "$WORK/romfs/Contents/lib.zip" python2.7) >/dev/null

# The NRO embeds the romfs at link time, so reconfigure per game.
source "$DEVKITPRO/switch2vars.sh"

PYTHON_ARCHIVE_DEFAULT="$REPO/build-python27/source-build/libpython2.7-switch2.a"
RENPY_ARCHIVE_DEFAULT="$REPO/build-python27/renpy-modules/librenpy-switch-modules.a"
[ -f "$PYTHON_ARCHIVE_DEFAULT" ] || PYTHON_ARCHIVE_DEFAULT="$DEVKITPRO/portlibs/switch/lib/libpython2.7.a"
[ -f "$RENPY_ARCHIVE_DEFAULT" ] || RENPY_ARCHIVE_DEFAULT="$DEVKITPRO/portlibs/switch/lib/librenpy-switch-modules.a"
CMAKE_ICON_ARGS=()
[ -z "$ICON" ] || CMAKE_ICON_ARGS=(-DSWITCH_ICON="$ICON")

rm -rf "$WORK/build"
cmake -S "$REPO/switch" -B "$WORK/build" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DRENONCE_PYTHON_ARCHIVE="${RENONCE_PYTHON_ARCHIVE:-$PYTHON_ARCHIVE_DEFAULT}" \
    -DRENONCE_RENPY_ARCHIVE="${RENONCE_RENPY_ARCHIVE:-$RENPY_ARCHIVE_DEFAULT}" \
    -DSWITCH_APP_NAME="$NAME" \
    -DSWITCH_AUTHOR="$AUTHOR" \
    -DSWITCH_VERSION="$VERSION" \
    -DSWITCH_GAME_ID="$GAME_ID" \
    -DSWITCH_ROMFS="$WORK/romfs" \
    "${CMAKE_ICON_ARGS[@]}"
cmake --build "$WORK/build"

mkdir -p "$OUT"
cp "$WORK/build/renpy-switch.nro" "$OUT/$GAME_ID.nro"

echo "=== built $OUT/$GAME_ID.nro"
echo "    (home menu: '$NAME' — saves in sdmc:/renOunce/$GAME_ID/ on the console)"
