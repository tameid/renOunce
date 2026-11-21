#!/usr/bin/env python3
"""Configure and build one Ren'Py game with the Switch 2 Podman container."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parent
CONTAINER = os.environ.get("RENONCE_CONTAINER", "renounce-dev")


def setting(source, key):
    match = re.search(
        r'^\s*define\s+' + re.escape(key) + r'\s*=\s*(?:_\()?\s*["\']([^"\']+)["\']',
        source, re.MULTILINE)
    return match.group(1) if match else None


def prompt(label, default):
    answer = input(f"{label} [{default}]: ").strip()
    return answer or default


def image_candidates(project, options):
    configured = setting(options, "config.window_icon")
    names = ([configured] if configured else []) + [
        "icon.png", "icon.jpg", "icon.jpeg", "icon.ico",
        "gui/window_icon.png", "gui/icon.png",
    ]
    for name in names:
        for base in (project / "game", project):
            candidate = base / name
            if candidate.is_file():
                yield candidate


def podman(*args):
    subprocess.run(["podman", "exec", "-w", "/work", CONTAINER, *args], check=True)


def main():
    if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help")):
        print("Usage: ./build-interactive.py [renpy-project]", file=sys.stderr)
        return 0 if len(sys.argv) == 2 else 2
    project = Path(sys.argv[1] if len(sys.argv) == 2 else input("Ruta del proyecto Ren'Py: ").strip()).expanduser().resolve()
    if not (project / "game").is_dir():
        print(f"No existe {project / 'game'}", file=sys.stderr)
        return 2
    options_path = project / "game/options.rpy"
    options = options_path.read_text(errors="replace") if options_path.exists() else ""
    name = prompt("Nombre", setting(options, "config.name") or project.name)
    author = prompt("Autor", "renOunce")
    version = prompt("Versión", setting(options, "config.version") or "1.0")
    default_id = re.sub(r"[^A-Za-z0-9._-]", "_", name) or "game"
    game_id = prompt("ID de guardado y archivo NRO", default_id)
    if not re.fullmatch(r"[A-Za-z0-9._-]+", game_id) or game_id in (".", ".."):
        print("El ID solo puede contener letras ASCII, números, punto, _ y -.", file=sys.stderr)
        return 2
    detected = next(image_candidates(project, options), None)
    icon_answer = input(f"Icono [{detected or 'predeterminado'}] (escribe - para omitir): ").strip()
    icon = None if icon_answer == "-" else Path(icon_answer).expanduser().resolve() if icon_answer else detected
    if icon and not icon.is_file():
        print(f"No existe el icono: {icon}", file=sys.stderr)
        return 2

    if not shutil.which("podman"):
        print("Falta podman.", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="build-interactive-", dir=REPO) as tmp:
        stage = Path(tmp)
        shutil.copytree(project / "game", stage / "project/game")
        build_args = ["bash", "/work/build-game.bash",
                      "/work/" + str((stage / "project").relative_to(REPO)),
                      "--name", name, "--author", author, "--version", version,
                      "--id", game_id, "--out", "/work/dist"]
        if icon:
            converter = shutil.which("magick") or shutil.which("convert")
            if not converter:
                print("Instala ImageMagick para convertir el icono a JPEG 256×256.", file=sys.stderr)
                return 2
            output = stage / "icon.jpg"
            subprocess.run([converter, str(icon) + "[0]", "-thumbnail", "256x256",
                            "-background", "white", "-gravity", "center",
                            "-extent", "256x256", "-strip", "-quality", "92",
                            str(output)], check=True)
            build_args += ["--icon", "/work/" + str(output.relative_to(REPO))]
        python_archive = REPO / "build-python27/source-build/libpython2.7-switch2.a"
        renpy_archive = REPO / "build-python27/renpy-modules/librenpy-switch-modules.a"
        if not python_archive.exists() or not renpy_archive.exists():
            print("Compilando el runtime de Switch 2…")
            podman("bash", "/work/build-switch2-runtime.bash")
        print(f"Compilando {name}…")
        podman("env", f"RENONCE_PYTHON_ARCHIVE=/work/{python_archive.relative_to(REPO)}",
               f"RENONCE_RENPY_ARCHIVE=/work/{renpy_archive.relative_to(REPO)}",
               *build_args)
    print(f"Listo: {REPO / 'dist' / (game_id + '.nro')}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
