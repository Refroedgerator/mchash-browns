#ifndef MC_API_H
#define MC_API_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    MC_OK = 0,
    MC_ERR = 1,
} mc_status;

typedef struct {
    mc_status status;
    uint64_t value;
    const char *msg;
} mc_response;

mc_response mc_insert(const char *key, uint64_t value);
mc_response mc_get(const char *key);
mc_response mc_remove(const char *key);
mc_response mc_clear(void);

mc_response mc_bench_insert(uint64_t n);
mc_response mc_bench_get(uint64_t n);
mc_response mc_surprise(uint64_t n);

const char* mc_info(void);

#ifdef __cplusplus
}

#endif

#endif
