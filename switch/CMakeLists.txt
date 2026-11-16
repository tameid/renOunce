cmake_minimum_required(VERSION 3.13)

if(NOT DEFINED CMAKE_TOOLCHAIN_FILE)
    if(DEFINED ENV{DEVKITPRO})
        set(DEVKITPRO $ENV{DEVKITPRO})
        set(CMAKE_TOOLCHAIN_FILE "$ENV{DEVKITPRO}/libounce/cmake/Switch2.cmake" CACHE PATH "toolchain file")
    else()
        message(FATAL_ERROR "Please define DEVKITPRO to point to your SDK path!")
    endif()
endif()

project(renpy-switch)

# Per-game branding. build-game.bash overrides all of these per game; the
# defaults build a generic engine-only NRO.
#
# SWITCH_GAME_ID picks the save folder: the game's saves, logs, cache and
# persistent data all live under sdmc:/renOunce/<SWITCH_GAME_ID>/, so two
# games never see each other's data. It defaults to the app name with every
# character outside [A-Za-z0-9._-] turned into '_'.
set(SWITCH_APP_NAME "Ren'Py" CACHE STRING "Title shown on the Switch 2 home menu")
set(SWITCH_AUTHOR   "renpytom" CACHE STRING "Author shown on the Switch 2 home menu")
set(SWITCH_VERSION  "7.6.1" CACHE STRING "Version shown on the Switch 2 home menu")
set(SWITCH_GAME_ID  "" CACHE STRING "Save folder id under sdmc:/renOunce/ (must be unique per game)")
set(SWITCH_ICON     "" CACHE FILEPATH "256x256 JPEG icon for the NRO (empty = libounce default icon)")
set(SWITCH_ROMFS    "${CMAKE_SOURCE_DIR}/../raw/switch/romfs" CACHE PATH "romfs directory embedded into the NRO")

if(NOT SWITCH_GAME_ID)
    set(SWITCH_GAME_ID "${SWITCH_APP_NAME}")
endif()
string(REGEX REPLACE "[^A-Za-z0-9._-]" "_" SWITCH_GAME_ID "${SWITCH_GAME_ID}")
if(NOT SWITCH_GAME_ID)
    set(SWITCH_GAME_ID "game")
endif()

message(STATUS "renOunce game: name='${SWITCH_APP_NAME}' save folder='sdmc:/renOunce/${SWITCH_GAME_ID}/'")

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE RelWithDebInfo)
endif()

set(C_FLAGS
    -DFRIBIDI_ENTRY=
    -DHAVE_CONFIG_H=1
)

set(OPTIMIZATION_FLAGS
    -Ofast
)

set(INCLUDES
    ${DEVKITPRO}/portlibs/switch/include/python2.7
)

set(SOURCES
    source/main.c
)

set(CMAKE_PREFIX_PATH "${DEVKITPRO}/portlibs/switch")
set(ENV{PKG_CONFIG_PATH} "${DEVKITPRO}/portlibs/switch/lib/pkgconfig")

