#ifndef MCHASH_BROWNS_H
#define MCHASH_BROWNS_H

#include <stdbool.h>
#include <stddef.h>

typedef struct Node {
    int key;
    int value;
    struct Node *next;
} Node;

typedef struct {
    Node **buckets;
    size_t bucket_count;
    size_t size;
} HashTable;

typedef struct {
    size_t operations;
    double total_time;
    size_t successful_ops;
    size_t failed_ops;
} BenchmarkResult;

HashTable* mc_create(size_t bucket_count);
void mc_destroy(HashTable *ht);
bool mc_insert(HashTable *ht, int key, int value);
bool mc_lookup(HashTable *ht, int key, int *value);
bool mc_remove(HashTable *ht, int key);
void mc_clear(HashTable *ht);
size_t mc_size(HashTable *ht);

BenchmarkResult bench_insert_sequential(size_t count);
BenchmarkResult bench_insert_random(size_t count);
BenchmarkResult bench_lookup_sequential(size_t count);
BenchmarkResult bench_lookup_random(size_t count);
BenchmarkResult bench_mixed_workload(size_t count);

#endif
