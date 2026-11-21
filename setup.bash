set -e

export DEVKITPRO=/opt/devkitpro
export RENPY_VER=7.6.1
export PYGAME_SDL2_VER=2.1.0


# Debian buster is EOL; point apt at the archive mirror if needed.
if [ -f /etc/apt/sources.list ]; then
    sed -i 's|http://deb.debian.org/debian|http://archive.debian.org/debian|g; s|http://security.debian.org/debian-security|http://archive.debian.org/debian-security|g' /etc/apt/sources.list || true
fi
rm -f /etc/apt/sources.list.d/buster-backports.list
echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99no-check-valid-until 2>/dev/null || true
apt-get -y update
apt-get -y install python2.7 python-pip p7zip-full cython libsdl2-dev libsdl2-image-dev libjpeg-dev libpng-dev libsdl2-ttf-dev libsdl2-mixer-dev libavformat-dev libfreetype6-dev libswscale-dev libglew-dev libfribidi-dev libavcodec-dev  libswresample-dev libsdl2-gfx-dev libgl1-mesa-glx
pip2 install future six typing requests ecdsa pefile==2019.4.18 Cython==0.29.36

curl -LOC - https://github.com/Otorhin/scripts/releases/download/oof/devkitpro-pkgbuild-helpers-2.2.3-1-any.pkg.tar.xz
curl -LOC - https://github.com/Otorhin/scripts/releases/download/oof/python27-switch.tar.gz
curl -LOC - https://github.com/Otorhin/scripts/releases/download/oof/switch-libfribidi-1.0.12-1-any.pkg.tar.xz
dkp-pacman -U --noconfirm devkitpro-pkgbuild-helpers-2.2.3-1-any.pkg.tar.xz
dkp-pacman -U --noconfirm switch-libfribidi-1.0.12-1-any.pkg.tar.xz
tar -xf python27-switch.tar.gz -C $DEVKITPRO/portlibs/switch

rm devkitpro-pkgbuild-helpers-2.2.3-1-any.pkg.tar.xz
rm switch-libfribidi-1.0.12-1-any.pkg.tar.xz
rm python27-switch.tar.gz

# Install the ounce-devkit (Switch 2: libounce + OunceVK + switch2 toolchain)
# into the existing devkitPro. This is the only Switch 2 specific setup step.
if [ ! -d "$DEVKITPRO/libounce" ]; then
    curl -fsSL https://github.com/ouncebrew/ounce-devkit/releases/download/devkit-20261114/ounce-devkit-20261114.tar.xz | tar -xJ -C $DEVKITPRO
fi

# Work around binutils 2.32 (shipped in devkita64:20221113) not understanding
# the Cortex-A78C march's flagm+pauth extension: fall back to the Switch 1
# CPU flags, which ounce-devkit documents as still producing working code on
# Switch 2. Remove this once a newer binutils is available.
if [ -f "$DEVKITPRO/libounce/switch2_cpu.mk" ]; then
    sed -i 's|^SWITCH2_CPU.*|SWITCH2_CPU\t:=\t-march=armv8-a+crc+crypto -mtune=cortex-a57|' "$DEVKITPRO/libounce/switch2_cpu.mk"
fi

# Upgrade newlib to a release that provides the __sf symbol referenced by
# ounce-devkit's libounce (the r20 newlib in the base image lacks it).
export PATH="$DEVKITPRO/pacman/bin:$PATH"
pacman -Sy --noconfirm >/dev/null 2>&1 || true
if ! aarch64-none-elf-nm "$DEVKITPRO/devkitA64/aarch64-none-elf/lib/pic/libc.a" 2>/dev/null | grep -q ' B __sf$'; then
    pacman -S --overwrite '*' --noconfirm devkita64-newlib
fi

# Adapt libounce/libnx recursive-mutex init to the upgraded newlib, whose
# _LOCK_RECURSIVE_T has no thread_tag field.
for f in "$DEVKITPRO/libounce/include/switch/kernel/mutex.h" "$DEVKITPRO/libnx/include/switch/kernel/mutex.h"; do
    if [ -f "$f" ]; then
        sed -i '/m->thread_tag = 0;/d' "$f"
    fi
done


curl -LOC - https://www.renpy.org/dl/$RENPY_VER/pygame_sdl2-$PYGAME_SDL2_VER-for-renpy-$RENPY_VER.tar.gz
curl -LOC - https://www.renpy.org/dl/$RENPY_VER/renpy-$RENPY_VER-sdk.zip
curl -LOC - https://www.renpy.org/dl/$RENPY_VER/renpy-$RENPY_VER-source.tar.bz2
curl -LOC - https://www.renpy.org/dl/$RENPY_VER/android-native-symbols.zip
curl -LOC - https://dl.otorh.in/github/rawproject.zip || true


rm -rf pygame_sdl2-$PYGAME_SDL2_VER-for-renpy-$RENPY_VER pygame_sdl2-source
tar -xf pygame_sdl2-$PYGAME_SDL2_VER-for-renpy-$RENPY_VER.tar.gz
mv pygame_sdl2-$PYGAME_SDL2_VER-for-renpy-$RENPY_VER pygame_sdl2-source
rm pygame_sdl2-$PYGAME_SDL2_VER-for-renpy-$RENPY_VER.tar.gz

rm -rf renpy-$RENPY_VER-source renpy-source
tar -xf renpy-$RENPY_VER-source.tar.bz2
mv renpy-$RENPY_VER-source renpy-source
rm renpy-$RENPY_VER-source.tar.bz2

rm -rf renpy-$RENPY_VER-sdk renpy_sdk
unzip -qq renpy-$RENPY_VER-sdk.zip -d renpy_sdk
rm renpy-$RENPY_VER-sdk.zip

if [ -f rawproject.zip ]; then
    rm -rf raw
    unzip -qq rawproject.zip -d raw
    rm -f rawproject.zip
fi
mkdir -p raw

rm -rf android-native-symbols renpy_androidlib ./raw/android/lib
mkdir -p ./raw/android/lib
unzip -qq android-native-symbols.zip -d ./raw/android/lib
rm -rf ./raw/android/lib/x86_64/
rm android-native-symbols.zip

pushd renpy-source
patch -p1 < ../renpy.patch
pushd module
rm -rf gen gen-static
popd
popd
pushd pygame_sdl2-source
rm -rf gen gen-static
popd
