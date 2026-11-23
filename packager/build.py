"""Public API for building a game NRO without a Switch toolchain."""

from pathlib import Path
import os
import re
import tempfile
from io import BytesIO
from zipfile import BadZipFile, ZipFile

from .nro import Directory, File, read_nro, read_romfs, write_nro, write_romfs


def engine_version(base_nro):
    blob, assets, sections = read_nro(base_nro)
    offset, length = sections[1]
    if length != 0x4000:
        raise ValueError('NACP del motor no reconocido')
    version = blob[assets + offset + 0x3060:assets + offset + 0x3070]
    return version.split(b'\0', 1)[0].decode('utf-8')


def option(source, key):
    match = re.search(r'^\s*define\s+' + re.escape(key) +
                      r'\s*=\s*(?:_\()?\s*["\']([^"\']+)["\']', source, re.MULTILINE)
    return match.group(1) if match else None


def project_defaults(project):
    project = Path(project)
    options = project / 'game/options.rpy'
    source = options.read_text(errors='replace') if options.exists() else ''
    return option(source, 'config.name') or project.name, option(source, 'config.version') or '1.0'


def _put_text(buffer, offset, limit, value):
    encoded = value.encode('utf-8')
    if len(encoded) >= limit:
        raise ValueError(f'Texto demasiado largo: {value[:40]}')
    buffer[offset:offset + limit] = encoded + b'\0' * (limit - len(encoded))


def _nacp(base, name, author, version):
    nacp = bytearray(base)
    if len(nacp) != 0x4000:
        raise ValueError('NACP del motor no reconocido')
    for language in range(12):
        _put_text(nacp, language * 0x300, 0x200, name)
        _put_text(nacp, language * 0x300 + 0x200, 0x100, author)
    _put_text(nacp, 0x3060, 0x10, version)
    return bytes(nacp)


def _icon(path):
    if path is None:
        return None
    from PIL import Image, ImageOps
    from io import BytesIO
    with Image.open(path) as original:
        image = ImageOps.pad(original.convert('RGB'), (256, 256), color='white')
        output = BytesIO()
        image.save(output, format='JPEG', quality=92)
        return output.getvalue()


