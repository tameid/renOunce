#!/usr/bin/env python3
"""Build a game from an immutable packager base NRO."""

import argparse
from pathlib import Path

from packager.build import build, project_defaults


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--id', required=True)
    parser.add_argument('--name')
    parser.add_argument('--author', default='renOunce')
    parser.add_argument('--version')
    parser.add_argument('--icon', type=Path)
    parser.add_argument('--out', type=Path, default=Path('dist'))
    args = parser.parse_args()
    default_name, default_version = project_defaults(args.project)
    output = args.out / (args.id + '.nro')
    build(args.project, args.base, output, args.name or default_name,
          args.author, args.version or default_version, args.id, args.icon)
    print(output)


if __name__ == '__main__':
    main()
