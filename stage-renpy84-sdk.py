#!/usr/bin/env python3
"""Stage platform-neutral files from the complete official Ren'Py 8.4.1 SDK."""
from pathlib import Path
import shutil
import zipfile

root = Path(__file__).resolve().parent
sdk = root / 'build-renpy8/8.4.1/renpy-8.4.1-sdk'
pygame = root / 'build-renpy8/8.4.1/pygame_sdl2-2.1.0+renpy8.4.1/src'
stdlib = root / 'build-python312/Python-3.12.8/Lib'
contents = root / 'build-python312/romfs/Contents'
assert (sdk / 'lib/python3.12/encodings/__init__.pyc').is_file()
assert (sdk / 'renpy/__init__.py').is_file()
assert (pygame / 'pygame_sdl2/__init__.py').is_file()
contents.mkdir(parents=True, exist_ok=True)
archive_path = contents / 'lib.zip'
with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_STORED) as archive:
    seen = set()
    for base in (stdlib, sdk / 'lib/python3.12', sdk, pygame):
        if base == sdk:
            paths = (p for p in (sdk / 'renpy').rglob('*.py')
                     if 'common' not in p.relative_to(sdk).parts)
        elif base == pygame:
            paths = (p for p in (pygame / 'pygame_sdl2').rglob('*.py'))
        else:
            paths = (p for p in base.rglob('*') if p.is_file())
        for path in paths:
            relative = path.relative_to(base)
            excluded = {'idlelib', 'tkinter', 'turtledemo', '__pycache__', 'lib-dynload'}
            if base != sdk:
                excluded.update({'test', 'tests'})
            if any(part in excluded for part in relative.parts):
                continue
            if base == sdk / 'lib/python3.12' and path.suffix not in {'.py', '.pyc', '.pem', '.txt'}:
                continue
            name = relative.as_posix()
            if path.suffix == '.pyc' and name[:-1] in seen:
                continue
            if name in seen:
                continue
            if base == sdk and name == 'renpy/loader.py':
                original = path.read_text()
                old_scan = 'i = os.path.join(renpy.config.basedir, i)'
                new_scan = 'i = i if i.startswith(("romfs:/", "sdmc:/")) else os.path.join(renpy.config.basedir, i)'
                old_lookup = 'fn = os.path.join(renpy.config.basedir, d, path)'
                new_lookup = 'fn = os.path.join(d, path) if d.startswith(("romfs:/", "sdmc:/")) else os.path.join(renpy.config.basedir, d, path)'
                old_cache = 'fn = os.path.join(renpy.config.gamedir, fn)'
                new_cache = 'fn = os.path.join(os.environ["RENOUNCE_HOME"], fn) if fn.startswith("cache/") else os.path.join(renpy.config.gamedir, fn)'
                assert original.count(old_scan) == 1
                assert original.count(old_lookup) == 1
                assert original.count(old_cache) == 1
                archive.writestr(name, original.replace(old_scan, new_scan).replace(old_lookup, new_lookup).replace(old_cache, new_cache))
                seen.add(name)
                continue
            if base == sdk and name == 'renpy/savelocation.py':
                original = path.read_text()
                old = 'if (not renpy.mobile) and (not renpy.macapp):'
                new = 'if (not renpy.mobile) and (not renpy.macapp) and not renpy.config.gamedir.startswith("romfs:/"):'
                assert original.count(old) == 1
                archive.writestr(name, original.replace(old, new))
                seen.add(name)
                continue
            if base == sdk and name == 'renpy/script.py':
                original = path.read_text()
                old = 'if not renpy.macapp:'
                new = 'if not renpy.macapp and not rpycfn.startswith("romfs:/"):'
                assert original.count(old) == 1
                archive.writestr(name, original.replace(old, new))
                seen.add(name)
                continue
            archive.write(path, name)
            seen.add(name)
    archive.write(root / 'switch/python3/import_probe.py', 'renounce_import_probe.py')
    archive.write(root / 'switch/python3/engine_boot.py', 'renounce_engine_boot.py')
    archive.write(sdk / 'renpy.py', 'renpy_launcher.py')
shutil.copy2(sdk / 'renpy.py', contents / 'renpy.py')
common = sdk / 'renpy/common'
if common.is_dir():
    shutil.copytree(common, contents / 'renpy/common', dirs_exist_ok=True)
cursor_script = (root / 'switch/assets/renounce-cursor.rpy').read_text()
assert cursor_script.count('if renpy.switch:') == 1
(contents / 'renpy/common/zz_renounce_cursor.rpy').write_text(
    cursor_script.replace('if renpy.switch:', 'if True:'))
shutil.copy2(root / 'switch/assets/renounce-cursor.png',
             contents / 'renpy/common/_renounce_cursor.png')
print(f'Staged {len(seen)} Python files from CPython and official Ren\'Py SDK')
