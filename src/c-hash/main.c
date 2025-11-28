#define FUSE_USE_VERSION 31

#include <fuse.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>
#include "mchash-browns.h"

static const char *filename = "/mcfrier";
static char result_buffer[512] = "READY\n";
static HashTable *global_ht = NULL;

static int do_getattr(const char *path, struct stat *st, struct fuse_file_info *fi) {
    (void) fi;
    memset(st, 0, sizeof(struct stat));
    
    st->st_uid = getuid();
    st->st_gid = getgid();

    if (strcmp(path, "/") == 0) {
        st->st_mode = S_IFDIR | 0755;
        st->st_nlink = 2;
    } else if (strcmp(path, filename) == 0) {
        st->st_mode = S_IFREG | 0666;
        st->st_nlink = 1;
        st->st_size = strlen(result_buffer);
    } else {
        return -ENOENT;
    }
    return 0;
}

static int do_open(const char *path, struct fuse_file_info *fi) {
    if (strcmp(path, filename) != 0) return -ENOENT;
    fi->direct_io = 1;
    return 0;
}

static int do_read(const char *path, char *buf, size_t size, off_t offset, struct fuse_file_info *fi) {
    (void) fi;
    if (strcmp(path, filename) != 0) return -ENOENT;

    size_t len = strlen(result_buffer);
    if (offset >= (off_t)len) return 0;
    if (offset + size > len) size = len - offset;
    memcpy(buf, result_buffer + offset, size);
    return size;
}

static int do_write(const char *path, const char *buf, size_t size, off_t offset, struct fuse_file_info *fi) {
    (void) offset; (void) fi;
    if (strcmp(path, filename) != 0) return -ENOENT;

    char command[256];
    size_t safe_size = size < 255 ? size : 255;
    memcpy(command, buf, safe_size);
    command[safe_size] = '\0';

    long count = 0;

    if (sscanf(command, "INSERT_SEQ %ld", &count) == 1) {
        if (global_ht) mc_destroy(global_ht);
        
        size_t buckets = count / 2;
        if (buckets < 100) buckets = 100;
        global_ht = mc_create(buckets);

        if (!global_ht) {
            snprintf(result_buffer, sizeof(result_buffer), "ERROR OOM_CREATE\n");
            return size;
        }

        clock_t start = clock();
        for (long i = 0; i < count; i++) {
            mc_insert(global_ht, i, i * 2);
        }
        clock_t end = clock();
        
        double time_taken = (double)(end - start) / CLOCKS_PER_SEC;
        snprintf(result_buffer, sizeof(result_buffer), "OK %.6f\n", time_taken);
        
        printf("[C-FUSE] Insert %ld: %.6f s\n", count, time_taken);
        fflush(stdout); 
    }
    else if (sscanf(command, "LOOKUP_SEQ %ld", &count) == 1) {
        if (!global_ht) {
            snprintf(result_buffer, sizeof(result_buffer), "ERROR NO_TABLE\n");
            return size;
        }

        clock_t start = clock();
        int val;
        for (long i = 0; i < count; i++) {
            mc_lookup(global_ht, i, &val);
        }
        clock_t end = clock();

        double time_taken = (double)(end - start) / CLOCKS_PER_SEC;
        snprintf(result_buffer, sizeof(result_buffer), "OK %.6f\n", time_taken);
        printf("[C-FUSE] Lookup %ld: %.6f s\n", count, time_taken);
        fflush(stdout);
    }
    else {
        snprintf(result_buffer, sizeof(result_buffer), "ERROR INVALID_CMD\n");
    }

    return size;
}

static int do_readdir(const char *path, void *buf, fuse_fill_dir_t filler, off_t offset, struct fuse_file_info *fi, enum fuse_readdir_flags flags) {
    (void) offset; (void) fi; (void) flags;
    if (strcmp(path, "/") != 0) return -ENOENT;
    filler(buf, ".", NULL, 0, 0);
    filler(buf, "..", NULL, 0, 0);
    filler(buf, filename + 1, NULL, 0, 0);
    return 0;
}

static struct fuse_operations operations = {
    .getattr = do_getattr,
    .open    = do_open,
    .read    = do_read,
    .write   = do_write,
    .readdir = do_readdir,
};

int main(int argc, char *argv[]) {
    return fuse_main(argc, argv, &operations, NULL);
}
