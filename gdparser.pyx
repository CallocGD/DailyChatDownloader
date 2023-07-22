#cython:language_level = 3
#distutils: sources = yyjson/yyjson.c
cimport cython
from cython.parallel cimport prange

from libc.stdlib cimport free
from libc.string cimport memcpy

from cpython.buffer cimport (
    Py_buffer, 
    PyObject_GetBuffer,
    PyBuffer_Release,
    PyBUF_SIMPLE
)

from cpython.mem cimport PyMem_Free

from cpython.bytes cimport PyBytes_FromStringAndSize


DEF parser_size = 2048

cdef extern from "Python.h":
    void *PyMem_Calloc(size_t nelem, size_t elsize)




cdef extern from "b64.h":
    
    struct buffer_s:
        size_t len
        char* buf
    ctypedef buffer_s buffer_t

    struct gd_node_s:
        size_t pos # The string's current position on the parsing phase...
        buffer_t* buf # An arrary of 30 buffers to use 
        char* raw # the raw robtop string to parse through
    ctypedef gd_node_s gd_node_t

    int give_memory(buffer_t* buff) nogil
    void reset_memory(buffer_t* buffer) nogil 
    void free_memory(buffer_t* buff) nogil 
    int parse_next(gd_node_t* node)
    bytes from_buffer(buffer_t* buff)
    Py_ssize_t fast_atoi(buffer_t * buff)
    Py_ssize_t fast_ternary(buffer_t * buff)
    bint fast_boolean(buffer_t* buff) with gil 
    bytes b64decode(buffer_t* buffer)
    bytes Write_Json(buffer_t* buff)
    


    # This will do multipurpose decoing on both url-safe and not so it's a win-win
    

cdef class GDComment:
    cdef:
        buffer_t* buf

    @property
    def body(self):
        return b64decode(&self.buf[2])

    @property
    def raw_comment(self):
        return from_buffer(&self.buf[2])
    
    @property
    def authorPlayerID(self):
        return from_buffer(&self.buf[3])
    
    @property
    def likes(self):
        return fast_atoi(&self.buf[4])

    @property
    def dislikes(self):
        return fast_ternary(&self.buf[5])
    
    @property
    def messageID(self):
        return from_buffer(&self.buf[6])

    @property
    def spam(self):
        return fast_boolean(&self.buf[7])
    
    @property
    def authorAccountID(self):
        return from_buffer(&self.buf[29])

    @property
    def age(self):
        return from_buffer(&self.buf[9])
    
    @property
    def percent(self):
        return fast_ternary(&self.buf[10])
    
    @property
    def modBadge(self):
        return fast_ternary(&self.buf[11])
    
    @property
    def moderatorChatColor(self):
        if self.modBadge > 0:
            return from_buffer(&self.buf[12])
    
    @property
    def author(self):
        return from_buffer(&self.buf[14])

    @property
    def icon(self):
        return fast_atoi(&self.buf[22])

    @property
    def playerColor(self):
        return fast_atoi(&self.buf[23])

    @property
    def playerColor2(self):
        return fast_atoi(&self.buf[24])

    @property
    def icontype(self):
        return fast_atoi(&self.buf[27])

    @property
    def glow(self):
        return fast_atoi(&self.buf[28])
    

    # def __dealloc__(self):
    #     PyMem_Free(self.buf)
    
    @property
    def as_json(self):
        return Write_Json(self.buf)
    
    


cdef class GDParser:
    cdef:
        Py_buffer py_buf
        gd_node_t node 
        int flag 

    def __init__(self, object b):
        PyObject_GetBuffer(b, &self.py_buf, PyBUF_SIMPLE)
        (&self.node).raw = <char*>self.py_buf.buf
        self.node.pos = 0
        self.node.buf = <buffer_t*>PyMem_Calloc(30, sizeof(buffer_t))
        self.give_mem()
        self.flag = 0

    def __dealloc__(self):
        self.free_mem()
        PyMem_Free(self.node.buf)
        PyBuffer_Release(&self.py_buf)

    # used with nogil for quick memeory management 
    cdef void give_mem(self):
        cdef int i , j = 0
        cdef gd_node_t node = self.node
        for i in prange(30, nogil=True):
            j = give_memory(&node.buf[i])
            if j == -1:
                with gil:
                    raise MemoryError()
        # Set object after use...
        self.node = node

        # Clean memory before use...
        self.reset_mem()

    cdef void reset_mem(self):
        cdef int i 
        cdef gd_node_t node = self.node
        for i in prange(30, nogil=True):
            reset_memory(&node.buf[i])
        # Set object after use...
        self.node = node
    
    cdef void free_mem(self):
        cdef int i 
        cdef gd_node_t node = self.node
        for i in prange(30, nogil=True):
            free_memory(&node.buf[i])
        # Set object after use...
        self.node = node

    def parse_comment(self):
        if self.flag == -1:
            return None 
        self.flag = parse_next(&self.node)
        cdef GDComment comment = GDComment.__new__(GDComment)
        comment.buf = self.node.buf
        return comment 
    
    def debug_position(self):
        return "Debug pos: <%i>" % self.node.pos 


    def __iter__(self):
        cdef GDComment comment
        while self.flag != -1:
            self.flag = parse_next(&self.node)
            comment = <GDComment>GDComment.__new__(GDComment)
            comment.buf = self.node.buf
            yield comment 
    
    def range(self,Py_ssize_t i):
        for _ in range(i):
            self.flag = parse_next(&self.node)
            comment = <GDComment>GDComment.__new__(GDComment)
            comment.buf = self.node.buf
            yield comment

    


