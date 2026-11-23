#!/usr/bin/env python3
"""Generate Python 3 inittab for the static Ren'Py extension archives."""
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('version', choices=('8.4.1', '8.6.1'))
parser.add_argument('output', type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
work = root / 'build-renpy8' / args.version
modules = []
if args.version == '8.4.1':
    renpy = work / 'renpy-8.4.1-source' / 'tmp/gen3-static'
    pygame = work / 'pygame_sdl2-2.1.0+renpy8.4.1' / 'gen3-static'
    modules = [(p.stem, p.stem.replace('.', '_')) for p in sorted(renpy.glob('*.c'))
               if p.stem != '_renpytfd']  # desktop file dialogs need termios
    if (renpy / 'renpy.gl2.assimp.cc').is_file():
        modules.append(('renpy.gl2.assimp', 'renpy_gl2_assimp'))
    modules += [(p.stem, p.stem.replace('.', '_')) for p in sorted(pygame.glob('*.c'))]
else:
    gen = work / 'renpy-8.6.1-source' / 'tmp/gen'
    for p in sorted(gen.rglob('*.c')):
        name = '.'.join(p.relative_to(gen).with_suffix('').parts)
        if name == 'renpy.gl2.assimp':
            continue  # unavailable Assimp target library
        modules.append((name, p.stem))
if not modules:
    parser.error('no generated C modules found')
symbols = [symbol for _, symbol in modules]
if len(symbols) != len(set(symbols)):
    parser.error('duplicate PyInit symbol names')
lines = ['#include <Python.h>', '']
lines += [f'extern PyObject *PyInit_{symbol}(void);' for symbol in symbols]
lines += ['', 'int register_renpy_modules(void)', '{']
lines += [f'    if (PyImport_AppendInittab("{name}", PyInit_{symbol}) < 0) return -1;'
          for name, symbol in modules]
lines += ['    return 0;', '}', '']
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text('\n'.join(lines))
print(f'{len(modules)} modules: {args.output}')
