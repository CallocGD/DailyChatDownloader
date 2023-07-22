#ifndef _GDNODE_H_
#define _GDNODE_H_


#include <stdlib.h>
#include <string.h>
#include <Python.h>
#include <stdbool.h>
#include "b64.h"
#include "yyjson/yyjson.h"



#ifdef __cplusplus 
extern "C" {
#endif

typedef struct buffer_s {
    size_t len;
    char* buf;
} buffer_t;


typedef struct gd_node_s {
    size_t pos; /* The string's current position on the parsing phase...*/
    buffer_t* buf; /* An arrary of 30 buffers to use */
    char* raw; /* the raw robtop string to parse through */
} gd_node_t;





void instert_slot(buffer_t* buff,const char* obj , size_t size){
    memcpy(buff->buf, obj, size);
    buff->len = size;
}


PyObject* from_buffer(buffer_t* buff){
    return PyBytes_FromStringAndSize(buff->buf, (Py_ssize_t)buff->len);
}


/* All of these can be ran without the gil if required... */
/* 176 is my magic number to take in the limit of base64 comments (body) which is the longest size possible */

int give_memory(buffer_t* buff){
    buff->buf = (char*)malloc(sizeof(char) * 200);
    if (buff == NULL)
        return -1;
    buff->len = 200;
    return 0;
}

void reset_memory(buffer_t* buffer){
    memset(buffer->buf, 0, buffer->len);
    buffer->len = 0;
}

void free_memory(buffer_t* buff){
    free(buff->buf);
}

/* 2~bunchofcrap~3~etc...*/

int parse_next(gd_node_t* node){
    const char* p = (const char*)node->raw + node->pos;
    const char* lastpos = p;
    const char* startpos;

    size_t slot = 0, offset = 0;

    /* start parsing */
    parse_key:
        switch (*p) {

        case '~':
            p++;
            startpos = p;
            goto parse_value;
        
        default:
            slot = (slot * 10) + (*p - 48);
            p++;
            goto parse_key;
        }

    /* parse the value */
    parse_value:
        switch (*p) {
        
        case '~':
            instert_slot(&node->buf[slot + offset], startpos, (size_t)(p - startpos));
            p++;
            slot = 0;
            goto parse_key;

        
        case ':':
            /* insert items... */
            instert_slot(&node->buf[slot + offset], startpos, (size_t)(p - startpos));
            p++;
            offset = 13;
            slot = 0;
            goto parse_key;

        case '|':
            instert_slot(&node->buf[slot + offset],  startpos, (size_t)(p - startpos));
            p++;
            slot = 0;
            goto finalize;

        case '#':
            instert_slot(&node->buf[slot + offset], startpos, (size_t)(p - startpos));
            p++;
            slot = 0;
            goto finish;

        default:
            p++;
            goto parse_value;
        }

    /* we will be allowed to parse more and return the length correctly the other does 
    returns -1 which means we have no more comments left and we need to move to the pagesum...*/
    finalize:
        node->pos += (size_t)(p - lastpos);
        return 0;

    /* now were really done... */
    finish:
        node->pos += (size_t)(p - lastpos);
        return -1;
}



bool fast_boolean(buffer_t* buff){
    return (buff->buf[0] == 49) ? true: false;
}


Py_ssize_t fast_atoi(buffer_t * buff){
    Py_ssize_t result = 0;
    size_t i = 0;
    int _final = 1;

    if (buff->buf[0] == '-'){
        _final = -1;
        i++;
    }

    for (i; i < buff->len; i++)
        result = (result * 10) + (buff->buf[i] - 48);
    return result * _final;
}


/* ternary is ? true:false */
Py_ssize_t fast_ternary(buffer_t * buff){
    return (buff->buf[0] == 0) ? fast_atoi(buff) : 0;
}





#ifdef __cplusplus 
}
#endif


#endif /* _GDNODE_H_ */