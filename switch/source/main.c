#include <switch.h>
#include <Python.h>
#include <errno.h>
#include <netinet/in.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

// Every game gets its own folder under sdmc:/renOunce/ for saves, logs,
// cache and persistent data. The folder id is baked in at build time
// (SWITCH_GAME_ID in switch/CMakeLists.txt) and handed to the Ren'Py
// python layer through the RENOUNCE_HOME environment variable, which
// renpy.patch reads everywhere Ren2Switch used to read the save: device.
#ifndef RENOUNCE_GAME_ID
#define RENOUNCE_GAME_ID "game"
#endif

// Boot diagnostics. Every stage between userAppInit() and the first frame
// Ren'Py draws is logged to sdmc:/renOunce/<id>/boot.log, so a black screen
// on hardware can be told apart from a failure inside Ren'Py itself (which
// writes Logs/log.txt and Logs/traceback.txt instead).
static FILE* boot_log_file = NULL;
static int nxlink_connected = 0;
static char boot_home[512] = "sdmc:/renOunce/" RENOUNCE_GAME_ID;
static char boot_log_path[600] = "sdmc:/renOunce-" RENOUNCE_GAME_ID "-boot.log";

static PadState mouse_pad;
static PadPointer mouse_pointer;
static int mouse_pointer_ready = 0;
static u64 mouse_last_sample = 0;

