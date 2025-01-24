#define PY_SSIZE_T_CLEAN
#include "Python.h"
#include "quicklz.h"

static PyObject* py_quicklz_compress(PyObject* self, PyObject* args) {
    const char* input;
    Py_ssize_t input_size;

    if (!PyArg_ParseTuple(args, "s#", &input, &input_size))
        return NULL;
    
    // Allocate scratch buffer for compression
    char *scratch_compress = (char *)malloc(QLZ_SCRATCH_COMPRESS);
    if (!scratch_compress) {
        PyErr_NoMemory();
        return NULL;
    }

    // Allocate output buffer - worst case is input size + 400 bytes
    char* compressed = (char*)malloc(input_size + 400);
    if (!compressed) {
        free(scratch_compress);
        PyErr_NoMemory();
        return NULL;
    }

    // Perform compression
    size_t compressed_size = qlz_compress(input, compressed, input_size, scratch_compress);

    // Build return value
    PyObject* result = Py_BuildValue("y#", compressed, compressed_size);
    
    // Clean up
    free(compressed);
    free(scratch_compress);
    
    return result;
}

static PyObject* py_quicklz_decompress(PyObject* self, PyObject* args) {
    const char* input;
    Py_ssize_t input_size;

    if (!PyArg_ParseTuple(args, "s#", &input, &input_size))
        return NULL;

    // Allocate scratch buffer for decompression
    char *scratch_decompress = (char *)malloc(QLZ_SCRATCH_DECOMPRESS);
    if (!scratch_decompress) {
        PyErr_NoMemory();
        return NULL;
    }

    // Get the size of the decompressed data from the compressed header
    size_t decompressed_size = qlz_size_decompressed(input);
    
    // Allocate output buffer
    char* decompressed = (char*)malloc(decompressed_size);
    if (!decompressed) {
        free(scratch_decompress);
        PyErr_NoMemory();
        return NULL;
    }

    // Perform decompression
    qlz_decompress(input, decompressed, scratch_decompress);

    // Build return value
    PyObject* result = Py_BuildValue("y#", decompressed, decompressed_size);
    
    // Clean up
    free(decompressed);
    free(scratch_decompress);
    
    return result;
}

static PyMethodDef QuicklzMethods[] = {
    {"compress", py_quicklz_compress, METH_VARARGS, "Compress data using QuickLZ."},
    {"decompress", py_quicklz_decompress, METH_VARARGS, "Decompress data using QuickLZ."},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef quicklzmodule = {
    PyModuleDef_HEAD_INIT,
    "quicklz",
    NULL,
    -1,
    QuicklzMethods
};

PyMODINIT_FUNC PyInit_quicklz(void) {
    return PyModule_Create(&quicklzmodule);
}