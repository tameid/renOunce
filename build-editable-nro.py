#!/usr/bin/env python3
"""Publish a clean engine NRO as a packager base, without modifying it."""

import argparse
from pathlib import Path
import os
import tempfile

from packager.build import engine_version
from packager.nro import read_nro, read_romfs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine_nro', type=Path)
    parser.add_argument('--version', required=True, choices=('7.6.1', '8.4.1'))
    args = parser.parse_args()
    source = args.engine_nro.resolve()
    if engine_version(source) != args.version:
        parser.error(f'{source} is not a Ren\'Py {args.version} engine NRO')
    blob, assets, sections = read_nro(source)
    offset, size = sections[2]
    root = read_romfs(memoryview(blob)[assets + offset:assets + offset + size])
    contents = root.dirs.get('Contents')
    if contents is None or 'game' in contents.dirs or 'renounce-game-id' in contents.files:
        parser.error(f'{source} is not a clean engine-only NRO')
    target = Path(__file__).resolve().parent / 'packager' / f'renounce-base-{args.version}.nro'
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, staged = tempfile.mkstemp(prefix='.renounce-base-', suffix='.nro', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as output, source.open('rb') as input_file:
            while chunk := input_file.read(1024 * 1024):
                output.write(chunk)
        os.replace(staged, target)
    finally:
        if os.path.exists(staged):
            os.unlink(staged)
    print(target)


if __name__ == '__main__':
    main()
