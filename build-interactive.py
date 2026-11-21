#!/usr/bin/env python3
"""Import or configure a Ren'Py game and build it with the Switch 2 container."""

import argparse
import ast
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

REPO = Path(__file__).resolve().parent
CONTAINER = os.environ.get("RENONCE_CONTAINER", "renounce-dev")
PROJECTS = REPO / "projects"


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
        "gui/window_icon.png", "gui/icon.png", "gui/icon.ico",
    ]
    for name in names:
        for base in (project / "game", project):
            candidate = base / name
            if candidate.is_file():
                yield candidate


def podman(*args):
    subprocess.run(["podman", "exec", "-w", "/work", CONTAINER, *args], check=True)


def release_version(game):
    path = game / "script_version.txt"
    if not path.is_file():
        return None
    try:
        value = ast.literal_eval(path.read_text().strip())
    except (SyntaxError, ValueError):
        return None
    if isinstance(value, (tuple, list)) and len(value) >= 2 and all(isinstance(v, int) for v in value[:2]):
        return tuple(value)
    return None


def release_metadata(game):
    path = game / "cache/build_info.json"
    if not path.is_file():
        return {}
    try:
        info = json.loads(path.read_text())
        return {key: info[key] for key in ("name", "version") if isinstance(info.get(key), str)}
    except (OSError, ValueError):
        return {}


def find_game_folder(root):
    if root.name == "game" and root.is_dir():
        return root
    direct = root / "game"
    if direct.is_dir():
        return direct
    matches = [path for path in root.glob("*/game") if path.is_dir()]
    if len(matches) == 1:
        return matches[0]
    raise ValueError("No se encontró una única carpeta game/ en el release.")


def extract_release(archive, destination):
    with zipfile.ZipFile(archive) as package:
        for item in package.infolist():
            path = Path(item.filename)
            if path.is_absolute() or ".." in path.parts or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("El ZIP contiene una ruta o enlace no seguro.")
            target = destination / path
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with package.open(item) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)


def import_release(root, game, game_id, name, version, icon):
    PROJECTS.mkdir(exist_ok=True)
    target = PROJECTS / game_id
    if target.exists():
        raise ValueError(f"Ya existe {target}; elige otro ID para no sobrescribirlo.")
    target.mkdir()
    try:
        shutil.copytree(game, target / "game", ignore=shutil.ignore_patterns("cache", "saves", "log.txt", "traceback.txt"))
        if icon:
            icon_target = target / ("source-icon" + icon.suffix.lower())
            shutil.copy2(icon, icon_target)
        else:
            icon_target = None
        manifest = {
            "name": name, "version": version,
            "renpy_version": release_version(game),
            "imported_from": str(root),
            "icon": icon_target.name if icon_target else None,
        }
        (target / "renounce-project.json").write_text(json.dumps(manifest, indent=2) + "\n")
    except BaseException:
        shutil.rmtree(target)
        raise
    return target, icon_target


def main():
    parser = argparse.ArgumentParser(description="Importa un release o compila un proyecto Ren'Py para Switch 2.")
    parser.add_argument("project", nargs="?", help="Proyecto, carpeta game/ o release ZIP")
    parser.add_argument("--import-only", action="store_true", help="Crear el proyecto sin compilar")
    args = parser.parse_args()
    source = Path(args.project or input("Ruta del proyecto o release Ren'Py: ").strip()).expanduser().resolve()
    extracted_dir = tempfile.TemporaryDirectory(prefix="renounce-release-")
    root = source
    if source.is_file() and zipfile.is_zipfile(source):
        print("Extrayendo release ZIP…", flush=True)
        extract_release(source, Path(extracted_dir.name))
        root = Path(extracted_dir.name)
    game = find_game_folder(root)
    project = game.parent
    manifest_path = project / "renounce-project.json"
    try:
        manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    except ValueError:
        manifest = {}
    compiled_release = not manifest_path.is_file() and (
        source.is_file() or release_version(game) is not None or
        (not any(game.glob("*.rpy")) and any(game.glob("*.rpa"))))
    if compiled_release:
        detected_version = release_version(game)
        if detected_version:
            print("Release compilado con Ren'Py " + ".".join(map(str, detected_version)), flush=True)
    options_path = project / "game/options.rpy"
    options = options_path.read_text(errors="replace") if options_path.exists() else ""
    metadata = release_metadata(game) if compiled_release else {}
    name = prompt("Nombre", setting(options, "config.name") or manifest.get("name") or metadata.get("name") or project.name)
    author = prompt("Autor", "renOunce")
    version = prompt("Versión", setting(options, "config.version") or manifest.get("version") or metadata.get("version") or "1.0")
    default_id = re.sub(r"[^A-Za-z0-9._-]", "_", name) or "game"
    game_id = prompt("ID de guardado y archivo NRO", default_id)
    if not re.fullmatch(r"[A-Za-z0-9._-]+", game_id) or game_id in (".", ".."):
        print("El ID solo puede contener letras ASCII, números, punto, _ y -.", file=sys.stderr)
        return 2
    detected = (project / manifest["icon"] if manifest.get("icon") else None) or next(image_candidates(project, options), None)
    icon_answer = input(f"Icono [{detected or 'predeterminado'}] (escribe - para omitir): ").strip()
    icon = None if icon_answer == "-" else Path(icon_answer).expanduser().resolve() if icon_answer else detected
    if icon and not icon.is_file():
        print(f"No existe el icono: {icon}", file=sys.stderr)
        return 2

    if compiled_release:
        project, icon = import_release(source, game, game_id, name, version, icon)
        print(f"Proyecto creado: {project}", flush=True)
        if args.import_only:
            return 0
    elif args.import_only:
        print("La entrada ya es un proyecto; no hay nada que importar.")
        return 0

    game_version = release_version(project / "game")
    if game_version and (game_version[0] != 7 or game_version[:2] > (7, 6)):
        print(f"No se puede compilar este proyecto con el runtime actual (Ren'Py 7.6.1/Python 2.7): "
              f"el release usa Ren'Py {'.'.join(map(str, game_version))}. "
              "El proyecto importado queda disponible para un runtime compatible.", file=sys.stderr)
        return 2

    if not shutil.which("podman"):
        print("Falta podman.", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="build-interactive-", dir=REPO) as tmp:
        stage = Path(tmp)
        try:
            container_project = project.relative_to(REPO)
        except ValueError:
            shutil.copytree(project / "game", stage / "project/game", ignore=shutil.ignore_patterns("cache", "saves"))
            container_project = (stage / "project").relative_to(REPO)
        build_args = ["bash", "/work/build-game.bash",
                      "/work/" + str(container_project),
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
        print(f"Compilando {name}…", flush=True)
        podman("env", f"RENONCE_PYTHON_ARCHIVE=/work/{python_archive.relative_to(REPO)}",
               f"RENONCE_RENPY_ARCHIVE=/work/{renpy_archive.relative_to(REPO)}",
               *build_args)
    print(f"Listo: {REPO / 'dist' / (game_id + '.nro')}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
