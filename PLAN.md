# renOunce — The Ultimate Plan

**Port [Otorhin/Ren2Switch](https://github.com/Otorhin/Ren2Switch) (Ren'Py 7.6.1
on Nintendo Switch 1 / libnx) to [ouncebrew/ounce-devkit](https://github.com/ouncebrew/ounce-devkit)
(Nintendo Switch 2 / libounce + OunceVK), with minimal changes.**

Everything below was verified against actual source, not assumed. Reference
commits: Ren2Switch @ master, ounce-devkit @ main (devkit release `20261114`),
libounce @ `9382b1ec`, OunceVK @ `f5afcd27`, kaiHEN @ `eb81e191`.

---

## 1. How Ren2Switch works today

Build pipeline (`setup.bash` → `build.bash`, in CI container
`devkitpro/devkita64:20221113`):

1. **Sources**: Ren'Py 7.6.1 source + SDK, pygame_sdl2 2.1.0, `renpy.patch`
   (1869 lines; ~90% Python-side plumbing for a new `renpy.switch = True`
   platform flag, GLES-only renderer, `romfs:`-aware loader, save/log paths,
   and an `_otrhlibnx` builtin module). Host Python 2.7 + Cython 0.29.36
   generate `gen-static/` C sources.
2. **Modules static lib** (root `CMakeLists.txt`): `librenpy-switch-modules.a`
   — every pygame_sdl2 + renpy C module, linked against Switch 1 portlibs:
   static Python 2.7 (`python27-switch`), fribidi, SDL2/SDL2_gfx/image/mixer/
   ttf, ffmpeg, freetype, zlib, and Switch-1 mesa (EGL/GLESv2/glapi/
   libdrm_nouveau). Installs into `$DEVKITPRO/portlibs/switch`.
3. **Final executable** (`switch/CMakeLists.txt`): a single `main.c` (434
   lines) that boots Python 2.7 in-process, registers ~50 statically-linked
   extension modules in an `_inittab`, sets `sys.path` to
   `romfs:/Contents/lib.zip` (a zipapp holding the Python stdlib + renpy
   engine), and runs `romfs:/Contents/renpy.py`. Built with
   `$DEVKITPRO/switch.cmake` → `renpy-switch.nso` via `elf2nso`, placed into
   an external NSP template (`rawproject.zip`).
4. **Distribution**: installed NSP (title takeover) with
   `romfs:/Contents/{renpy.py, lib.zip, renpy/common}`; saves went to the
   NSP's save data (`save:` device).

Everything heavy (SDL2 video/audio/input, EGL, GLES3, ffmpeg decode, Python,
fonts) comes from devkitPro Switch 1 portlibs; Ren2Switch itself is glue +
patches.

## 2. What ounce-devkit provides

- **libounce** (`$DEVKITPRO/libounce`): libnx with Switch 2 changes. Installs
  `lib/libnx.a` (a linker script selecting `libounce.a`) so **`-lnx` keeps
  linking "libnx"**. `switch2_rules` replaces `switch_rules`;
  `switch2_cpu.mk` sets `SWITCH2_CPU := -mcpu=cortex-a78c+crypto`. Uses
  **mimalloc** by default (`_mallocInitialize()` runs from `__libnx_init` and
  divides the Horizon heap into 64 KiB pages using `fake_heap_start/end`).
- **OunceVK** (`$DEVKITPRO/portlibs/switch2`): NVK (Mesa's Vulkan driver for
  NVIDIA) + **Zink** (OpenGL / **OpenGL ES 3.1**) + EGL on the default
  `NWindow`. Static archives; GPU opens on first EGL display / Vulkan
  instance. Mesa logs go to stderr (`MESA_LOG_LEVEL` etc. via `setenv`).
- **libkaiHEN**: the Switch 2 homebrew environment. Homebrew is launched as
  **NRO** (hold R on a native game → hbloader replaces the game process →
  hbmenu). No title takeover / installed-NSP path.
- Toolchain: `libounce/cmake/Switch2.cmake` (devkitPro `switch.cmake` with
  `NX_ROOT=libounce`, switch2 portlibs first, `-D__SWITCH2__`, A78C flags;
  keeps devkitPro's platform helpers incl. `nx_generate_nacp` /
  `nx_create_nro`), plus `switch2vars.sh` for Makefiles/Meson/autotools.

## 3. Verified compatibility findings

| # | Finding | Evidence |
|---|---------|----------|
| 3.1 | **Every libnx API `switch/source/main.c` uses exists in libounce with the same signature**: `appletSetCpuBoostMode`/`ApmPerformanceMode` (applet.h:568, apm.h), `errorSystemCreate`/`errorSystemShow` (applets/error.h:236/242), `pselShowUserSelector` (applets/psel.h), `accountGetPreselectedUser` (acc.h:97), `appletRestartProgram(buffer, size)` (applet.h:1658), `nsGetApplicationControlData(source, id, buf, size, out)` (ns.h:313), `nwindowGetDefault` (display/native_window.h), `ConsoleRenderer` (runtime/devices/console.h), plus fsdev save-data APIs, `romfsInit`, `socketInitializeDefault`, `svcGetInfo`/`svcSetHeapSize`. | libounce `nx/include/switch/**` |
| 3.2 | **The custom `__libnx_initheap` override in main.c stays compatible.** libounce keeps `__libnx_initheap` weak and overridable, and the mimalloc bootstrap `_mallocInitialize()` reads `fake_heap_start`/`fake_heap_end` — exactly what the override sets after its one `svcSetHeapSize` call. | libounce `nx/source/runtime/init.c:65-100,193-212`, `nx/source/switch2/malloc/malloc.c` |
| 3.3 | **OunceVK ships the exact stub libraries Ren2Switch's link lines ask for.** `package-portlib.sh` installs **empty** `libGLESv2.a`, `libglapi.a`, `libdrm_nouveau.a` plus real `libEGL.a` (EGL+GL+GLES+Vulkan in one object) — explicitly "so a Switch 1 Makefile that links them still works" and so Switch-1 mesa (which does not work on Switch 2) is hidden. Ren2Switch's `pkg_check_modules(EGL/GLAPI/GLESV2/LIBDRM_NOUVEAU …)` resolve to these. | ouncevk `switch2/build/package-portlib.sh` |
| 3.4 | **pkg-config just works**: `portlibs/switch2/bin/aarch64-none-elf-pkg-config` searches `portlibs/switch2/lib/pkgconfig` (OunceVK: `egl`, `glesv2`, `glapi`, `libdrm_nouveau`, `vulkan`) first, then `portlibs/switch/lib/pkgconfig` (everything else). Both CMakeLists' `PKG_CONFIG_PATH`/`CMAKE_PREFIX_PATH` lines are harmlessly overridden by that wrapper. | package-portlib.sh (wrapper script) |
| 3.5 | **Switch 1 portlibs are reusable unchanged**: portlibs that use only newlib + libnx "work unchanged" (devkit README), and libounce is libnx-API-compatible — SDL2, SDL2_gfx/image/mixer/ttf, ffmpeg, freetype, libpng/jpeg/webp, modplug/mpg123/ogg/opus/vorbisidec, bz2, zlib, python2.7, fribidi all link against libounce. Ren'Py's video path is software ffmpeg decode (`config.hw_video` removed by the patch), so no NVDEC dependency. | devkit README; portlib contents |
| 3.6 | **CPU compatibility**: Switch 1 portlibs are built `-march=armv8-a+crc+crypto -mtune=cortex-a57`; Switch 2 is Cortex-A78C. A57 code runs on A78C; `+crypto` is enabled on both (`switch2_cpu.mk` notes A78C AES/SHA is the optional extension devkitPro's flags already enable). Same armv8-a base ISA, no PAC/BTI flags in play. | libounce `nx/switch2_cpu.mk` |
| 3.7 | **CMake platform machinery carries over**: Switch2.cmake includes devkitPro's `Platform/NintendoSwitch.cmake`, keeping the `-lnx` executable link and `nx_generate_nacp`/`nx_create_nro`; only NX_ROOT changes to libounce, switch2 portlibs prepend, `-D__SWITCH2__` and A78C flags are added. `CMAKE_SYSTEM_NAME` stays `NintendoSwitch`, so `NINTENDO_SWITCH` checks behave identically. | devkit `toolchain/cmake/{Switch2.cmake,Platform/NintendoSwitch.cmake}` |
| 3.8 | **EGL usage matches exactly**: OunceVK supports `eglGetDisplay(EGL_DEFAULT_DISPLAY)` + `eglCreateWindowSurface(nwindowGetDefault())` + GLES 3 context — the same pattern Ren'Py's gl2 renderer (via pygame_sdl2 → SDL2's `switch` video driver) uses. Zink provides GLES 3.1, more than Ren'Py 7.6 gl2 needs (patch forces renderer list to `["gles"]`). | devkit `examples/gles-triangle/source/main.c`; ouncevk `switch2/README.md`; renpy.patch (core.py) |
| 3.9 | **The one structural difference**: Switch 2 homebrew runs as **NRO via kaiHEN/hbmenu** (hold R on a native game). No installed-NSP/title-takeover path, so the NSO-into-NSP packaging becomes an NRO (nacp + elf2nro + embedded romfs). | kaihen `README.md`, `hen/README.md` |
| 3.10 | **Saves go directly to the SD card — the same way a shipping Switch 2 port already does it.** [NerdsMcGee/sm64ex-alo-s2](https://github.com/NerdsMcGee/sm64ex-alo-s2) has no save-data device at all: `sys_user_path()` → `SDL_GetPrefPath("", "sm64ex")` (SDL2's Switch pref path = the NRO's directory on SD), and its README: "The game writes its config and save file next to it" (`sdmc:/switch/sm64ex-alo/`). renOunce does the equivalent with explicit paths: `sdmc:/renOunce/{Data,Logs,cache,MultiPersistent}`, and the whole save-data block in `main.c` is deleted. | sm64ex-alo-s2 `SWITCH2.md`, `src/pc/platform.c:194-230`, `src/pc/pc_main.c:286-289` |
| 3.11 | **`appletSetCpuBoostMode` is proven on Switch 2.** sm64ex-alo-s2's shipped Switch 2 build calls `appletSetCpuBoostMode(ApmCpuBoostMode_FastLoad)` (value 1); Ren2Switch passes `ApmPerformanceMode_Boost` (also 1) and ignores the Result. No change needed. | sm64ex-alo-s2 `src/pc/nx_main.c:21-27` |
| 3.12 | **A full Switch 2 port on this devkit validates the entire approach.** sm64ex-alo-s2 uses exactly the planned recipe: `LIBNX := $(DEVKITPRO)/libounce`, switch2 portlibs first, `-D__SWITCH2__`, `SWITCH2_CPU`, and `aarch64-none-elf-pkg-config --libs glesv2 egl` for GL — running the Switch 1 SDL2 portlib + OunceVK GLES with a **1920×1080 SDL window in handheld and docked** (the Switch 2 screen is 1080p in both modes), which is also the resolution Ren2Switch's patch hardcodes. | sm64ex-alo-s2 `Makefile:358-360,757-777`, `SWITCH2.md`, `src/pc/gfx/gfx_sdl2.c` |

## 4. The minimal change set (≈ 7 edits, ~60 lines net)

| File | Change |
|------|--------|
| `setup.bash` | Delete the `switch.cmake` sed hack (line 23); install the ounce-devkit tarball instead |
| `build.bash` | `switchvars.sh` → `switch2vars.sh` (line 49); `.nso` → `.nro` output (line 59) |
| `CMakeLists.txt` | Toolchain file → `libounce/cmake/Switch2.cmake` (line 6) |
| `switch/CMakeLists.txt` | Toolchain file (line 6); fix `pkgcfg_lib_*_nx` pins → `${DEVKITPRO}/libounce/lib/libnx.a`, delete the mesa pins (`*_EGL`, `*_GLAPI`, `*_GLESV2_m`, `*LIBDRM_NOUVEAU*`); replace `elf2nso` target with `nx_generate_nacp` + `nx_create_nro(… ROMFS …)` |
| `switch/source/main.c` | **Delete** the save-data block (~40 lines removed, nothing added except one error string): `userAppInit()` → `romfsInit(); socketInitializeDefault();`; delete `createSaveData()` and the account/psel block; delete `fsdevCommitDevice("save")` in `userAppExit()` and the applet hook; `commitsave()` → `return Py_None;` (keep the function so `renpy.patch`'s hooks stay untouched); error text "save:// folder" → "sdmc:/renOunce/ folder" |
| `renpy.patch` | Exactly **5 path strings**, `save:` → `sdmc:/renOunce/` (see §5) |
| `.github/workflows/ci.yml` | One step: unpack the devkit release (keep `devkita64:20221113` — Ubuntu 22.04 base still has apt `python2.7`, and its GCC 12 supports `-mcpu=cortex-a78c`) |
| `link_sources.bash`, `generate_private.py`, `script.rpy` | **Unchanged** |

Unchanged by design: the heap override (3.2), all service calls (3.1, 3.11),
`MESA_NO_ERROR=1` in `main()` (Zink honors Mesa options), `-Ofast`, the
modules build, and the whole `raw/` romfs content layout.

## 5. `renpy.patch` — the five save-path strings

| Hunk | Was | Becomes |
|------|-----|---------|
| `bootstrap.py` logdir | `renpy.config.logdir = "save:/Logs/"` | `renpy.config.logdir = "sdmc:/renOunce/Logs/"` |
| `main.py` searchpath | `searchpath = [ gamedir, "save://" ]` | `searchpath = [ gamedir, "sdmc:/renOunce/" ]` |
| `loader.py` cache | `fn = "save://" + fn` / `dn = "save://cache"` | `fn = "sdmc:/renOunce/" + fn` / `dn = "sdmc:/renOunce/cache"` |
| `persistent.py` | `files = ["save://MultiPersistent"]` | `files = ["sdmc:/renOunce/MultiPersistent"]` |
| `savelocation.py` | `FileLocation("save:/Data/")` | `FileLocation("sdmc:/renOunce/Data/")` |

Everything else in the patch is byte-identical to Ren2Switch's. The
`_otrhlibnx.commitsave()` calls in `bootstrap.py`/`savelocation.py` stay and
are absorbed by the no-op in main.c.

## 6. Step-by-step build guide

**One-time setup**

1. Install the devkit into an existing devkitPro:
   ```sh
   curl -fsSL https://github.com/ouncebrew/ounce-devkit/releases/download/devkit-20261114/ounce-devkit-20261114.tar.xz | tar -xJ -C /opt/devkitpro
   ```

**Build changes (the §4 table, in order)**

2. `setup.bash`: delete line 23, insert the same curl+tar line.
3. `build.bash` line 49: `source /opt/devkitpro/switch2vars.sh`.
4. `CMakeLists.txt` line 6: `set(CMAKE_TOOLCHAIN_FILE "$ENV{DEVKITPRO}/libounce/cmake/Switch2.cmake" …)`.
5. `switch/CMakeLists.txt`: same toolchain swap; fix/delete the pkgcfg pins;
   replace the NSO target with:
   ```cmake
   nx_generate_nacp(renpy-switch.nacp NAME "${SWITCH_APP_NAME}"
       AUTHOR "${SWITCH_AUTHOR}" VERSION "${SWITCH_VERSION}")
   nx_create_nro(renpy-switch NACP renpy-switch.nacp
       ROMFS "${CMAKE_SOURCE_DIR}/../raw/switch/romfs")
   ```
6. `build.bash` line 59: `mv ./switch/build/renpy-switch.nro ./raw/switch/renpy-switch.nro`.
7. `switch/source/main.c`: apply the deletions in §4.
8. `renpy.patch`: apply the 5 strings in §5.

**CI**

9. Add to `ci.yml` before setup (keep container `devkitpro/devkita64:20221113`):
   ```yaml
   - name: install Switch 2 devkit
     run: curl -fsSL https://github.com/ouncebrew/ounce-devkit/releases/download/devkit-20261114/ounce-devkit-20261114.tar.xz | sudo tar -xJ -C $DEVKITPRO
   ```

## 7. Validation ladder (each milestone blocks the next)

1. **M0 — toolchain sanity (host only)**: configure both CMake projects; verify
   `pkg_check_modules` resolves `egl` → OunceVK `libEGL.a` (linker script
   `INPUT(-louncevk-gl -lstdc++ -lm)`), `glapi`/`glesv2`/`libdrm_nouveau` →
   empty stubs, SDL2/ffmpeg/python2.7 from Switch 1 portlibs,
   `nx` → `libounce/lib/libnx.a`.
2. **M1 — hello NRO on hardware**: build a Switch-1-style libnx program as
   NRO, run via hbmenu (hold R).
3. **M2 — EGL/GLES**: run devkit's `examples/gles-triangle` (provided).
4. **M3 — SDL2 + GL context**: link Switch-1 `libSDL2.a` + OunceVK `libEGL.a`;
   SDL window + GLES context + input. sm64ex-alo-s2 proves this stack ships
   (3.12); this milestone proves Ren'Py's exact usage (context recreation,
   resize).
5. **M4 — Python 2.7**: link `python27-switch` static lib; boot
   `Py_InitializeEx` + import `encodings`, `os` from `romfs:/Contents/lib.zip`.
6. **M5 — modules**: build `librenpy-switch-modules.a` with the Switch2
   toolchain; link into M4; import every module in the `_inittab`.
7. **M6 — ffmpeg**: decode one frame + one audio buffer through ffmedia.
8. **M7 — full Ren'Py**: the real pipeline end-to-end with `script.rpy`;
   verify rendering, saves/logs/persistent landing in `sdmc:/renOunce/`,
   restart, and the error screen.

## 8. Open questions

1. Does `appletRestartProgram` restart cleanly for a homebrew NRO (the
   `UtterRestart` path), or does it exit to hbmenu? Low impact — the call is
   already best-effort.
2. Presentation scaling docked (4K output) at 1080p — sm64ex-alo-s2 ships
   1920×1080 in both modes, so likely nothing to do; confirm visually at M7.
3. `rawproject.zip` (external URL, closed template) provided the NSP
   scaffolding; its PC/Android halves are orthogonal — confirm with the
   maintainer whether to keep consuming it for non-Switch targets.

## 9. Summary

The port is cheap because ounce-devkit was built for exactly this migration:
libounce keeps every libnx symbol `main.c` uses (including the heap-override
hook under mimalloc, and boost mode — both proven by a shipped Switch 2 port);
OunceVK ships empty `libGLESv2`/`libglapi`/`libdrm_nouveau` archives so the
Switch-1-style link lines resolve to real EGL/GLES (Zink/NVK) unedited;
Switch-1 portlibs (SDL2, ffmpeg, python2.7, fribidi) link and run unchanged;
and the CMake platform file drops in as a one-line toolchain swap. The only
structural change is packaging (NSO-in-NSP → NRO under kaiHEN), and saves move
to the SD card by deleting the save-data code — the same pattern a shipping
Switch 2 port uses in production.

---

## 10. Implementation notes (deviations from §4/§5)

Two requirements were added after the plan was written: **one NRO per game
with the game's own name/branding**, and **one save folder per game**. That
produced three changes to the plan's minimal change set:

1. **`RENOUNCE_HOME` instead of five static strings (§5).** A static
   `sdmc:/renOunce/` in the patch would share one save folder across every
   game. Instead, `main.c` computes
   `sdmc:/renOunce/<RENOUNCE_GAME_ID>/` from a compile-time define
   (`-DRENOUNCE_GAME_ID=…`, fed by `SWITCH_GAME_ID` in
   `switch/CMakeLists.txt`), creates the folder tree with `mkdir()`, and
   exports it as the `RENOUNCE_HOME` environment variable before Python
   starts. Every `save:` site in `renpy.patch` became
   `os.environ.get("RENOUNCE_HOME", "sdmc:/renOunce") + "/…"`.
2. **All 9 `save:` sites, not 5.** The plan's table missed two that also
   break once the `save:` device is gone: `log.py`'s
   `real_open("save://Logs/log.log")` (unwrapped — it would crash the first
   log write) and `renpy.py`'s traceback hook `open("save://otrh.log")`.
   Both now use `RENOUNCE_HOME`. The two `romfs:`-only searchpath guards in
   `loader.py` also accept `sdmc:` entries, which makes the `main.py`
   searchpath entry functional instead of the silent no-op it was
   upstream (`os.path.join(basedir, "save://", name)`).
3. **No NRO in `build.bash`.** §4 moved the `.nso` → `.nro` rename inside
   `build.bash`, but a generic engine-only NRO would embed the romfs
   *before* `build.bash` populates it (the executable build used to run
   earlier in the script), and per-game branding must be baked at link time
   anyway. `build.bash` now stops at the engine template (`raw/` +
   `raw.zip`), and `build-game.bash` does the per-game cmake/NRO build.

Also worth knowing:

- `nx_create_nro`'s `ICON` argument is optional; without it the NRO gets
  libounce's `default_icon.jpg` (found via `NX_DEFAULT_ICON` in
  `Switch2.cmake`).
- The `save:` device never exists on renOunce, so `_otrhlibnx.commitsave()`
  is a no-op that only keeps the patch's call sites valid.
- Both CMake projects' `cmake_minimum_required` moved to 3.13 to match
  `Switch2.cmake`'s own requirement.
- `main.c`'s error strings no longer mention NSPs.

