"""Start the bundled Ren'Py 8.4.1 engine from RomFS."""

import os
import shutil
import sys
import tempfile
import _otrhlibnx

home = _otrhlibnx.get_home()
for directory in (home, home + "/Data", home + "/Logs", home + "/cache"):
    os.makedirs(directory, exist_ok=True)
os.environ["RENOUNCE_HOME"] = home
os.environ["RENPY_MULTIPERSISTENT"] = home + "/MultiPersistent"
sd_temp_dir = home + "/tmp"
shutil.rmtree(sd_temp_dir, ignore_errors=True)
os.makedirs(sd_temp_dir, exist_ok=True)

temp_dir = None
candidates = []
if _otrhlibnx.temporary_storage_available():
    candidates.append("tmp:/")
candidates.append(sd_temp_dir)
for candidate in candidates:
    try:
        if candidate.startswith("sdmc:"):
            os.makedirs(candidate, exist_ok=True)
        probe = candidate.rstrip("/") + "/.write-test"
        with open(probe, "wb") as test_file:
            test_file.write(b"ok")
        os.unlink(probe)
    except OSError:
        continue
    temp_dir = candidate
    break
if temp_dir is None:
    raise OSError("No writable temporary storage on Switch 2")
tempfile.tempdir = temp_dir

import renpy
import renpy_launcher
import renpy.bootstrap


def path_to_logdir(basedir):
    """Keep runtime logs writable while the bundled engine stays in RomFS."""
    return home + "/Logs"


sys.argv = ["renpy", "--savedir", home + "/Data"]
renpy.__main__ = renpy_launcher
renpy_launcher.path_to_logdir = path_to_logdir
renpy_launcher.path_to_saves = lambda gamedir, save_directory=None: home + "/Data"

try:
    renpy.bootstrap.bootstrap("romfs:/Contents")
finally:
    shutil.rmtree(sd_temp_dir, ignore_errors=True)
