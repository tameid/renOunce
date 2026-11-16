# renOunce

Ren'Py 7.6.1 games on **Nintendo Switch 2** homebrew — a port of
[Otorhin/Ren2Switch](https://github.com/Otorhin/Ren2Switch) (Ren'Py on
Switch 1 / libnx) to [ouncebrew/ounce-devkit](https://github.com/ouncebrew/ounce-devkit)
(libounce + OunceVK, Switch 2 / libnx-compatible), with minimal changes.
See [PLAN.md](PLAN.md) for the full port analysis and change list.

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

## Building

The pipeline targets the same kind of container as Ren2Switch did
(`devkitpro/devkita64:20221113` — Ubuntu-based, has apt + python2.7). CI
builds everything on every push.

Locally, you need an environment where `setup.bash`'s apt step works — a
devkitPro container, WSL, or a plain Ubuntu box. (A flatpak sandbox is *not*
enough: no python2.7, no cmake, and `/opt` is read-only; do source work
there and let CI build.)

```sh
# 1. Engine + toolchain (once, ~long): installs the ounce-devkit, fetches
#    Ren'Py/pygame_sdl2 sources, patches them, builds librenpy-switch-modules.a
#    and the engine template under raw/.
sudo bash setup.bash
sudo bash build.bash

# 2. One NRO per game:
sudo bash build-game.bash /path/to/your-game            # defaults below
sudo bash build-game.bash /path/to/your-game \
    --name "My Game" --author "You" --version "1.2" \
    --id MyGame --icon icon.jpg --out dist

#    --name/--version default to config.name/config.version in the game's
#    game/options.rpy; --id defaults to the sanitized name; --icon is a
#    256x256 JPEG for the home menu (empty = libounce default icon).
```

Output: `dist/<id>.nro`. Copy it to the Switch 2's SD card (e.g.
`sdmc:/switch/renOunce/<id>.nro`) and launch from hbmenu while holding R, as
usual for kaiHEN homebrew.

`build.bash` also still uploads the classic `raw.zip` template (PC/Android/
Switch scaffolding) for anyone packaging other targets.

## Repository layout

| Path | Role |
|------|------|
| `setup.bash` | container setup: apt deps, Switch-1 portlib extras, ounce-devkit |
| `build.bash` | engine build: cython → `librenpy-switch-modules.a` → `raw/` template |
| `build-game.bash` | per-game NRO build (branding + romfs + save folder) |
| `CMakeLists.txt` | builds `librenpy-switch-modules.a` (Switch 2 toolchain) |
| `switch/` | the NRO itself: `main.c` boots Python 2.7 and runs `romfs:/Contents/renpy.py` |
| `renpy.patch` | Ren'Py 7.6.1 patch: `renpy.switch` platform, GLES renderer, romfs loader, `RENOUNCE_HOME` paths |
| `examples/minimal-game/` | gui-free demo game used by CI; safe restart probe on hardware |
| `.github/workflows/ci.yml` | builds the engine and the demo NRO on every push |

## Status

Validation ladder in [PLAN.md](PLAN.md) §7 — M0 (toolchain sanity) is what
CI checks; M1+ need real Switch 2 hardware.
