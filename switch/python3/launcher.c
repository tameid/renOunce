/* Python 3 bootstrap probe for a future Ren'Py 8 Switch 2 runtime.
 * Kept separate from the Python 2.7 launcher to avoid mixing ABIs.
 */
#include <Python.h>
#include <switch.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/stat.h>

#ifdef RENOUNCE_LINK_EXTENSIONS
int register_renpy_modules(void);
#endif
static int temporary_storage_mounted = 0;
#ifndef RENOUNCE_GAME_ID
#define RENOUNCE_GAME_ID "renpy-8.4.1-engine"
#endif
static char renounce_home[1024];
static char renounce_logs[1100];

static int make_directory(const char *path)
{
    struct stat info;
    if (mkdir(path, 0777) == 0) return 0;
    return errno == EEXIST && stat(path, &info) == 0 && S_ISDIR(info.st_mode) ? 0 : -1;
}

static int prepare_home(int argc, char **argv)
{
    char base[1024], folder[1024];
    const char *slash;
    size_t length;
    if (argc < 1 || !argv || !argv[0] || strncmp(argv[0], "sdmc:/", 6) != 0)
        return -1;
    slash = strrchr(argv[0], '/');
    if (!slash || slash <= argv[0] + 5 || !slash[1]) return -1;
    length = (size_t)(slash - argv[0]);
    if (length >= sizeof(base)) return -1;
    memcpy(base, argv[0], length);
    base[length] = 0;
    if (snprintf(folder, sizeof(folder), "%s/renounce", base) >= (int)sizeof(folder) ||
        snprintf(renounce_home, sizeof(renounce_home), "%s/%s", folder,
                 RENOUNCE_GAME_ID) >= (int)sizeof(renounce_home) ||
        snprintf(renounce_logs, sizeof(renounce_logs), "%s/Logs", renounce_home) >=
            (int)sizeof(renounce_logs)) return -1;
    return make_directory(folder) || make_directory(renounce_home) ||
           make_directory(renounce_logs) ? -1 : 0;
}
static PadState mouse_pad;
static PadPointer mouse_pointer;
static int mouse_pointer_ready = 0;
static u64 mouse_last_sample = 0;

static PyObject *get_home(PyObject *self, PyObject *args)
{
    return PyUnicode_FromString(renounce_home);
}

static PyObject *polljoyconmouse(PyObject *self, PyObject *args)
{
    int width, height;
    if (!PyArg_ParseTuple(args, "ii", &width, &height)) return NULL;

    if (!mouse_pointer_ready) {
        if (width <= 0 || height <= 0 ||
            R_FAILED(padPointerInitialize(&mouse_pointer, width, height)))
            return Py_BuildValue("(iiiiiii)", 0, 0, 0, 0, 0, 0, 0);
        padInitializeDefault(&mouse_pad);
        mouse_pointer_ready = 1;
    }

    int tracking = 0;
    padUpdate(&mouse_pad);
    padPointerUpdate(&mouse_pointer, &mouse_pad);
    if (mouse_pointer.active) {
        HidNmouseState state;
        size_t count = 0;
        if (R_SUCCEEDED(hidGetNmouseStates(mouse_pointer.current, &state, 1, &count)) &&
            count != 0 && state.sampling_number != mouse_last_sample) {
            mouse_last_sample = state.sampling_number;
            tracking = (state.flags & BIT(1)) != 0;
        }
    } else {
        mouse_last_sample = 0;
    }

    return Py_BuildValue("(iiiiiii)", mouse_pointer.active,
                         mouse_pointer.x, mouse_pointer.y,
                         mouse_pointer.buttons_cur,
                         mouse_pointer.wheel_delta_y, tracking,
                         mouse_pointer.delta_x != 0 || mouse_pointer.delta_y != 0);
}

static PyObject *commitsave(PyObject *self, PyObject *args)
{
    Py_RETURN_NONE;
}

static PyObject *startboost(PyObject *self, PyObject *args)
{
    appletSetCpuBoostMode(ApmPerformanceMode_Boost);
    Py_RETURN_NONE;
}

static PyObject *disableboost(PyObject *self, PyObject *args)
{
    appletSetCpuBoostMode(ApmPerformanceMode_Normal);
    Py_RETURN_NONE;
}

static PyObject *restartprogram(PyObject *self, PyObject *args)
{
    appletRestartProgram(NULL, 0);
    Py_RETURN_NONE;
}

static PyObject *temporary_storage_available(PyObject *self, PyObject *args)
{
    if (temporary_storage_mounted) Py_RETURN_TRUE;
    Py_RETURN_FALSE;
}