static PyObject* polljoyconmouse(PyObject* self, PyObject* args)
{
    int width, height;
    if (!PyArg_ParseTuple(args, "ii", &width, &height))
        return NULL;

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

static void boot_log(const char* fmt, ...)
{
    va_list ap;

    if (boot_log_file == NULL)
        return;

    va_start(ap, fmt);
    vfprintf(boot_log_file, fmt, ap);
    va_end(ap);
    fputc('\n', boot_log_file);
    fflush(boot_log_file);

    if (nxlink_connected) {
        va_start(ap, fmt);
        vfprintf(stderr, fmt, ap);
        va_end(ap);
        fputc('\n', stderr);
        fflush(stderr);
    }
}

static PyObject* commitsave(PyObject* self, PyObject* args)
{
    // Saves live on the SD card now, so there is no save: device to commit.
    // The function stays because renpy.patch's bootstrap.py/savelocation.py
    // hooks still call it.
    Py_RETURN_NONE;
}

static PyObject* startboost(PyObject* self, PyObject* args)
{
    appletSetCpuBoostMode(ApmPerformanceMode_Boost);
    return Py_None;
}

static PyObject* disableboost(PyObject* self, PyObject* args)
{
    appletSetCpuBoostMode(ApmPerformanceMode_Normal);
    return Py_None;
}

static PyObject* restartprogram(PyObject* self, PyObject* args)
{
    appletRestartProgram(NULL, 0);
    return Py_None;
}

static PyMethodDef myMethods[] = {
    { "polljoyconmouse", polljoyconmouse, METH_VARARGS, "Read the Switch 2 Joy-Con pointer" },
    { "commitsave", commitsave, METH_NOARGS, "commitsave" },
    { "startboost", startboost, METH_NOARGS, "startboost" },
    { "disableboost", disableboost, METH_NOARGS, "disableboost" },
    { "restartprogram", restartprogram, METH_NOARGS, "restartprogram" },
    { NULL, NULL, 0, NULL }
};

PyMODINIT_FUNC init_otrh_libnx(void)
{
    Py_InitModule("_otrhlibnx", myMethods);
}

PyMODINIT_FUNC initpygame_sdl2_color();
PyMODINIT_FUNC initpygame_sdl2_controller();
PyMODINIT_FUNC initpygame_sdl2_display();
PyMODINIT_FUNC initpygame_sdl2_draw();
PyMODINIT_FUNC initpygame_sdl2_error();
PyMODINIT_FUNC initpygame_sdl2_event();
PyMODINIT_FUNC initpygame_sdl2_font();
PyMODINIT_FUNC initpygame_sdl2_gfxdraw();
PyMODINIT_FUNC initpygame_sdl2_image();
PyMODINIT_FUNC initpygame_sdl2_joystick();
PyMODINIT_FUNC initpygame_sdl2_key();
PyMODINIT_FUNC initpygame_sdl2_locals();
PyMODINIT_FUNC initpygame_sdl2_mixer();
PyMODINIT_FUNC initpygame_sdl2_mixer_music();
PyMODINIT_FUNC initpygame_sdl2_mouse();
PyMODINIT_FUNC initpygame_sdl2_power();
PyMODINIT_FUNC initpygame_sdl2_pygame_time();
PyMODINIT_FUNC initpygame_sdl2_rect();
PyMODINIT_FUNC initpygame_sdl2_render();
PyMODINIT_FUNC initpygame_sdl2_rwobject();
PyMODINIT_FUNC initpygame_sdl2_scrap();
PyMODINIT_FUNC initpygame_sdl2_surface();
PyMODINIT_FUNC initpygame_sdl2_transform();

PyMODINIT_FUNC init_renpy();
PyMODINIT_FUNC init_renpybidi();
PyMODINIT_FUNC initrenpy_audio_renpysound();
PyMODINIT_FUNC initrenpy_display_accelerator();
PyMODINIT_FUNC initrenpy_display_render();
PyMODINIT_FUNC initrenpy_display_matrix();
PyMODINIT_FUNC initrenpy_gl_gl();
PyMODINIT_FUNC initrenpy_gl_gldraw();
PyMODINIT_FUNC initrenpy_gl_glenviron_shader();
PyMODINIT_FUNC initrenpy_gl_glrtt_copy();
PyMODINIT_FUNC initrenpy_gl_glrtt_fbo();
PyMODINIT_FUNC initrenpy_gl_gltexture();
PyMODINIT_FUNC initrenpy_pydict();
PyMODINIT_FUNC initrenpy_style();
PyMODINIT_FUNC initrenpy_styledata_style_activate_functions();
PyMODINIT_FUNC initrenpy_styledata_style_functions();
PyMODINIT_FUNC initrenpy_styledata_style_hover_functions();
PyMODINIT_FUNC initrenpy_styledata_style_idle_functions();
PyMODINIT_FUNC initrenpy_styledata_style_insensitive_functions();
PyMODINIT_FUNC initrenpy_styledata_style_selected_activate_functions();
PyMODINIT_FUNC initrenpy_styledata_style_selected_functions();
PyMODINIT_FUNC initrenpy_styledata_style_selected_hover_functions();
PyMODINIT_FUNC initrenpy_styledata_style_selected_idle_functions();
PyMODINIT_FUNC initrenpy_styledata_style_selected_insensitive_functions();
PyMODINIT_FUNC initrenpy_styledata_styleclass();
PyMODINIT_FUNC initrenpy_styledata_stylesets();
PyMODINIT_FUNC initrenpy_text_ftfont();
PyMODINIT_FUNC initrenpy_text_textsupport();
PyMODINIT_FUNC initrenpy_text_texwrap();

PyMODINIT_FUNC initrenpy_compat_dictviews();
PyMODINIT_FUNC initrenpy_gl2_gl2draw();
PyMODINIT_FUNC initrenpy_gl2_gl2mesh();
PyMODINIT_FUNC initrenpy_gl2_gl2mesh2();
PyMODINIT_FUNC initrenpy_gl2_gl2mesh3();
PyMODINIT_FUNC initrenpy_gl2_gl2model();
PyMODINIT_FUNC initrenpy_gl2_gl2polygon();
PyMODINIT_FUNC initrenpy_gl2_gl2shader();
PyMODINIT_FUNC initrenpy_gl2_gl2texture();
PyMODINIT_FUNC initrenpy_uguu_gl();
PyMODINIT_FUNC initrenpy_uguu_uguu();

PyMODINIT_FUNC initrenpy_lexersupport();
PyMODINIT_FUNC initrenpy_display_quaternion();
PyMODINIT_FUNC initselect(void);

// The Ren2Switch heap override is gone: it predates libounce, which already
// sets the newlib/mimalloc heap to every byte the applet will give us and
// calls _mallocInitialize() right after. Keeping the override meant replacing
// libounce's initialization path with a hand copy of it, before the SD card
// (and therefore any log) exists. Probe NRO on hardware confirmed libounce's
// own path works, so use it.
static Result userapp_romfs_rc = 1;
static Result userapp_socket_rc = 1;


// Create the per-game folder tree on the SD card and export it to Python.
// mkdir() on an existing directory just fails with EEXIST, which is ignored.
static void prepare_renounce_home(void)
{
    char path[512];
    const char* home = "sdmc:/renOunce/" RENOUNCE_GAME_ID;
    int rc_root, rc_home, rc_data, rc_logs, rc_cache;

    rc_root = mkdir("sdmc:/renOunce", 0777);
    rc_home = mkdir(home, 0777);

    snprintf(path, sizeof(path), "%s/boot.log", home);
    boot_log_file = fopen(path, "w");

    if (boot_log_file == NULL)
    {
        // The per-game folder may not be writable yet; keep a copy at the SD
        // card root so a black screen still leaves evidence behind.
        boot_log_file = fopen(boot_log_path, "w");
        if (boot_log_file != NULL)
            boot_log("renOunce boot log (fallback path) for %s", home);
    }

    if (boot_log_file != NULL) {
        boot_log("renOunce boot log for %s", home);
        boot_log("mkdir sdmc:/renOunce: %d (errno %d)", rc_root, errno);
        boot_log("mkdir %s: %d (errno %d)", home, rc_home, errno);
    }

    snprintf(path, sizeof(path), "%s/Data", home);
    rc_data = mkdir(path, 0777);
    snprintf(path, sizeof(path), "%s/Logs", home);
    rc_logs = mkdir(path, 0777);
    snprintf(path, sizeof(path), "%s/cache", home);
    rc_cache = mkdir(path, 0777);

    boot_log("mkdir Data/Logs/cache: %d %d %d (errno %d)",
             rc_data, rc_logs, rc_cache, errno);

    setenv("RENOUNCE_HOME", home, 1);
    strncpy(boot_home, home, sizeof(boot_home) - 1);
    boot_log("RENOUNCE_HOME=%s", home);
}

void userAppInit()
{
    Result rc_romfs, rc_socket;
    u64 mem_available = 0, mem_used = 0;

    prepare_renounce_home();

    svcGetInfo(&mem_available, InfoType_TotalMemorySize, CUR_PROCESS_HANDLE, 0);
    svcGetInfo(&mem_used, InfoType_UsedMemorySize, CUR_PROCESS_HANDLE, 0);
    boot_log("heap: available=%llu used=%llu (libounce default heap)",
             (unsigned long long) mem_available,
             (unsigned long long) mem_used);

    rc_romfs = romfsInit();
    userapp_romfs_rc = rc_romfs;
    boot_log("romfsInit(): 0x%08x", rc_romfs);

    rc_socket = socketInitializeDefault();
    userapp_socket_rc = rc_socket;
    boot_log("socketInitializeDefault(): 0x%08x", rc_socket);
}

void userAppExit()
{
    socketExit();
    romfsExit();
}


ConsoleRenderer* getDefaultConsoleRenderer(void)
{
    return NULL;
}

char python_error_buffer[0x400];


void show_error_and_exit(const char* message)
{
    boot_log("FATAL: %s", message);
    if (boot_log_file != NULL)
        fflush(boot_log_file);

    if (Py_IsInitialized())
        Py_Finalize();

    char* first_line = (char*)message;
    char* end = strchr(message, '\n');
    if (end != NULL)
    {
        first_line = python_error_buffer;
        memcpy(first_line, message, (end - message) > sizeof(python_error_buffer) ? sizeof(python_error_buffer) : (end - message));
        first_line[end - message] = '\0';
    }
    ErrorSystemConfig c;
    errorSystemCreate(&c, (const char*)first_line, message);
    errorSystemShow(&c);
    Py_Exit(1);
}

// Send Python's stdout/stderr (including uncaught tracebacks) to a file, so
// the boot log survives a console that never gets a working display.
static void redirect_python_stdio(void)
{
    char code[2048];

    snprintf(code, sizeof(code),
        "import sys\n"
        "class _RenounceLog(object):\n"
        "    def __init__(self, path, orig):\n"
        "        self.fd = open(path, 'w')\n"
        "        self.orig = orig\n"
        "    def write(self, s):\n"
        "        try:\n"
        "            self.fd.write(s)\n"
        "            self.fd.flush()\n"
        "        except Exception:\n"
        "            pass\n"
        "        try:\n"
        "            self.orig.write(s)\n"
        "            self.orig.flush()\n"
        "        except Exception:\n"
        "            pass\n"
        "    def flush(self):\n"
        "        for f in (self.fd, self.orig):\n"
        "            try:\n"
        "                f.flush()\n"
        "            except Exception:\n"
        "                pass\n"
        "    def isatty(self):\n"
        "        return False\n"
        "_renounce_out = sys.stdout\n"
        "_renounce_err = sys.stderr\n"
        "sys.stdout = _RenounceLog('%s/Logs/stdout.log', _renounce_out)\n"
        "sys.stderr = _RenounceLog('%s/Logs/stderr.log', _renounce_err)\n",
        boot_home, boot_home);

    if (PyRun_SimpleString(code) == -1)
        boot_log("could not redirect Python stdio");
}


static AppletHookCookie applet_hook_cookie;
static void on_applet_hook(AppletHookType hook, void *param)
{
   switch (hook)
   {
      case AppletHookType_OnExitRequest:
        svcSleepThread(1500000000ULL);
        appletUnlockExit();
        break;

      default:
         break;
   }
}



int main(int argc, char* argv[])
{
    setenv("MESA_NO_ERROR", "1", 1);

    // DIAGNOSTIC: appletLockExit() is deliberately not called while boot
    // failures are being chased. It defers HOME/exit, so any hang here leaves
    // the console unable to return to hbmenu without a reboot.
    // appletLockExit();
    // appletHook(&applet_hook_cookie, on_applet_hook, NULL);

    boot_log("main(): entered (romfs=0x%08x socket=0x%08x)",
             userapp_romfs_rc, userapp_socket_rc);

    // nxlinkSetup fills __nxlink_host only for a netloader launch. Keep the
    // normal hbmenu path free of network connection attempts.
    if (__nxlink_host.s_addr != 0) {
        int nxlink_fd = nxlinkStdio();
        nxlink_connected = nxlink_fd >= 0;
        boot_log("nxlinkStdio(): %d", nxlink_fd);
    }

    Py_NoSiteFlag = 1;
    Py_IgnoreEnvironmentFlag = 1;
    Py_NoUserSiteDirectory = 1;
    Py_DontWriteBytecodeFlag = 1;
    Py_OptimizeFlag = 2;

    static struct _inittab builtins[] = {

        {"_otrhlibnx", init_otrh_libnx},
        {"select", initselect},

        {"pygame_sdl2.color", initpygame_sdl2_color},
        {"pygame_sdl2.controller", initpygame_sdl2_controller},
        {"pygame_sdl2.display", initpygame_sdl2_display},
        {"pygame_sdl2.draw", initpygame_sdl2_draw},
        {"pygame_sdl2.error", initpygame_sdl2_error},
        {"pygame_sdl2.event", initpygame_sdl2_event},
        {"pygame_sdl2.font", initpygame_sdl2_font},
        {"pygame_sdl2.gfxdraw", initpygame_sdl2_gfxdraw},
        {"pygame_sdl2.image", initpygame_sdl2_image},
        {"pygame_sdl2.joystick", initpygame_sdl2_joystick},
        {"pygame_sdl2.key", initpygame_sdl2_key},
        {"pygame_sdl2.locals", initpygame_sdl2_locals},
        {"pygame_sdl2.mixer", initpygame_sdl2_mixer},
        {"pygame_sdl2.mixer_music", initpygame_sdl2_mixer_music},
        {"pygame_sdl2.mouse", initpygame_sdl2_mouse},
        {"pygame_sdl2.power", initpygame_sdl2_power},
        {"pygame_sdl2.pygame_time", initpygame_sdl2_pygame_time},
        {"pygame_sdl2.rect", initpygame_sdl2_rect},
        {"pygame_sdl2.render", initpygame_sdl2_render},
        {"pygame_sdl2.rwobject", initpygame_sdl2_rwobject},
        {"pygame_sdl2.scrap", initpygame_sdl2_scrap},
        {"pygame_sdl2.surface", initpygame_sdl2_surface},
        {"pygame_sdl2.transform", initpygame_sdl2_transform},

        {"_renpy", init_renpy},
        {"_renpybidi", init_renpybidi},
        {"renpy.audio.renpysound", initrenpy_audio_renpysound},
        {"renpy.display.accelerator", initrenpy_display_accelerator},
        {"renpy.display.matrix", initrenpy_display_matrix},
        {"renpy.display.render", initrenpy_display_render},
        {"renpy.gl.gldraw", initrenpy_gl_gldraw},
        {"renpy.gl.glenviron_shader", initrenpy_gl_glenviron_shader},
        {"renpy.gl.glrtt_copy", initrenpy_gl_glrtt_copy},
        {"renpy.gl.glrtt_fbo", initrenpy_gl_glrtt_fbo},
        {"renpy.gl.gltexture", initrenpy_gl_gltexture},
        {"renpy.pydict", initrenpy_pydict},
        {"renpy.style", initrenpy_style},
        {"renpy.styledata.style_activate_functions", initrenpy_styledata_style_activate_functions},
        {"renpy.styledata.style_functions", initrenpy_styledata_style_functions},
        {"renpy.styledata.style_hover_functions", initrenpy_styledata_style_hover_functions},
        {"renpy.styledata.style_idle_functions", initrenpy_styledata_style_idle_functions},
        {"renpy.styledata.style_insensitive_functions", initrenpy_styledata_style_insensitive_functions},
        {"renpy.styledata.style_selected_activate_functions", initrenpy_styledata_style_selected_activate_functions},
        {"renpy.styledata.style_selected_functions", initrenpy_styledata_style_selected_functions},
        {"renpy.styledata.style_selected_hover_functions", initrenpy_styledata_style_selected_hover_functions},
        {"renpy.styledata.style_selected_idle_functions", initrenpy_styledata_style_selected_idle_functions},
        {"renpy.styledata.style_selected_insensitive_functions", initrenpy_styledata_style_selected_insensitive_functions},
        {"renpy.styledata.styleclass", initrenpy_styledata_styleclass},
        {"renpy.styledata.stylesets", initrenpy_styledata_stylesets},
        {"renpy.text.ftfont", initrenpy_text_ftfont},
        {"renpy.text.textsupport", initrenpy_text_textsupport},
        {"renpy.text.texwrap", initrenpy_text_texwrap},

        {"renpy.compat.dictviews", initrenpy_compat_dictviews},
        {"renpy.gl2.gl2draw", initrenpy_gl2_gl2draw},
        {"renpy.gl2.gl2mesh", initrenpy_gl2_gl2mesh},
        {"renpy.gl2.gl2mesh2", initrenpy_gl2_gl2mesh2},
        {"renpy.gl2.gl2mesh3", initrenpy_gl2_gl2mesh3},
        {"renpy.gl2.gl2model", initrenpy_gl2_gl2model},
        {"renpy.gl2.gl2polygon", initrenpy_gl2_gl2polygon},
        {"renpy.gl2.gl2shader", initrenpy_gl2_gl2shader},
        {"renpy.gl2.gl2texture", initrenpy_gl2_gl2texture},
        {"renpy.uguu.gl", initrenpy_uguu_gl},
        {"renpy.uguu.uguu", initrenpy_uguu_uguu},
        
        {"renpy.lexersupport", initrenpy_lexersupport},
        {"renpy.display.quaternion", initrenpy_display_quaternion},

        {NULL, NULL}
    };

    FILE* sysconfigdata_file = fopen("romfs:/Contents/lib.zip", "rb");
    FILE* renpy_file = fopen("romfs:/Contents/renpy.py", "rb");
    // Games are installed separately by the companion preparation tool.
    const char* game_dir = "sdmc:/renOunce/game";
    setenv("RENOUNCE_GAME_DIR", game_dir, 1);
    FILE* game_file = fopen("sdmc:/renOunce/game/script.rpy", "rb");
    FILE* game_file_c = fopen("sdmc:/renOunce/game/script.rpyc", "rb");

    boot_log("romfs checks: lib.zip=%p renpy.py=%p game/script.rpy=%p script.rpyc=%p",
             (void*) sysconfigdata_file, (void*) renpy_file,
             (void*) game_file, (void*) game_file_c);

    if (sysconfigdata_file != NULL)
    {
        long sz;
        fseek(sysconfigdata_file, 0, SEEK_END);
        sz = ftell(sysconfigdata_file);
        fseek(sysconfigdata_file, 0, SEEK_SET);
        boot_log("lib.zip size: %ld", sz);
    }

    if (game_file != NULL)
        fclose(game_file);
    if (game_file_c != NULL)
        fclose(game_file_c);

    if (sysconfigdata_file == NULL)
    {
        show_error_and_exit("Could not find lib.zip.\n\nPlease ensure that the romfs was built correctly: the \"lib.zip\" file must be at romfs:/Contents/lib.zip, next to the .nro.");
    }

    if (renpy_file == NULL)
    {
        show_error_and_exit("Could not find renpy.py.\n\nPlease ensure that the romfs was built correctly: the \"renpy.py\" file must be at romfs:/Contents/renpy.py, next to the .nro.");
    }

    fclose(sysconfigdata_file);

    // Set Python's home before initialization, then replace sys.path below.
    static char python_home[] = "romfs:/Contents/lib.zip";
    Py_SetPythonHome(python_home);

    // CPython reads the built-in module table during initialization.
    int inittab_result = PyImport_ExtendInittab(builtins);
    boot_log("PyImport_ExtendInittab(): %d", inittab_result);
    boot_log("Py_InitializeEx(): starting");
    Py_InitializeEx(0);
    boot_log("Py_InitializeEx(): done, initialized=%d", Py_IsInitialized());

    if (PyErr_Occurred())
    {
        boot_log("Py_InitializeEx left an exception pending");
        PyErr_Print();
    }

    redirect_python_stdio();

    char* pyargs[] = {
        "romfs:/Contents/renpy.py",
        NULL,
    };

    PySys_SetArgvEx(1, pyargs, 1);

    int python_result;

    // The archive has two roots: Python's stdlib is under python2.7/ while
    // Ren'Py lives at the archive root. zipimport accepts a subdirectory
    // after the .zip filename as a separate sys.path entry.
    python_result = PyRun_SimpleString(
        "import sys\n"
        "sys.path = ['romfs:/Contents/lib.zip/python2.7', "
        "'romfs:/Contents/lib.zip']");
    boot_log("set sys.path: %d", python_result);

    if (python_result == -1)
    {
        show_error_and_exit("Could not set the Python path.\n\nThis is an internal error and should not occur during normal usage.");
    }

#define x(lib) \
    { \
        if (PyRun_SimpleString("import " lib) == -1) \
        { \
            boot_log("import " lib " failed"); \
            PyErr_Print(); \
            show_error_and_exit("Could not import python library " lib ".\n\nPlease ensure that the romfs was built correctly: \"lib.zip\" must contain the folder \"python2.7\". \nInside that folder, the file \"" lib ".py\" or folder \"" lib "\" needs to exist."); \
        } \
        else \
        { \
            boot_log("import " lib ": ok"); \
        } \
    }

    x("os");
    x("pygame_sdl2");
    x("encodings");
    x("select");
    x("subprocess");
    x("builtins");

#undef x

    boot_log("running romfs:/Contents/renpy.py");
    python_result = PyRun_SimpleFileEx(renpy_file, "romfs:/Contents/renpy.py", 1);
    boot_log("renpy.py returned: %d", python_result);

    if (python_result == -1)
    {
        PyErr_Print();
        show_error_and_exit("An uncaught Python exception occurred during renpy.py execution.\n\nPlease look in the sdmc:/renOunce/" RENOUNCE_GAME_ID "/Logs/ folder for more information about this exception.");
    }

    Py_Exit(0);
    return 0;
}