def _patch_python3_boot(library):
    """Make the 8.4.1 Python boot script use the packaged save ID."""
    source = b'home = _otrhlibnx.get_home()'
    replacement = (b'with open("romfs:/Contents/renounce-game-id", "r", encoding="ascii") as game_id_file:\n'
                   b'    packaged_game_id = game_id_file.read().strip()\n'
                   b'home = _otrhlibnx.get_home()\n'
                   b'if os.path.basename(home.rstrip("/")) != packaged_game_id:\n'
                   b'    raise RuntimeError("Native save folder does not match packaged game ID")')
    log_setup = (b'\nimport traceback\n'
                 b'def _renounce_boot_log(message):\n'
                 b'    with open(home + "/Logs/boot.log", "a", encoding="utf-8") as log_file:\n'
                 b'        log_file.write(message + "\\n")\n'
                 b'def _renounce_excepthook(exc_type, exc_value, exc_traceback):\n'
                 b'    with open(home + "/Logs/boot.log", "a", encoding="utf-8") as log_file:\n'
                 b'        traceback.print_exception(exc_type, exc_value, exc_traceback, file=log_file)\n'
                 b'    sys.__excepthook__(exc_type, exc_value, exc_traceback)\n'
                 b'sys.excepthook = _renounce_excepthook\n'
                 b'_renounce_boot_log("Directories created; starting RenPy")\n')
    bootstrap_markers = (
        (b'    # Check that we have installed pygame properly.', b'checking pygame_sdl2'),
        (b'    gamedir = renpy.__main__.path_to_gamedir(basedir, name)', b'pygame_sdl2 loaded'),
        (b'    # Ditto for the Ren\'Py module.', b'loading _renpy'),
        (b'    # Load the rest of Ren\'Py.', b'_renpy loaded'),
        (b'    renpy.import_all()', b'loading RenPy modules'),
        (b'    renpy.importer.init_importer()', b'RenPy modules loaded'),
        (b'                renpy.main.main()', b'entering renpy.main.main'),
    )
    save_lambda = b'renpy_launcher.path_to_saves = lambda gamedir, save_directory=None: home + "/Data"'
    save_function = (b'def path_to_saves(gamedir, save_directory=None):\n'
                     b'    return home + "/Data"\n\n'
                     b'renpy_launcher.path_to_saves = path_to_saves')
    output = BytesIO()
    with ZipFile(BytesIO(library)) as archive, ZipFile(output, 'w') as target:
        if 'renounce_engine_boot.py' not in archive.namelist():
            raise ValueError('El motor 8.4.1 no contiene renounce_engine_boot.py')
        for member in archive.infolist():
            data = archive.read(member.filename)
            if member.filename == 'renounce_engine_boot.py':
                if data.count(source) != 1:
                    raise ValueError('El arranque de Ren\'Py 8.4.1 no tiene el formato esperado')
                data = data.replace(source, replacement)
                anchor = b'os.environ["RENOUNCE_HOME"] = home\n'
                if data.count(anchor) != 1:
                    raise ValueError('No se encontró la inicialización de Ren\'Py 8.4.1')
                data = data.replace(anchor, log_setup + anchor)
                bootstrap = b'    renpy.bootstrap.bootstrap("romfs:/Contents")'
                if data.count(bootstrap) != 1:
                    raise ValueError('No se encontró el arranque de Ren\'Py 8.4.1')
                data = data.replace(bootstrap, b'    _renounce_boot_log("Entering RenPy bootstrap")\n' + bootstrap)
                if data.count(save_lambda) != 1:
                    raise ValueError('No se encontró path_to_saves en el arranque de Ren\'Py 8.4.1')
                data = data.replace(save_lambda, save_function)
                data = data.replace(b'finally:\n    shutil.rmtree(sd_temp_dir, ignore_errors=True)',
                                    b'except SystemExit as exit_status:\n'
                                    b'    _renounce_boot_log("RenPy exited: " + str(exit_status.code))\n'
                                    b'    raise\n'
                                    b'except Exception:\n'
                                    b'    with open(home + "/Logs/boot.log", "a", encoding="utf-8") as log_file:\n'
                                    b'        traceback.print_exc(file=log_file)\n'
                                    b'    raise\n'
                                    b'finally:\n    shutil.rmtree(sd_temp_dir, ignore_errors=True)')
            elif member.filename == 'renpy/bootstrap.py':
                data = data.replace(b'def bootstrap(renpy_base):',
                                    b'def bootstrap(renpy_base):\n'
                                    b'    from renounce_engine_boot import _renounce_boot_log')
                for anchor, message in bootstrap_markers:
                    if anchor not in data:
                        raise ValueError('El bootstrap de Ren\'Py 8.4.1 no tiene el formato esperado')
                    indent = anchor[:len(anchor) - len(anchor.lstrip())]
                    data = data.replace(anchor, indent + b'_renounce_boot_log("' + message + b'")\n' + anchor, 1)
            target.writestr(member, data)
    return output.getvalue()


def _patch_native_game_id(nro, game_id):
    """Replace the fixed native save folder in the Ren'Py 8.4.1 launcher."""
    original = b'renpy-8.4.1-engine'
    encoded = game_id.encode('ascii')
    if len(encoded) > len(original):
        raise ValueError('En Ren\'Py 8.4.1 el ID de guardado admite como máximo 18 caracteres')
    image = bytearray(nro)
    executable_end = int.from_bytes(image[0x18:0x1c], 'little')
    if image[:executable_end].count(original) != 1:
        raise ValueError('El NRO base de Ren\'Py 8.4.1 no tiene el ID nativo esperado')
    offset = image[:executable_end].index(original)
    image[offset:offset + len(original)] = encoded + b'\0' * (len(original) - len(encoded))
    return bytes(image)


