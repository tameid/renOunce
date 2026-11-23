import struct
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from packager.build import _patch_native_game_id, _patch_python3_boot, build
from packager.nro import Directory, File, read_nro, read_romfs, write_romfs


class PackagerTest(unittest.TestCase):
    def test_build_preserves_engine_and_adds_game(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            project = directory / 'project'
            (project / 'game').mkdir(parents=True)
            (project / 'game/script.rpy').write_text('label start:\n    "Hola"\n')
            root = Directory('')
            contents = Directory('Contents')
            root.dirs['Contents'] = contents
            library = BytesIO()
            with ZipFile(library, 'w') as archive:
                archive.writestr('python2.7/pygame_sdl2/__init__.py', '')
                archive.writestr('python2.7/builtins/__init__.pyo', '')
            contents.files['lib.zip'] = File('lib.zip', library.getvalue())
            contents.files['renpy.py'] = File('renpy.py', b'engine-script')
            executable = bytearray(0x100)
            executable[0x10:0x14] = b'NRO0'
            struct.pack_into('<I', executable, 0x18, 0x100)
            marker = b'romfs:/Contents/renounce-game-id'
            executable[0x40:0x40 + len(marker)] = marker
            executable.extend(b'ASET' + b'\0' * 52)
            nacp = bytearray(0x4000)
            nacp[0x3060:0x3065] = b'7.6.1'
            for index, part in enumerate((b'icon', nacp, write_romfs(root))):
                struct.pack_into('<QQ', executable, 0x108 + index * 16,
                                 len(executable) - 0x100, len(part))
                executable.extend(part)
            base = directory / 'base.nro'
            base.write_bytes(executable)
            output = directory / 'game.nro'
            build(project, base, output, 'Mi juego', 'Autora', '1.2', 'MiJuego')
            blob, assets, sections = read_nro(output)
            romfs_offset, romfs_size = sections[2]
            result = read_romfs(memoryview(blob)[assets + romfs_offset:
                                                  assets + romfs_offset + romfs_size])
            packed = result.dirs['Contents']
            self.assertEqual(bytes(packed.files['lib.zip'].data), library.getvalue())
            self.assertEqual(bytes(packed.files['renounce-game-id'].data), b'MiJuego\n')
            self.assertIn('script.rpy', packed.dirs['game'].files)
            nacp_offset, _ = sections[1]
            self.assertTrue(blob[assets + nacp_offset:].startswith('Mi juego'.encode()))

    def test_rejects_unsafe_game_id(self):
        with self.assertRaises(ValueError):
            build('.', 'base.nro', 'out.nro', 'Name', 'Author', '1', '../other')

    def test_python3_boot_uses_packaged_id(self):
        original = BytesIO()
        with ZipFile(original, 'w') as archive:
            archive.writestr('renounce_engine_boot.py',
                             'import os\nimport sys\nimport _otrhlibnx\n'
                             'home = _otrhlibnx.get_home()\n'
                             'os.environ["RENOUNCE_HOME"] = home\n'
                             'renpy_launcher.path_to_saves = lambda gamedir, save_directory=None: home + "/Data"\n'
                             'try:\n    renpy.bootstrap.bootstrap("romfs:/Contents")\n'
                             'finally:\n    pass\n')
            archive.writestr('pygame_sdl2/__init__.py', '')
        patched = _patch_python3_boot(original.getvalue())
        with ZipFile(BytesIO(patched)) as archive:
            boot = archive.read('renounce_engine_boot.py').decode()
            compile(boot, 'renounce_engine_boot.py', 'exec')
            self.assertIn('renounce-game-id', boot)
            self.assertIn('packaged_game_id', boot)
            self.assertIn('Native save folder does not match', boot)
            self.assertIn('boot.log', boot)
            self.assertIn('Entering RenPy bootstrap', boot)
            self.assertIn('def path_to_saves', boot)
            self.assertNotIn('path_to_saves = lambda', boot)
            self.assertIn('pygame_sdl2/__init__.py', archive.namelist())

    def test_python3_native_folder_uses_game_id(self):
        executable = bytearray(0x100)
        struct.pack_into('<I', executable, 0x18, len(executable))
        original = b'renpy-8.4.1-engine'
        executable[0x40:0x40 + len(original)] = original
        patched = _patch_native_game_id(executable, 'MyGame')
        self.assertNotIn(original, patched)
        self.assertEqual(patched[0x40:0x40 + len(original)], b'MyGame' + b'\0' * 12)
        with self.assertRaises(ValueError):
            _patch_native_game_id(executable, 'ID-is-longer-than-18')



if __name__ == '__main__':
    unittest.main()
