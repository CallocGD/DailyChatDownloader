#ifndef _b64_h
#define _b64_h
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <Python.h>
#include "gdnode.h"

// typedef struct buffer_s {
//     size_t len;
//     char* buf;
// } buffer_t;

/* Base 64 library inspired by Polfosol */


static const int B64index[256] =
{
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 62, 0, 0,
    52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 0, 0, 0, 
    0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 
    12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 
    25, 0, 0, 0, 0, 63, 0, 26, 27, 28, 29, 30, 31, 32, 33, 
    34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 
    48, 49, 50, 51
};


PyObject *b64decode(buffer_t* buffer){
    const unsigned char* p = (const unsigned char*)buffer->buf;
    size_t pad1 = buffer->len % 4 || p[buffer->len - 1] == '=';
    size_t pad2 = pad1 && (buffer->len % 4 > 2 || p[buffer->len - 2] != '=');
    size_t j = 0;
    const size_t last = (buffer->len - pad1) / 4 << 2;

    
    PyObject* result = PyBytes_FromStringAndSize(NULL,last / 4 * 3 + pad1 + pad2);
    unsigned char* str = (unsigned char*)PyBytes_AsString(result);
    

    for (size_t i = 0; i < last; i += 4)
    {
        int n = B64index[p[i]] << 18 | B64index[p[i + 1]] << 12 | B64index[p[i + 2]] << 6 | B64index[p[i + 3]];
        str[j++] = n >> 16;
        str[j++] = n >> 8 & 0xFF;
        str[j++] = n & 0xFF;
    }
    if (pad1)
    {
        int n = B64index[p[last]] << 18 | B64index[p[last + 1]] << 12;
        str[j++] = n >> 16;
        if (pad2)
        {
            n |= B64index[p[last + 2]] << 6;
            str[j++] = n >> 8 & 0xFF;
        }
    }
    // printf("result:%s",str);
    return result;
}




unsigned char* Cb64decode(buffer_t* buffer){
    const unsigned char* p = (const unsigned char*)buffer->buf;
    size_t pad1 = buffer->len % 4 || p[buffer->len - 1] == '=';
    size_t pad2 = pad1 && (buffer->len % 4 > 2 || p[buffer->len - 2] != '=');
    size_t j = 0;
    const size_t last = (buffer->len - pad1) / 4 << 2;

    
    unsigned char* result = (unsigned char*)calloc(sizeof(char),last / 4 * 3 + pad1 + pad2);
    unsigned char* str = (unsigned char*)result;
    

    for (size_t i = 0; i < last; i += 4)
    {
        int n = B64index[p[i]] << 18 | B64index[p[i + 1]] << 12 | B64index[p[i + 2]] << 6 | B64index[p[i + 3]];
        str[j++] = n >> 16;
        str[j++] = n >> 8 & 0xFF;
        str[j++] = n & 0xFF;
    }
    if (pad1)
    {
        int n = B64index[p[last]] << 18 | B64index[p[last + 1]] << 12;
        str[j++] = n >> 16;
        if (pad2)
        {
            n |= B64index[p[last + 2]] << 6;
            str[j++] = n >> 8 & 0xFF;
        }
    }
    // printf("result:%s",str);
    return result;
}



#define _gdnode_depack(i) (&buff[i])->buf,(&buff[i])->len
// #define sg(n) &buff[n].buf

PyObject* Write_Json(buffer_t* buff){

    /* Theres alot to depack right here...*/
    yyjson_mut_doc *doc = yyjson_mut_doc_new(NULL);
    yyjson_mut_val *root = yyjson_mut_obj(doc);
    yyjson_mut_doc_set_root(doc, root);

    
    yyjson_mut_obj_add_strn(doc,root,"body",_gdnode_depack(2));
    yyjson_mut_obj_add_strn(doc,root,"PlayerID",_gdnode_depack(3));
    yyjson_mut_obj_add_uint(doc,root,"likes",fast_atoi(&buff[4]));
    yyjson_mut_obj_add_strn(doc,root,"messageID",_gdnode_depack(6));
    yyjson_mut_obj_add_bool(doc,root,"spam",fast_boolean(&buff[7]));
    yyjson_mut_obj_add_strn(doc,root,"AccountID",_gdnode_depack(29));
    /* Age isn't just a number...*/
    yyjson_mut_obj_add_strn(doc,root,"Age",_gdnode_depack(9));
    
    yyjson_mut_obj_add_uint(doc,root,"precent",fast_atoi(&buff[10]));
    yyjson_mut_obj_add_strn(doc,root,"Author",_gdnode_depack(14));
    
    yyjson_mut_obj_add_uint(doc,root,"precent",fast_atoi(&buff[14]));

    yyjson_mut_obj_add_uint(doc,root,"icon",fast_atoi(&buff[22]));
    yyjson_mut_obj_add_uint(doc,root,"PlayerColor",fast_atoi(&buff[23]));
    yyjson_mut_obj_add_uint(doc,root,"PlayerColor2",fast_atoi(&buff[24]));
    yyjson_mut_obj_add_uint(doc,root,"icontype",fast_atoi(&buff[27]));
    yyjson_mut_obj_add_uint(doc,root,"glow",fast_atoi(&buff[28]));

    /* write document */
    size_t len;
    const char* json = yyjson_mut_write(doc,0,&len);

    /* return value */
    yyjson_mut_doc_free(doc);
    return PyBytes_FromStringAndSize(json,(Py_ssize_t)len);
}

#endif