def _game_tree(project):
    game_dir = project / 'game'
    if not game_dir.is_dir():
        raise ValueError(f'No existe {game_dir}')
    root = Directory('game')
    count = 0
    for source in sorted(game_dir.rglob('*')):
        if source.is_symlink():
            raise ValueError(f'El juego contiene un enlace simbólico: {source}')
        relative = source.relative_to(game_dir)
        parent = root
        for part in relative.parts[:-1]:
            parent = parent.dirs.setdefault(part, Directory(part))
        if source.is_dir():
            parent.dirs.setdefault(source.name, Directory(source.name))
        elif source.is_file():
            parent.files[source.name] = File(source.name, source.read_bytes())
            count += 1
    if count == 0:
        raise ValueError('La carpeta game/ está vacía')
    return root


def build(project, base_nro, output, name, author, version, game_id, icon=None, progress=None):
    project, base_nro, output = Path(project), Path(base_nro), Path(output)
    if not re.fullmatch(r'[A-Za-z0-9._-]+', game_id) or game_id in ('.', '..') or len(game_id) > 126:
        raise ValueError('ID inválido: usa letras ASCII, números, punto, _ o - (máximo 126)')
    if not all((name, author, version)):
        raise ValueError('Nombre, autor y versión son obligatorios')
    if progress:
        progress('Leyendo el NRO base…')
    blob, assets, sections = read_nro(base_nro)
    nacp_offset, nacp_size = sections[1]
    if nacp_size != 0x4000:
        raise ValueError('NACP del motor no reconocido')
    base_version = blob[assets + nacp_offset + 0x3060:assets + nacp_offset + 0x3070].split(b'\0', 1)[0].decode('utf-8')
    if base_version not in ('7.6.1', '8.4.1'):
        raise ValueError(f'El motor Ren\'Py {base_version or "desconocido"} aún no está admitido por este empaquetador')
    if base_version == '8.4.1' and len(game_id) > len('renpy-8.4.1-engine'):
        raise ValueError('En Ren\'Py 8.4.1 el ID de guardado admite como máximo 18 caracteres')
    if base_version == '7.6.1' and b'romfs:/Contents/renounce-game-id' not in blob[:assets]:
        raise ValueError('Este NRO base no admite el ID de guardado empaquetado; recompila el motor actualizado')
    romfs_offset, romfs_size = sections[2]
    root = read_romfs(memoryview(blob)[assets + romfs_offset:assets + romfs_offset + romfs_size])
    if 'Contents' not in root.dirs:
        raise ValueError('El NRO base no contiene Contents/')
    contents = root.dirs['Contents']
    if 'lib.zip' not in contents.files or 'renpy.py' not in contents.files:
        raise ValueError('El NRO base no contiene lib.zip y renpy.py')
    try:
        with ZipFile(BytesIO(contents.files['lib.zip'].data)) as archive:
            members = set(archive.namelist())
    except BadZipFile as exc:
        raise ValueError('El NRO base contiene un lib.zip inválido') from exc
    if base_version == '7.6.1':
        required = {'python2.7/pygame_sdl2/__init__.py', 'python2.7/builtins/__init__.pyo'}
    else:
        required = {'pygame_sdl2/__init__.py', 'renounce_engine_boot.py'}
    if not required.issubset(members):
        raise ValueError('El NRO base tiene un lib.zip incompleto; faltan módulos de arranque o pygame_sdl2')
    if base_version == '8.4.1':
        contents.files['lib.zip'] = File('lib.zip', _patch_python3_boot(bytes(contents.files['lib.zip'].data)))
    if progress:
        progress('Añadiendo archivos del juego…')
    contents.dirs['game'] = _game_tree(project)
    contents.files['renounce-game-id'] = File('renounce-game-id', (game_id + '\n').encode('ascii'))
    nacp = _nacp(blob[assets + nacp_offset:assets + nacp_offset + nacp_size], name, author, version)
    icon_bytes = _icon(icon)
    if progress:
        progress('Reconstruyendo romfs y NRO…')
    result = write_nro(base_nro, write_romfs(root), nacp, icon_bytes)
    if base_version == '8.4.1':
        result = _patch_native_game_id(result, game_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.renounce-', suffix='.nro', dir=output.parent)
    try:
        with os.fdopen(fd, 'wb') as target:
            target.write(result)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    if progress:
        progress(f'Listo: {output}')
    return output
