# renOunce

Ren'Py 7.6.1 games on **Nintendo Switch 2** homebrew — a port of
[Otorhin/Ren2Switch](https://github.com/Otorhin/Ren2Switch) (Ren'Py on
Switch 1 / libnx) to [ouncebrew/ounce-devkit](https://github.com/ouncebrew/ounce-devkit)
(libounce + OunceVK, Switch 2 / libnx-compatible), with minimal changes.

## Ren'Py 8.4.1 engine

The game-free Ren'Py 8.4.1/Python 3.12 Switch 2 NRO is built with
`package-renpy84-release.bash` after staging the official SDK and compiling
the runtime and extensions. It is written to
`build-renpy8/8.4.1/renounce-renpy-8.4.1.nro`, with a `.sha256` file.
Writable data lives in `renounce/renpy-8.4.1-engine/` beside the NRO.
See [release notes](releases/renpy-8.4.1.md) for the packaged contents and
current external-game integration scope.

Releases are built from version branches when their target is ready.

## What's different from Ren2Switch

- **Switch 2 toolchain everywhere**: `libounce/cmake/Switch2.cmake`,
  `switch2vars.sh`, `-D__SWITCH2__`, Cortex-A78C flags. Switch 1 portlibs
  (SDL2, ffmpeg, python2.7, fribidi) are reused unchanged; EGL/GLES comes
  from OunceVK (Zink/NVK) through the `portlibs/switch2` pkg-config wrapper.
- **NRO, not NSP**: Switch 2 homebrew runs via kaiHEN/hbmenu, so the
  executable is packaged with `nx_generate_nacp` + `nx_create_nro` and the
  game's romfs is embedded at link time.
- **Saves on the SD card, one folder per game.** The NSP save-data block was
  deleted from `switch/source/main.c`. Every game gets its own folder
  `sdmc:/renOunce/<SAVE_ID>/` (created at boot by the NRO), holding:

      sdmc:/renOunce/<SAVE_ID>/
      ├── Data/            # save slots (FileLocation)
      ├── Logs/            # log.txt, log.log
      ├── cache/           # loader cache
      ├── MultiPersistent  # renpy MultiPersistent data
      └── otrh.log         # top-level traceback, if a boot crash happens

  The folder id is baked into the NRO (`RENOUNCE_GAME_ID`) and exported to
  the Ren'Py layer as the `RENOUNCE_HOME` environment variable; every
  `save:` path in `renpy.patch` reads it. **Never reuse a SAVE_ID across
  games** — they would share a save folder.

- **One branded NRO per game**: title, author, version and icon go into the
  nacp shown on the Switch 2 home menu; the NRO file itself is named after
  the game.
- **Joy-Con 2 mouse mode**: libounce's `PadPointer` sends movement, clicks
  and scrolling to Ren'Py. The on-screen cursor appears after the optical
  sensor tracks movement, and polling runs at 16 ms. Verified on Switch 2
  hardware with The Question.

## Building

The pipeline targets the same kind of container as Ren2Switch did
(`devkitpro/devkita64:20221113` — Ubuntu-based, has apt + python2.7). CI
builds everything on every push.

Use the `renounce-dev` Podman container for the toolchain. On the host,
`build-interactive.py` needs Python 3, Podman and ImageMagick (for automatic
icon conversion). Set `RENONCE_CONTAINER` if your container has another name.

```sh
# 1. Prepare the engine once inside the container:
podman exec -w /work renounce-dev bash setup.bash
podman exec -w /work renounce-dev bash build.bash
podman exec -w /work renounce-dev bash build-switch2-runtime.bash

# 2. Interactive build: reads config.name, config.version and window icon.
./build-interactive.py /path/to/your-game

# A final Ren'Py release (directory or ZIP) can also be imported as a new
# project under projects/<ID>/, then built if its bytecode is compatible.
./build-interactive.py /path/to/final-release.zip
./build-interactive.py --import-only /path/to/final-release

# Or build directly inside the container:
podman exec -w /work renounce-dev bash build-game.bash /work/my-game \
    --name "My Game" --author "You" --version "1.2" \
    --id MyGame --icon icon.jpg --out dist

# The interactive script copies the game's game/ folder into the container,
# detects config.window_icon (or common icon filenames), and converts the
# image to a 256x256 JPEG. Press Enter to accept each default, or enter -
# at the icon prompt to use the libounce icon.

The importer copies the release's `game/` assets and archives, preserves the
detected icon and metadata in `projects/<ID>/`, and omits caches and saves.
The project can be reopened with `./build-interactive.py projects/<ID>`.
Compiled releases need a compatible Ren'Py runtime: the current port runs
Ren'Py 7.6.1/Python 2.7 and rejects Ren'Py 8.x bytecode before building.
```

Output: `dist/<id>.nro`. Copy it to the Switch 2's SD card (e.g.
`sdmc:/switch/renOunce/<id>.nro`) and launch from hbmenu while holding R, as
usual for kaiHEN homebrew.

