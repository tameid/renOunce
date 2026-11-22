# CPython 3 Switch 2 probe

The sections below record earlier hardware tests. Current 8.4.1 builds put
all writable files in `renounce/<ID>/` beside the NRO, as described at the end.

`build-python3-runtime.bash` cross-compiles CPython 3.11.9 into a separate
static archive and creates a Python 3-only `lib.zip`. The source uses the
Python 3 module and configuration APIs. In the `renounce-dev` container:

```sh
bash build-python3-runtime.bash
source /opt/devkitpro/switch2vars.sh
cmake -S switch/python3 -B build-python3/probe \
  -DRENONCE_PYTHON3_INCLUDE="$PWD/build-python3/Python-3.11.9/Include" \
  -DRENONCE_PYTHON3_CONFIG_INCLUDE="$PWD/build-python3/switch2" \
  -DRENONCE_PYTHON3_ARCHIVE="$PWD/build-python3/switch2/libpython3.11.a" \
  -DRENONCE_PYTHON3_ROMFS="$PWD/build-python3/romfs"
cmake --build build-python3/probe
```

NRO packaging is now disabled by default after a hardware crash in a later
Ren'Py 8.4.1 link probe. This command builds an ELF only. An explicit
`-DRENONCE_PACKAGE_PROBE=ON` is required to generate an NRO for controlled
hardware testing.

When explicitly packaged, this produces `build-python3/probe/renounce-python3.nro`. On hardware, the
probe attempts to write `sdmc:/renOunce/python3-probe.txt` after importing
`sys`, `os`, and `encodings`. That hardware check has not yet been performed.

This is **not** a Ren'Py 8 runtime. The Ren'Py and pygame_sdl2 C extensions
must be built against Python 3.11, registered in the launcher, and paired
with version-specific Ren'Py patches before enabling the 8.4.1 or 8.6.1
release targets. The probe romfs contains no game and no Ren'Py 7 assets.

The 8.4.1 extension link probe is built separately with
`link-renpy84-probe.bash`. It uses Python **3.12.8** to match the official
Ren'Py 8.4.1 SDK and registers 64 extension modules. It is not yet a
playable Ren'Py engine; the earlier standalone 3.11 smoke-test path above
is retained only for comparison and has not passed a hardware boot test.

For the controlled 8.4.1 test, run `package-renpy84-test.bash` explicitly.
It emits `build-renpy8/8.4.1/renounce-renpy-8.4.1-boot-test.nro` and logs
startup stages to `sdmc:/renounce-python3-boot.log`.

The first hardware test reached Python initialization and failed for lack of
`/dev/urandom`. The current test NRO includes the targeted CSRNG patch in
CPython 3.12. The previous NRO is marked `.no-rng`; use the current file only.

The next test reached extension registration but failed while loading the
filesystem codec. The rebuilt 8.4.1 test stages the official SDK's Python
files and an uncompressed `lib.zip`, with `zlib` linked statically. Build it
with `bash build-renpy84-one-step.bash` on the host. It writes C startup
stages to `sdmc:/renounce-python3-boot.log` and Python import diagnostics
to `sdmc:/renounce-python3-import.log`. Hardware verification is pending.

The codec fix has now passed a hardware smoke test: Python initialized,
imported `encodings`, wrote the probe file, and finalized successfully.
The current NRO adds a module import probe and writes per-module results to
`sdmc:/renounce-python3-modules.log`. This probe still needs a hardware test.

The latest 8.4.1 probe follows Ren'Py's bootstrap import order and calls the
complete `renpy.import_all()` routine. Its log ends with `ALL IMPORTS OK`
only if every import returns. The package includes `renpy.test` and the
compiled `renpy.gl2.assimp` extension; the latter uses a separately built
Assimp 5.2.5 static library. `audit-renpy84-imports.py` confirms all 131
explicit imports in that routine are packaged. Hardware validation remains
necessary for dynamic imports and module initialization.

For the separate engine bootstrap test, run
`package-renpy84-engine.bash` in the container. Its NRO uses the official
Ren'Py launcher helpers and `romfs:/Contents` for all engine assets,
including `renpy/common`; it bundles no game. Bootstrap diagnostics go to
`sdmc:/renounce-engine-boot.log`. The test has not yet run on hardware.

`package-renpy84-game-test.bash` produces a separate NRO with a minimal
`game/script.rpy` inside RomFS, so the full engine can attempt to display
dialogue without requiring external game files. This is only for hardware
testing; the engine-only package remains game-free.

The 8.4.1 launcher now uses `renounce/<ID>/` beside the NRO. For example,
`sdmc:/switch/game.nro` uses `sdmc:/switch/renounce/<ID>/`. It requires the
launcher to provide the NRO path and refuses an NRO at the SD root.
The game-test ID is `renpy-8.4.1-test`; the engine-only ID is
`renpy-8.4.1-engine`. `Data` contains saves and persistent data, `Logs`
contains Ren'Py logs, `cache` contains writable game
cache, and `tmp` is the SD fallback for temporary files. Only `tmp` is
removed on normal exit and at the next startup. The Joy-Con pointer and
cursor use the 7.6.1 PadPointer logic, now linked to the Python 3 module.
Mouse behavior still needs a hardware test.
Diagnostic builds place C boot and import logs and Python probe files under
`<ID>/Logs`.

For a game-free distribution candidate, run `python3 stage-renpy84-sdk.py`
and `bash package-renpy84-release.bash` in the build container. It creates
`build-renpy8/8.4.1/renounce-renpy-8.4.1.nro` without the import probe,
Python verbose tracing, bootstrap smoke-test files, or a bundled game.
Ren'Py's save path is pinned to `<ID>/Data`, including when its game
configuration supplies an unusual save directory name. The NRO still needs
a hardware test before publication.
