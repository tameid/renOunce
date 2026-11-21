#!/usr/bin/env python3
"""Cross-compile CPython 2.7.18 as a static Switch 2 archive.

Usage inside the build container:
    python3 switch/python27/build.py --source build-python27/Python-2.7.18

The installed Switch Python headers currently supply pyconfig.h. No object
files from the installed libpython archive are used.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys

here = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, default=Path('build-python27/source-build'))
args = parser.parse_args()
source = args.source.resolve()
output = args.output.resolve()
objects = output / 'objects'
patched = output / 'patched'
objects.mkdir(parents=True, exist_ok=True)
patched.mkdir(parents=True, exist_ok=True)

def replace_once(data, old, new):
    if data.count(old) != 1:
        raise RuntimeError('expected one occurrence of ' + old[:50])
    return data.replace(old, new)

posix = (source / 'Modules/posixmodule.c').read_text()
posix = replace_once(posix, '#endif /* ! __IBMC__ */', '''#endif /* ! __IBMC__ */
#ifdef __SWITCH2__
#undef HAVE_CHROOT
#undef HAVE_EXECV
#undef HAVE_FCHDIR
#undef HAVE_FDATASYNC
#undef HAVE_GETPPID
#undef HAVE_PIPE
#undef HAVE_POPEN
#undef HAVE_SETGROUPS
#undef HAVE_TTYNAME
#endif
''')
posix = replace_once(posix, '    i = (int)umask(i);', '''#ifdef __SWITCH2__
    i = 0; /* SD files have no POSIX permission mask. */
#else
    i = (int)umask(i);
#endif''')
posix = replace_once(posix, 'static PyMethodDef posix_methods[] = {', '''#ifdef __SWITCH2__
static PyObject *switch_waitpid(PyObject *self, PyObject *args)
{
    errno = ENOSYS;
    return PyErr_SetFromErrno(PyExc_OSError);
}
#endif

static PyMethodDef posix_methods[] = {''')
posix = replace_once(posix,
    '    {"umask",           posix_umask, METH_VARARGS, posix_umask__doc__},',
    '''    {"umask",           posix_umask, METH_VARARGS, posix_umask__doc__},
#ifdef __SWITCH2__
    {"waitpid",         switch_waitpid, METH_VARARGS,
     "Unavailable on Switch 2 (no child processes)."},
#endif''')
(patched / 'posixmodule.c').write_text(posix)

# Switch has no /dev/urandom. Use the system cryptographic RNG for both
# os.urandom() and CPython's optional randomized hash seed.
random = (source / 'Python/random.c').read_text()
random = replace_once(random, '#include "Python.h"', '''#include "Python.h"
#ifdef __SWITCH2__
#include <switch.h>

static int switch2_urandom(void *buffer, Py_ssize_t size, int raise)
{
    static int initialized = 0;
    Result rc;

    if (!initialized) {
        rc = csrngInitialize();
        if (R_FAILED(rc)) goto error;
        initialized = 1;
    }
    rc = csrngGetRandomBytes(buffer, (size_t)size);
    if (R_FAILED(rc)) goto error;
    return 0;

error:
    if (raise)
        PyErr_Format(PyExc_OSError, "Switch 2 RNG failed: 0x%08x", rc);
    else
        Py_FatalError("Switch 2 RNG failed during Python initialization");
    return -1;
}
#endif''')
random = replace_once(random, '''#ifdef MS_WINDOWS
    return win32_urandom((unsigned char *)buffer, size, 1);''', '''#ifdef __SWITCH2__
    return switch2_urandom(buffer, size, 1);
#elif defined(MS_WINDOWS)
    return win32_urandom((unsigned char *)buffer, size, 1);''')
random = replace_once(random, '''#ifdef MS_WINDOWS
        (void)win32_urandom((unsigned char *)secret, secret_size, 0);''', '''#ifdef __SWITCH2__
        (void)switch2_urandom(secret, secret_size, 0);
#elif defined(MS_WINDOWS)
        (void)win32_urandom((unsigned char *)secret, secret_size, 0);''')
(patched / 'random.c').write_text(random)

hotshot = (source / 'Modules/_hotshot.c').read_text()
hotshot = replace_once(hotshot,
    '#if defined(MS_WINDOWS) || defined(PYOS_OS2) || \\\n',
    '#if defined(__SWITCH2__) || defined(MS_WINDOWS) || defined(PYOS_OS2) || \\\n')
(patched / '_hotshot.c').write_text(hotshot)

# CPython 2.7 normally searches built-ins only at the top level. Ren'Py and
# pygame_sdl2 register statically linked extensions with dotted names.
imp = (source / 'Python/import.c').read_text()
imp = replace_once(imp, '''    if (path == NULL) {
        if (is_builtin(name)) {''', '''    if (path != NULL && fullname != NULL && is_builtin(fullname)) {
        if (strlen(fullname) >= buflen) {
            PyErr_SetString(PyExc_OverflowError, "module name is too long");
            goto error_exit;
        }
        strcpy(buf, fullname);
        PyMem_FREE(name);
        return &fd_builtin;
    }
    if (path == NULL) {
        if (is_builtin(name)) {''')
(patched / 'import.c').write_text(imp)

modules = (here / 'modules.txt').read_text().splitlines()
config = (source / 'Modules/config.c.in').read_text()
declarations = '\n'.join('extern void %s(void);' % name for name in modules)
entries = '\n'.join('    {"%s", %s},' % (name[4:], name) for name in modules)
config = replace_once(config, '/* -- ADDMODULE MARKER 1 -- */', declarations)
config = replace_once(config, '/* -- ADDMODULE MARKER 2 -- */', entries)
(patched / 'config.c').write_text(config)

names = (here / 'objects.txt').read_text().splitlines() + ['config.o']
compiler = '/opt/devkitpro/devkitA64/bin/aarch64-none-elf-gcc'
flags = [
    '-O2', '-fPIC', '-ffunction-sections', '-fdata-sections',
    '-D__SWITCH__', '-D__SWITCH2__', '-D_REENTRANT',
    '-DPREFIX="/opt/devkitpro/portlibs/switch2"',
    '-DEXEC_PREFIX="/opt/devkitpro/portlibs/switch2"',
    '-DPYTHONPATH=""', '-DVERSION="2.7"', '-DVPATH=""',
    '-DPLATFORM="horizon"',
    '-Dtimezone=_timezone', '-Ddaylight=_daylight', '-DMAX_GROUPS=64',
    '-I' + str(source / 'Include'),
    '-I' + str(source / 'Modules'),
    '-I' + str(source / 'Python'),
    '-I/opt/devkitpro/portlibs/switch/include/python2.7',
    '-I/opt/devkitpro/libounce/include',
    '-I/opt/devkitpro/portlibs/switch/include',
]

def compile_one(name):
    override = patched / (name[:-2] + '.c')
    matches = list(source.rglob(name[:-2] + '.c')) if not override.exists() else []
    if not override.exists() and len(matches) != 1:
        return name, 'expected one source, found %d' % len(matches)
    src = override if override.exists() else matches[0]
    result = subprocess.run([compiler, *flags, '-c', str(src),
                             '-o', str(objects / name)], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return name, result.stdout if result.returncode else ''

with ThreadPoolExecutor(max_workers=8) as pool:
    errors = [(name, msg) for name, msg in pool.map(compile_one, names) if msg]
for name, message in errors:
    print('FAILED', name, message[-2000:])
if errors:
    sys.exit(1)

archive = output / 'libpython2.7-switch2.a'
subprocess.run(['ar', 'rcs', str(archive),
                *(str(objects / name) for name in names)], check=True)
print('Compiled %d CPython objects: %s' % (len(names), archive))