find_package(PkgConfig REQUIRED)
# Workaround for library paths not being set correctly
set(pkgcfg_lib_FREETYPE2_nx ${DEVKITPRO}/libounce/lib/libnx.a)
set(pkgcfg_lib_LIBAVFILTER_nx ${DEVKITPRO}/libounce/lib/libnx.a)
set(pkgcfg_lib_LIBAVFORMAT_nx ${DEVKITPRO}/libounce/lib/libnx.a)
set(pkgcfg_lib_EGL_m /opt/devkitpro/devkitA64/aarch64-none-elf/lib/pic/libm.a)
set(pkgcfg_lib_FREETYPE2_m /opt/devkitpro/devkitA64/aarch64-none-elf/lib/pic/libm.a)
set(pkgcfg_lib_GLAPI_m /opt/devkitpro/devkitA64/aarch64-none-elf/lib/pic/libm.a)
set(pkgcfg_lib_GLESV2_m /opt/devkitpro/devkitA64/aarch64-none-elf/lib/pic/libm.a)
set(pkgcfg_lib_LIBAVCODEC_m /opt/devkitpro/devkitA64/aarch64-none-elf/lib/libm.a)
set(pkgcfg_lib_LIBAVFILTER_m /opt/devkitpro/devkitA64/aarch64-none-elf/lib/libm.a)
set(pkgcfg_lib_LIBAVFORMAT_m /opt/devkitpro/devkitA64/aarch64-none-elf/lib/libm.a)
set(pkgcfg_lib_LIBAVUTIL_m /opt/devkitpro/devkitA64/aarch64-none-elf/lib/libm.a)
set(pkgcfg_lib_LIBSWRESAMPLE_m /opt/devkitpro/devkitA64/aarch64-none-elf/lib/libm.a)
set(pkgcfg_lib_LIBSWSCALE_m /opt/devkitpro/devkitA64/aarch64-none-elf/lib/libm.a)
set(pkgcfg_lib_SDL2_IMAGE_m /opt/devkitpro/devkitA64/aarch64-none-elf/lib/libm.a)
set(pkgcfg_lib_SDL2_MIXER_m /opt/devkitpro/devkitA64/aarch64-none-elf/lib/libm.a)
set(pkgcfg_lib_SDL2_TTF_m /opt/devkitpro/devkitA64/aarch64-none-elf/lib/libm.a)
# The Switch 1 mesa pins (libEGL.a / libglapi.a / libdrm_nouveau.a) are gone:
# the Switch 2 pkg-config wrapper resolves egl/glesv2/glapi/libdrm_nouveau to
# OunceVK's real libEGL.a and its empty stubs, and hard pins would silently
# link the Switch 1 mesa archives again.
set(pkgcfg_lib_SDL2_GFX_SDL2 /opt/devkitpro/portlibs/switch/lib/libSDL2.a)
set(pkgcfg_lib_SDL2_IMAGE_SDL2 /opt/devkitpro/portlibs/switch/lib/libSDL2.a)
set(pkgcfg_lib_SDL2_MIXER_SDL2 /opt/devkitpro/portlibs/switch/lib/libSDL2.a)
set(pkgcfg_lib_SDL2_SDL2 /opt/devkitpro/portlibs/switch/lib/libSDL2.a)
set(pkgcfg_lib_SDL2_TTF_SDL2 /opt/devkitpro/portlibs/switch/lib/libSDL2.a)
set(pkgcfg_lib_SDL2_IMAGE_z /opt/devkitpro/portlibs/switch/lib/libz.a)
set(pkgcfg_lib_SDL2_TTF_z /opt/devkitpro/portlibs/switch/lib/libz.a)
set(pkgcfg_lib_SDL2_IMAGE_SDL2_image /opt/devkitpro/portlibs/switch/lib/libSDL2_image.a)
set(pkgcfg_lib_SDL2_GFX_SDL2_gfx /opt/devkitpro/portlibs/switch/lib/libSDL2_gfx.a)
set(pkgcfg_lib_SDL2_IMAGE_jpeg /opt/devkitpro/portlibs/switch/lib/libjpeg.a)
set(pkgcfg_lib_SDL2_IMAGE_png16 /opt/devkitpro/portlibs/switch/lib/libpng16.a)
set(pkgcfg_lib_SDL2_IMAGE_webp /opt/devkitpro/portlibs/switch/lib/libwebp.a)
set(pkgcfg_lib_SDL2_MIXER_SDL2_mixer /opt/devkitpro/portlibs/switch/lib/libSDL2_mixer.a)
set(pkgcfg_lib_SDL2_MIXER_modplug /opt/devkitpro/portlibs/switch/lib/libmodplug.a)
set(pkgcfg_lib_SDL2_MIXER_mpg123 /opt/devkitpro/portlibs/switch/lib/libmpg123.a)
set(pkgcfg_lib_SDL2_MIXER_ogg /opt/devkitpro/portlibs/switch/lib/libogg.a)
set(pkgcfg_lib_SDL2_MIXER_opus /opt/devkitpro/portlibs/switch/lib/libopus.a)
set(pkgcfg_lib_SDL2_MIXER_opusfile /opt/devkitpro/portlibs/switch/lib/libopusfile.a)
set(pkgcfg_lib_SDL2_MIXER_stdc++ /opt/devkitpro/devkitA64/aarch64-none-elf/lib/pic/libstdc++.a)
set(pkgcfg_lib_SDL2_MIXER_vorbisidec /opt/devkitpro/portlibs/switch/lib/libvorbisidec.a)
set(pkgcfg_lib_SDL2_TTF_SDL2_ttf /opt/devkitpro/portlibs/switch/lib/libSDL2_ttf.a)
set(pkgcfg_lib_SDL2_TTF_bz2 /opt/devkitpro/portlibs/switch/lib/libbz2.a)
set(pkgcfg_lib_SDL2_TTF_freetype /opt/devkitpro/portlibs/switch/lib/libfreetype.a)
set(pkgcfg_lib_SDL2_TTF_png16 /opt/devkitpro/portlibs/switch/lib/libpng16.a)

