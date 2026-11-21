// Python 2.7 select module for the static Switch build. The devkit's
// libpython2.7.a omits CPython's selectmodule.o, while subprocess imports it.
#include <Python.h>
#include <errno.h>
#include <sys/select.h>

static PyObject *select_error;

static int add_descriptors(PyObject *items, fd_set *fds, int *maxfd)
{
    Py_ssize_t i, count = PySequence_Fast_GET_SIZE(items);
    for (i = 0; i < count; ++i) {
        PyObject *item = PySequence_Fast_GET_ITEM(items, i);
        int fd = PyObject_AsFileDescriptor(item);
        if (fd < 0)
            return -1;
        if (fd >= FD_SETSIZE) {
            PyErr_SetString(PyExc_ValueError, "file descriptor exceeds FD_SETSIZE");
            return -1;
        }
        FD_SET(fd, fds);
        if (fd > *maxfd)
            *maxfd = fd;
    }
    return 0;
}

static PyObject *ready_descriptors(PyObject *items, const fd_set *fds)
{
    PyObject *result = PyList_New(0);
    Py_ssize_t i, count = PySequence_Fast_GET_SIZE(items);
    if (!result)
        return NULL;
    for (i = 0; i < count; ++i) {
        PyObject *item = PySequence_Fast_GET_ITEM(items, i);
        int fd = PyObject_AsFileDescriptor(item);
        if (fd < 0 || (FD_ISSET(fd, fds) && PyList_Append(result, item) < 0)) {
            Py_DECREF(result);
            return NULL;
        }
    }
    return result;
}

static PyObject *py_select(PyObject *self, PyObject *args)
{
    PyObject *inputs[3], *items[3] = {NULL, NULL, NULL};
    PyObject *timeout = Py_None, *result = NULL, *ready[3] = {NULL, NULL, NULL};
    fd_set fds[3];
    struct timeval tv, *tvp = NULL;
    int maxfd = -1, rc, i;

    if (!PyArg_ParseTuple(args, "OOO|O:select", &inputs[0], &inputs[1],
                          &inputs[2], &timeout))
        return NULL;

    for (i = 0; i < 3; ++i) {
        FD_ZERO(&fds[i]);
        items[i] = PySequence_Fast(inputs[i], "select() arguments must be iterable");
        if (!items[i] || add_descriptors(items[i], &fds[i], &maxfd) < 0)
            goto done;
    }

    if (timeout != Py_None) {
        double seconds = PyFloat_AsDouble(timeout);
        if (PyErr_Occurred())
            goto done;
        if (seconds < 0) {
            PyErr_SetString(PyExc_ValueError, "timeout must be non-negative");
            goto done;
        }
        tv.tv_sec = (long) seconds;
        tv.tv_usec = (long) ((seconds - tv.tv_sec) * 1000000.0);
        tvp = &tv;
    }

    Py_BEGIN_ALLOW_THREADS
    rc = select(maxfd + 1, &fds[0], &fds[1], &fds[2], tvp);
    Py_END_ALLOW_THREADS
    if (rc < 0) {
        PyErr_SetFromErrno(select_error);
        goto done;
    }

    for (i = 0; i < 3; ++i) {
        ready[i] = ready_descriptors(items[i], &fds[i]);
        if (!ready[i])
            goto done;
    }
    result = PyTuple_Pack(3, ready[0], ready[1], ready[2]);

done:
    for (i = 0; i < 3; ++i) {
        Py_XDECREF(items[i]);
        Py_XDECREF(ready[i]);
    }
    return result;
}

static PyMethodDef select_methods[] = {
    {"select", py_select, METH_VARARGS, "Wait for file descriptors to be ready."},
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC initselect(void)
{
    PyObject *module = Py_InitModule("select", select_methods);
    if (!module)
        return;
    select_error = PyErr_NewException("select.error", PyExc_IOError, NULL);
    if (!select_error)
        return;
    Py_INCREF(select_error);
    PyModule_AddObject(module, "error", select_error);
}
