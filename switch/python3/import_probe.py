"""Fail-fast hardware import probe using Ren'Py's bootstrap order."""

import traceback
import _otrhlibnx


with open(_otrhlibnx.get_home() + "/Logs/python3-modules.log", "w", encoding="utf-8") as log:
    try:
        for name, action in (
            ("hashlib", lambda: __import__("hashlib")),
            ("random", lambda: __import__("random")),
            ("renpy.bootstrap", lambda: __import__("renpy.bootstrap")),
            ("pygame_sdl2", lambda: __import__("pygame_sdl2")),
            ("pygame alias", lambda: __import__("pygame_sdl2").import_as_pygame()),
            ("_renpy", lambda: __import__("_renpy")),
            ("renpy.import_all", lambda: __import__("renpy").import_all()),
        ):
            log.write(f"START {name}\n")
            log.flush()
            action()
            log.write(f"OK {name}\n")
            log.flush()
    except BaseException:
        traceback.print_exc(file=log)
        log.write("FAIL\n")
        log.flush()
        raise
    log.write("ALL IMPORTS OK\n")
    log.flush()