### Source-built Python and Ren'Py

After `setup.bash`, the Switch 2 runtime can be rebuilt from CPython 2.7.18
and the Ren'Py/pygame_sdl2 Cython sources:

```sh
./container/run.sh bash build-switch2-runtime.bash
./container/run.sh env \
    RENONCE_PYTHON_ARCHIVE=/work/build-python27/source-build/libpython2.7-switch2.a \
    RENONCE_RENPY_ARCHIVE=/work/build-python27/renpy-modules/librenpy-switch-modules.a \
    bash build-game.bash examples/minimal-game --id renOunce_PythonBuilt
```

The build compiles CPython's C objects and the Ren'Py extension archive with
the Switch 2 toolchain, then links them with libounce. It uses the installed
Switch Python `pyconfig.h` and stdlib files as configuration inputs. The
source-built runtime has launched The Question on Switch 2 hardware.

`build.bash` also still uploads the classic `raw.zip` template (PC/Android/
Switch scaffolding) for anyone packaging other targets.

## Repository layout

| Path | Role |
|------|------|
| `setup.bash` | container setup: apt deps, Switch-1 portlib extras, ounce-devkit |
| `build.bash` | engine build: cython → `librenpy-switch-modules.a` → `raw/` template |
| `build-game.bash` | per-game NRO build (branding + romfs + save folder) |
| `build-interactive.py` | interactive game configuration and automatic icon conversion |
| `build-switch2-runtime.bash` | cross-compile CPython and Ren'Py modules |
| `CMakeLists.txt` | builds `librenpy-switch-modules.a` (Switch 2 toolchain) |
| `switch/` | the NRO itself: `main.c` boots Python 2.7 and runs `romfs:/Contents/renpy.py` |
| `renpy.patch` | Ren'Py 7.6.1 patch: `renpy.switch` platform, GLES renderer, romfs loader, `RENOUNCE_HOME` paths |
| `examples/minimal-game/` | gui-free demo game used by CI; safe restart probe on hardware |
| `.github/workflows/ci.yml` | builds the engine and the demo NRO on every push |

## Status

The Question reached its menu on Switch 2 hardware. The SDK font package is
included for its translated menus; other game fonts should live in `game/`.

## Versioned engine targets (work in progress)

Targets are declared independently in `targets/<Ren'Py version>/target.env`.
`bash build-engine.bash 7.6.1` creates `dist/7.6.1/renounce-renpy-7.6.1.nro`
from the existing Python 2.7 runtime, without embedding `Contents/game`.
Its game directory is `sdmc:/renOunce/game/`, which a separate preparation
application must populate. This external installation path has not yet been
validated on hardware.

Ren'Py 8.4.1 uses its own Python 3.12 runtime and
`package-renpy84-release.bash`; `build-engine.bash` is the legacy 7.6.1
builder and rejects 8.x. Ren'Py 8.6.1 still needs its own completed port.
CI currently builds 7.6.1 only and does not publish releases.
The existing per-game builder remains a legacy path for Ren'Py 7.6.1.

### Python 3 port probe

`build-python3-runtime.bash` now builds a separate CPython 3.11.9 static
archive in the existing `renounce-dev` container. The standalone
`switch/python3` target links a Python 3 NRO and embeds its own stdlib ZIP.
See [switch/python3/README.md](switch/python3/README.md) for the Python 3
build history and the Ren'Py 8.4.1 packaging instructions.

### Ren'Py 8 extension work

See [RENPY8-PORT.md](RENPY8-PORT.md) for the official SDK inputs,
Python 3.12 build, compiled extension archives, and remaining integration.