static PyMethodDef methods[] = {
    {"commitsave", commitsave, METH_NOARGS, NULL},
    {"startboost", startboost, METH_NOARGS, NULL},
    {"disableboost", disableboost, METH_NOARGS, NULL},
    {"restartprogram", restartprogram, METH_NOARGS, NULL},
    {"temporary_storage_available", temporary_storage_available, METH_NOARGS, NULL},
    {"get_home", get_home, METH_NOARGS, NULL},
    {"polljoyconmouse", polljoyconmouse, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT, "_otrhlibnx", NULL, -1, methods,
    NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC PyInit__otrhlibnx(void)
{
    return PyModule_Create(&module);
}

#ifdef RENOUNCE_RELEASE
#define boot_stage(log, stage, value) ((void)0)
#else
static void boot_stage(FILE *log, const char *stage, int value)
{
    if (log) {
        fprintf(log, "%s: %d\n", stage, value);
        fflush(log);
    }
}
#endif

int main(int argc, char **argv)
{
    int result;
#ifndef RENOUNCE_RELEASE
    char path[1200];
#endif
    if (prepare_home(argc, argv) != 0) {
        fprintf(stderr, "Cannot create renounce beside NRO: %s\n",
                argc > 0 && argv && argv[0] ? argv[0] : "(missing path)");
        return 1;
    }
    FILE *boot_log = NULL;
#ifndef RENOUNCE_RELEASE
    snprintf(path, sizeof(path), "%s/python3-boot.log", renounce_logs);
    boot_log = fopen(path, "w");
#endif
    boot_stage(boot_log, "main entered", 0);
    Result rc = romfsInit();
    boot_stage(boot_log, "romfsInit", (int)rc);
    if (R_FAILED(rc)) {
        if (boot_log) fclose(boot_log);
        return 1;
    }
    Result temp_rc = fsdevMountTemporaryStorage("tmp");
    temporary_storage_mounted = R_SUCCEEDED(temp_rc);
    boot_stage(boot_log, "temporary storage mount", (int)temp_rc);
#ifndef RENOUNCE_RELEASE
    FILE *stdlib = fopen("romfs:/Contents/lib.zip", "rb");
    boot_stage(boot_log, "stdlib zip opened", stdlib != NULL);
    if (stdlib) fclose(stdlib);
    snprintf(path, sizeof(path), "%s/python3-import.log", renounce_logs);
    if (freopen(path, "w", stderr)) {
        boot_stage(boot_log, "Python stderr redirected", 0);
    }
#endif
    if (PyImport_AppendInittab("_otrhlibnx", PyInit__otrhlibnx) < 0) {
        boot_stage(boot_log, "AppendInittab failed", -1);
        if (boot_log) fclose(boot_log);
        if (temporary_storage_mounted) fsdevUnmountDevice("tmp");
        return 1;
    }
#ifdef RENOUNCE_LINK_EXTENSIONS
    if (register_renpy_modules() < 0) {
        boot_stage(boot_log, "extension registration failed", -1);
        if (boot_log) fclose(boot_log);
        if (temporary_storage_mounted) fsdevUnmountDevice("tmp");
        return 1;
    }
    boot_stage(boot_log, "extensions registered", 0);
#endif

    /* Python 3 uses wide strings and isolated configuration. */
    PyConfig config;
    PyConfig_InitIsolatedConfig(&config);
    config.write_bytecode = 0;
    config.site_import = 0;
    config.parse_argv = 0;
    config.verbose = 0;
#ifndef RENOUNCE_RELEASE
    config.verbose = 1;
#endif
    PyStatus status = PyConfig_SetString(&config, &config.program_name,
                                          L"renounce-python3");
    if (!PyStatus_Exception(status))
        status = PyConfig_SetString(&config, &config.home,
                                    L"romfs:/Contents");
    if (!PyStatus_Exception(status)) {
        config.module_search_paths_set = 1;
        status = PyWideStringList_Append(&config.module_search_paths,
                                          L"romfs:/Contents/lib.zip");
    }
    if (!PyStatus_Exception(status))
        status = Py_InitializeFromConfig(&config);
    PyConfig_Clear(&config);
    if (PyStatus_Exception(status)) {
        fprintf(stderr, "Py_InitializeFromConfig failed: %s\n",
                status.err_msg ? status.err_msg : "unknown error");
        if (boot_log) {
            fprintf(boot_log, "Py_InitializeFromConfig failed: %s\n",
                    status.err_msg ? status.err_msg : "unknown error");
            fflush(boot_log);
            fclose(boot_log);
        }
        romfsExit();
        if (temporary_storage_mounted) fsdevUnmountDevice("tmp");
        return 1;
    }
    boot_stage(boot_log, "Python initialized", 0);

    /* Hardware smoke test is excluded from distribution builds. */
#ifndef RENOUNCE_RELEASE
    result = PyRun_SimpleString(
        "import sys, encodings, _otrhlibnx\n"
        "with open(_otrhlibnx.get_home() + '/Logs/python3-probe.txt', 'w') as f:\n"
        "    f.write(sys.version + '\\n')\n"
        "    f.write('imports ok\\n')\n");
    if (result != 0) PyErr_Print();
    boot_stage(boot_log, "Python smoke test", result);
#else
    result = 0;
#endif
    if (result == 0) {
#ifdef RENOUNCE_ENGINE_BOOT
        int module_result = PyRun_SimpleString("import renounce_engine_boot\n");
        if (module_result != 0) PyErr_Print();
        boot_stage(boot_log, "Ren'Py engine boot", module_result);
#else
        int module_result = PyRun_SimpleString("import renounce_import_probe\n");
        if (module_result != 0) PyErr_Print();
        boot_stage(boot_log, "Ren'Py module import probe", module_result);
#endif
        if (module_result != 0) result = module_result;
    }
    if (Py_FinalizeEx() < 0) result = 1;
    boot_stage(boot_log, "Python finalized", result);
    if (boot_log) fclose(boot_log);
    if (temporary_storage_mounted) fsdevUnmountDevice("tmp");
    romfsExit();
    return result != 0;
}
