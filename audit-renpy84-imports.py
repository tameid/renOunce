#!/usr/bin/env python3
"""Check every explicit Ren'Py import in the official import_all() routine."""

import ast
from pathlib import Path
import re
from zipfile import ZipFile

root = Path(__file__).resolve().parent
source = root / "build-renpy8/8.4.1/renpy-8.4.1-sdk/renpy/__init__.py"
archive = root / "build-python312/romfs/Contents/lib.zip"
table = root / "build-module-tables/renpy84.c"
function = next(node for node in ast.parse(source.read_text()).body
                if isinstance(node, ast.FunctionDef) and node.name == "import_all")
imports = []
for node in ast.walk(function):
    if isinstance(node, ast.Import):
        imports.extend(alias.name for alias in node.names if alias.name.startswith("renpy."))
native = set(re.findall(r'PyImport_AppendInittab\("([^"]+)', table.read_text()))
with ZipFile(archive) as zipfile:
    packaged = set(zipfile.namelist())
missing = []
for name in dict.fromkeys(imports):
    path = name.replace(".", "/")
    if name not in native and not any(candidate in packaged for candidate in (
        f"{path}.py", f"{path}.pyc", f"{path}/__init__.py",
        f"{path}/__init__.pyc",
    )):
        missing.append(name)
if missing:
    raise SystemExit("Missing import_all modules: " + ", ".join(missing))
print(f"Audited {len(set(imports))} explicit Ren'Py imports: all packaged")
