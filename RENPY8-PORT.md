# Ren'Py 8 extension port status

Both [Ren'Py 8.4.1](https://www.renpy.org/release/8.4.1) and
[Ren'Py 8.6.1](https://www.renpy.org/release/8.6.1) ship Python 3.12
bytecode in their official SDKs. The complete SDK and source archives are
fetched separately per target by `prepare-renpy8-sdk.bash` and checked against
the SHA-256 values in their official `checksums.txt` files. The archives and
build outputs stay under ignored `build-renpy8/` paths.

`build-python312-runtime.bash` cross-compiles CPython 3.12.8 as a static
Switch 2 archive with a `horizon` target configuration. The extension scripts use its matching headers. Do not
link these archives with the older 3.11 probe.

## 8.4.1

The official `setup.py` generates static Cython C files. With a host Python
that has Cython and setuptools installed, run from the extracted Ren'Py source:

```sh
RENPY_STATIC=1 RENPY_CYTHON_SINGLETHREAD=1 RENPY_CYTHON=cython python setup.py --help
```

Generate pygame_sdl2's static C files using its official `setup.py` with
`PYGAME_SDL2_STATIC=1` and a working `sdl2-config` in `PATH`. Then run
`build-renpy84-extensions.bash` inside `renounce-dev`. This produced
`build-renpy8/8.4.1/librenpy84-switch2.a` from 42 Ren'Py Cython modules,
23 pygame_sdl2 Cython modules, and their C helpers. The optional Assimp C++
helper is not included because the devkit has no Assimp portlib. The sole
source patch is `patches/renpy8-switch2-rng.patch`, mapping libhydrogen's
seed source to the Switch 2 cryptographic RNG.

## 8.6.1

The official `setup.py generate` produced 63 Cython modules without source
changes. This release uses pygame over SDL3, not pygame_sdl2. With the official
SDL3 3.4.20 and SDL3_image 3.4.8 headers in `build-renpy8/`, run
`build-renpy86-extensions.bash` inside `renounce-dev`. It produced
`build-renpy8/8.6.1/librenpy86-core-switch2.a` from 62 generated modules
and their C helpers. The Assimp module is excluded until Assimp is built for
Switch 2. The same small RNG patch applies to this version.

## Remaining integration

The archives are cross-compiled, but **neither version is a playable engine**.
The 8.4.1 extensions are linked and statically registered in a probe NRO.
Version-specific Ren'Py platform patches, complete SDK asset staging, and
hardware boot testing remain. Version 8.6.1 also needs SDL3, SDL3_image,
and Assimp target libraries plus static module registration. The 8.x release targets
remain disabled until those steps pass. The earlier Python 3 smoke-test NRO
did not leave a log on hardware, so its boot status remains unknown.

## Link audit and hardware incident

The first 8.4.1 link probe mixed the Switch 1 `libnx.a` and Mesa archives with
libounce/OunceVK because pkg-config exported absolute legacy paths. It linked
but the console locked up when tested, so **do not launch that NRO again**.
The exact on-console message about not being compiled for Switch 2 has not
been reproduced in the container. The mixed link is a concrete defect; the
full cause of the hardware crash remains unconfirmed.

`switch/python3/CMakeLists.txt` now replaces legacy libnx/Mesa paths with
libounce/OunceVK, removes the legacy libnx include directory, and leaves NRO
packaging disabled by default. `link-renpy84-probe.bash` verifies the final
link command and produces only
`build-renpy8/8.4.1/renounce-renpy-8.4.1-link-only.elf`. The audited ELF linked
successfully with Python 3.12 and 64 registered extension modules. No NRO
from this corrected link has been executed on hardware.

The earlier generated NROs have been renamed with `.unsafe` while retaining
them for diagnosis. The `_renpytfd` desktop file-dialog module is excluded
from registration because its C helper needs `termios`, absent on Switch.
The container uses `switch-harfbuzz` 10.0.1 and `switch-freetype` 2.13.3 from
devkitPro to satisfy the official Ren'Py extension symbols.

For 8.6.1, official SDL3 3.4.20 is not directly configurable as a working
Switch 2 backend. Forcing its Unix console backend fails on `dlfcn.h`, which
is not supplied by the target SDK. SDL3_image and Assimp target libraries
also remain unavailable. No Ren'Py 8.6.1 NRO is linked yet.

## ABI audit

The crash report prompted a second audit. The first CPython 3.12 archive was
cross-compiled with a Linux host triplet and incorrectly had `MACHDEP=linux`
and `HAVE_FORK=1`. That archive and the corresponding extension objects must
not be used. `build-python312-runtime.bash` now builds into
`build-python312/switch2-horizon` with `MACHDEP=horizon`, `HAVE_FORK` and
`HAVE_SEM_OPEN` disabled. The 8.4.1 extensions were rebuilt against that
`pyconfig.h`, and the audited ELF was relinked successfully. Both source and
extension objects use the AArch64 Switch 2 toolchain; the linker uses
libounce specs and OunceVK, with no Switch 1 libnx/Mesa paths.

This confirms a consistent compile/link ABI, **not** a working runtime ABI.
Python initialization, libc/thread behavior, and the NRO loader have not
been validated on hardware with this configuration. NRO packaging remains
disabled by default.

Earlier sections record the paths used during development. Current 8.4.1
builds put all writable files in `renounce/<ID>/` beside the NRO; see the
current layout at the end of this document.

## Controlled hardware boot test

The user requested a hardware test after the ABI audit. Run
`package-renpy84-test.bash` in `renounce-dev` to explicitly package the
audited ELF as `build-renpy8/8.4.1/renounce-renpy-8.4.1-boot-test.nro`.
This is a Python 3.12 import test only; it does not launch Ren'Py or include
a game. The launcher writes `sdmc:/renounce-python3-boot.log` from C at
`main`, `romfsInit`, extension registration, Python initialization, the
Python smoke test, and finalization. If Python reaches the smoke test, it
also writes `sdmc:/renOunce/python3-probe.txt`. An absent C log means the
failure may have occurred before `main` or SD logging was unavailable.
The NRO was compiled and its link inputs audited, but it has not yet been
executed on hardware.

## Python startup RNG fix

The first controlled hardware test reached `Py_InitializeFromConfig` and
reported `failed to get random numbers to initialize Python`. CPython was
falling back to `/dev/urandom`, which is unavailable on this target.
`patches/cpython312-switch2-rng.patch` now routes CPython's startup hash seed
and `os.urandom()` through libounce's `csrngInitialize` and
`csrngGetRandomBytes`. The patch touches only `Python/bootstrap_hash.c`.
The old test NRO is retained as `.no-rng`; the replacement
`renounce-renpy-8.4.1-boot-test.nro` was rebuilt and statically verified to
contain `csrngGetRandomBytes`. Hardware verification of the replacement is
still pending.

## Filesystem codec and one-step build

The next hardware test passed extension registration but Python initialization
reported `failed to get the Python codec of the filesystem encoding`. The
previous `lib.zip` used deflate while the static Python runtime had no zlib
module. The 8.4.1 ROMFS now stores ZIP entries without compression, and the
runtime also builds zlib plus other standard native modules statically.
`stage-renpy84-sdk.py` packages the Python 3.12 standard library and the
platform-neutral Python files from the official Ren'Py 8.4.1 SDK, plus
`renpy.py` and `renpy/common`; it includes no game. The launcher checks that
`romfs:/Contents/lib.zip` opens and writes verbose Python import diagnostics
to `sdmc:/renounce-python3-import.log`.

Run `bash build-renpy84-one-step.bash` on the host to fetch/verify the SDK,
generate official Cython sources, rebuild Python and Ren'Py extensions,
stage SDK assets, link, and package the 8.4.1 boot-test NRO. This still tests
Python startup and imports, not a playable engine. The new package requires
another hardware test.

The subsequent hardware test confirmed `romfsInit`, ZIP access, Python
initialization, the smoke test, and clean finalization all returned zero.
Verbose imports confirmed `encodings` loaded from the 1588-entry RomFS ZIP.
The next boot-test NRO imports selected native standard modules, pygame_sdl2,
and Ren'Py modules. It records each attempt and traceback in
`sdmc:/renounce-python3-modules.log` and the overall probe result in
`sdmc:/renounce-python3-boot.log`. This new import probe has not yet been
tested on hardware.

The import-probe hardware log confirmed `zlib`, `_bz2`, `math`, `_socket`,
`pygame_sdl2`, `renpy`, and `renpy.astsupport` load successfully. Importing
`renpy.display.render` failed because `random` needs SHA-512 and the static
runtime lacked `_sha2`; the `hashlib` fallback then lacked SHA-512 too.
The runtime build now includes CPython's built-in `_md5`, `_sha1`, `_sha2`,
`_sha3`, and `_blake2` modules. The next probe explicitly imports `hashlib`
and `random` before Ren'Py display modules. SHA-2's HACL C source is linked
directly into the Python archive because a nested static archive left its
symbols unresolved. The revised NRO links and contains both `PyInit__sha2`
and the SHA-512 implementation; hardware verification is pending.

The next reported failure was `Module 'renpy' has no attribute 'config'`.
The import probe had loaded `renpy` then reached display code without the
official `renpy.import_all()` sequence, which imports `renpy.config` first.
The updated probe checks `renpy.config` and `renpy.log`, then calls
`renpy.import_all()` and records its first traceback. This package has not
yet been tried on hardware.

## Complete 8.4.1 import preparation

The later `renpy.error` attribute failure exposed that importing the package
and individual modules is not the official bootstrap sequence. The probe now
imports `renpy.bootstrap` first, then pygame_sdl2, installs its pygame alias,
imports `_renpy`, and calls
`renpy.import_all()` once. It stops on the first exception and records it;
success is marked `ALL IMPORTS OK` only after that complete call returns.

`stage-renpy84-sdk.py` now includes the SDK's `renpy.test` package, which
`import_all()` imports unconditionally. `build-assimp-switch2.bash` builds
upstream Assimp 5.2.5 with the glTF importer, and the official generated
`renpy.gl2.assimp` C++ extension is linked into the 8.4.1 archive. The ELF
contains its `PyInit` entry and Assimp implementation. The build audit checks
all 131 explicit Ren'Py imports in `import_all()` against the ZIP and static
module table. This is a complete static import audit, but only the next
hardware run can confirm dynamic imports and initialization side effects.

The next hardware report stopped at `No module named _posixsubprocess` while
importing Ren'Py's bootstrap module. CPython's `subprocess.py` treats Horizon
as a POSIX process platform by default and imports its fork/exec helper.
`patches/cpython312-horizon-subprocess.patch` adds Horizon to CPython's
existing no-process platform list. The ROMFS staging now prefers patched
CPython `.py` files over duplicate SDK `.pyc` files, so that change reaches
the NRO. Process creation remains unavailable on this target. The complete
one-step build and 131-import audit pass; hardware validation is pending.

## Engine bootstrap test

`package-renpy84-engine.bash` builds a separate
`renounce-renpy-8.4.1-engine-test.nro`. It calls the official Ren'Py
`bootstrap()` with `romfs:/Contents` as the engine base. The official
`renpy.py` launcher helpers and all SDK/common assets are bundled in RomFS;
no game is bundled and no game directory is created on SD. Only diagnostic
logs use SD. `sdmc:/renounce-engine-boot.log` records bootstrap entry,
exceptions, and exit status; the existing C/Python logs remain available.
Because the NRO contains no game, script loading may stop after engine
initialization. This is an unverified hardware test, not a playable release.

For an end-to-end hardware test, `package-renpy84-game-test.bash` creates a
separate `renounce-renpy-8.4.1-game-test.nro`. Its RomFS contains the same
engine plus `game/script.rpy`, a two-line dialogue that returns. The
engine-only NRO stays separate and contains no game. The bundled launcher
uses `sdmc:/renounce-engine-boot.log` for bootstrap diagnostics, with
Ren'Py logs and test saves directed to SD rather than read-only RomFS.
The test game is a development fixture and is not part of the eventual
engine-only release.

The first game-test hardware run reached `renpy.import_all()` but failed in
Ren'Py's module backup because the test launcher assigned an anonymous
`path_to_logdir` function. Ren'Py pickles module attributes there, and a
lambda cannot be resolved by name. The launcher now assigns a named module
function. Both game-test and engine-only NROs were repackaged; hardware
verification of the fix is pending.

The next hardware run reported `Module _errorhandling could not be loaded`.
The SDK's `_errorhandling.rpym` and `.rpymc` were present in RomFS, but
`renpy.loader` joined the RomFS base with a search path that already began
with `romfs:/`, producing an invalid doubled path. The staging step now
patches only the loader's filesystem scan and lookup joins to preserve
`romfs:/` and `sdmc:/` rooted paths. Both game-test and engine-only NROs
were regenerated; the fix is awaiting hardware verification.

The next hardware run proceeded further but logged `No usable temporary
directory found`. CPython's `tempfile` applies `abspath()` to candidates,
which does not preserve the Switch `sdmc:` device prefix. The launcher now
creates and verifies `sdmc:/renounce-tmp`, then assigns it directly to
`tempfile.tempdir` before importing Ren'Py. The same log showed a harmless
but noisy attempt to write `game/script.rpyc` into read-only RomFS. The
staged `renpy/script.py` now skips that write only for RomFS scripts; source
parsing and writable game paths keep their existing behavior. Both NROs were
repackaged and await hardware verification.

The game-test hardware run then worked but logged a missing
`cache/shaders.txt`. Ren'Py treats this as an optional list of shaders to
precompile; the test game now bundles an empty file so loading it succeeds
without implying persistent shader cache support. `tempfile` is used by
Ren'Py for fallback logs and error reports, not for this shader list.
The launcher now tries libounce's `fsdevMountTemporaryStorage("tmp")` first,
tests whether `tmp:/` is writable, then falls back to the dedicated
`sdmc:/renounce-tmp` directory. The selected path is written to
`sdmc:/renounce-engine-boot.log`, and the mount result to the C boot log.
The SDK's current NACP generator does not expose a temporary-storage size,
so the native mount may fail; the SD fallback keeps the engine usable.

The current 8.4.1 launcher keeps per-game data beside the NRO. Its
compiled `RENONCE_GAME_ID` selects `<NRO directory>/renounce/<ID>/`, with `Data`,
`Logs`, `cache`, and `tmp` underneath. Saves and persistent data use `Data`,
MultiPersistent uses `<ID>/MultiPersistent`, Ren'Py logs use `Logs`, and
`renpy.loader.get_path("cache/...")` uses `cache`. The SD fallback for
`tempfile` is `<ID>/tmp`; it is cleared on startup and in the bootstrap
exit path, leaving saves, logs, and cache untouched. Native temporary
storage remains the preferred option when mounted and writable.
The early C boot and import logs and Python diagnostics are also placed in
`<ID>/Logs`. The launcher requires a valid NRO path under an SD subdirectory;
it exits without writing to SD if the path is unavailable or points to its root.

The Joy-Con pointer logic from the 7.6.1 launcher is now registered in the
Python 3 `_otrhlibnx` module. Its cursor image and periodic Ren'Py script
are bundled in the 8.4.1 common assets, so both the engine-only NRO and
the game-test NRO can use it. This input path is linked but still needs a
hardware interaction test.

`package-renpy84-release.bash` builds the game-free 8.4.1 distribution
candidate at `build-renpy8/8.4.1/renounce-renpy-8.4.1.nro`. It removes the
import probe and disables bootstrap diagnostics. The runtime saves directly
to `<NRO directory>/renounce/renpy-8.4.1-engine/Data`, avoiding extra
directories derived from the game's save-directory setting. A hardware test
of this release candidate remains necessary before publishing it.
