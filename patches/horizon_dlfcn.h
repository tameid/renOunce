/* Horizon does not provide POSIX dynamic libraries.  Keep ctypes' data
 * types available while making CDLL calls fail with a clear OS error. */
#ifndef RENOUNCE_HORIZON_DLFCN_H
#define RENOUNCE_HORIZON_DLFCN_H

#define RTLD_LAZY 1
#define RTLD_NOW 2
#define RTLD_LOCAL 0
#define RTLD_GLOBAL 0

static inline void *dlopen(const char *name, int flags) {
    (void)name; (void)flags;
    return 0;
}
static inline void *dlsym(void *handle, const char *name) {
    (void)handle; (void)name;
    return 0;
}
static inline int dlclose(void *handle) {
    (void)handle;
    return -1;
}
static inline char *dlerror(void) {
    return "dynamic libraries are unavailable on Horizon";
}

#endif