pkg_check_modules(EGL REQUIRED IMPORTED_TARGET egl)
pkg_check_modules(FREETYPE2 REQUIRED IMPORTED_TARGET freetype2)
pkg_check_modules(GLAPI REQUIRED IMPORTED_TARGET glapi)
pkg_check_modules(GLESV2 REQUIRED IMPORTED_TARGET glesv2)
pkg_check_modules(LIBAVCODEC REQUIRED IMPORTED_TARGET libavcodec)
pkg_check_modules(LIBAVFILTER REQUIRED IMPORTED_TARGET libavfilter)
pkg_check_modules(LIBAVFORMAT REQUIRED IMPORTED_TARGET libavformat)
pkg_check_modules(LIBAVUTIL REQUIRED IMPORTED_TARGET libavutil)
pkg_check_modules(LIBDRM_NOUVEAU REQUIRED IMPORTED_TARGET libdrm_nouveau)
pkg_check_modules(LIBSWRESAMPLE REQUIRED IMPORTED_TARGET libswresample)
pkg_check_modules(LIBSWSCALE REQUIRED IMPORTED_TARGET libswscale)
pkg_check_modules(SDL2 REQUIRED IMPORTED_TARGET sdl2)
pkg_check_modules(SDL2_GFX REQUIRED IMPORTED_TARGET SDL2_gfx)
pkg_check_modules(SDL2_IMAGE REQUIRED IMPORTED_TARGET SDL2_image)
pkg_check_modules(SDL2_MIXER REQUIRED IMPORTED_TARGET SDL2_mixer)
pkg_check_modules(SDL2_TTF REQUIRED IMPORTED_TARGET SDL2_ttf)
pkg_check_modules(ZLIB REQUIRED IMPORTED_TARGET zlib)

# Workaround for pkg-config not expanding $(DEVKITPRO)
if(LIBDRM_NOUVEAU_INCLUDE_DIRS)
    set_property(TARGET PkgConfig::LIBDRM_NOUVEAU PROPERTY
                 INTERFACE_INCLUDE_DIRECTORIES "${DEVKITPRO}/portlibs/switch/include")
endif()

add_executable(${PROJECT_NAME} ${SOURCES})

target_link_libraries(${PROJECT_NAME}
    ${DEVKITPRO}/portlibs/switch/lib/libpython2.7.a
    ${DEVKITPRO}/portlibs/switch/lib/librenpy-switch-modules.a
    m
    PkgConfig::EGL
    PkgConfig::FREETYPE2
    PkgConfig::GLAPI
    PkgConfig::GLESV2
    PkgConfig::LIBAVCODEC
    PkgConfig::LIBAVFILTER
    PkgConfig::LIBAVFORMAT
    PkgConfig::LIBAVUTIL
    PkgConfig::LIBDRM_NOUVEAU
    PkgConfig::LIBSWRESAMPLE
    PkgConfig::LIBSWSCALE
    PkgConfig::SDL2
    PkgConfig::SDL2_GFX
    PkgConfig::SDL2_IMAGE
    PkgConfig::SDL2_MIXER
    PkgConfig::SDL2_TTF
    PkgConfig::ZLIB
)

target_include_directories(${PROJECT_NAME} PUBLIC ${INCLUDES})
target_compile_definitions(${PROJECT_NAME} PRIVATE RENOUNCE_GAME_ID="${SWITCH_GAME_ID}")
target_compile_options(${PROJECT_NAME} PUBLIC $<$<COMPILE_LANGUAGE:C>:${C_FLAGS}>)
target_compile_options(${PROJECT_NAME} PUBLIC $<$<CONFIG:RELEASE>:${OPTIMIZATION_FLAGS}>)
target_compile_options(${PROJECT_NAME} PUBLIC $<$<CONFIG:RELWITHDEBINFO>:${OPTIMIZATION_FLAGS}>)
set_target_properties(${PROJECT_NAME} PROPERTIES LINKER_LANGUAGE CXX)

nx_generate_nacp(${PROJECT_NAME}.nacp
    NAME "${SWITCH_APP_NAME}"
    AUTHOR "${SWITCH_AUTHOR}"
    VERSION "${SWITCH_VERSION}"
)

if(SWITCH_ICON)
    nx_create_nro(${PROJECT_NAME}
        NACP ${PROJECT_NAME}.nacp
        ICON "${SWITCH_ICON}"
        ROMFS "${SWITCH_ROMFS}"
    )
else()
    nx_create_nro(${PROJECT_NAME}
        NACP ${PROJECT_NAME}.nacp
        ROMFS "${SWITCH_ROMFS}"
    )
endif()
