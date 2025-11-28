#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include "mchash-browns.h"

static size_t hash_function(int key, size_t bucket_count) {
    unsigned int h = (unsigned int)key;
    h = h * 2654435761U;
    return h % bucket_count;
}

HashTable* mc_create(size_t bucket_count) {
    HashTable *ht = malloc(sizeof(HashTable));
    if (!ht) return NULL;
    
    ht->bucket_count = bucket_count;
    ht->size = 0;
    
    ht->buckets = calloc(bucket_count, sizeof(Node*));
    if (!ht->buckets) {
        free(ht);
        return NULL;
    }
    
    return ht;
}

static void free_chain(Node *head) {
    while (head) {
        Node *temp = head;
        head = head->next;
        free(temp);
    }
}

void mc_destroy(HashTable *ht) {
    if (!ht) return;
    
    for (size_t i = 0; i < ht->bucket_count; i++) {
        free_chain(ht->buckets[i]);
    }
    
    free(ht->buckets);
    free(ht);
}

bool mc_insert(HashTable *ht, int key, int value) {
    if (!ht) return false;
    
    size_t bucket = hash_function(key, ht->bucket_count);
    
    Node *current = ht->buckets[bucket];
    while (current) {
        if (current->key == key) {
            current->value = value;
            return true;
        }
        current = current->next;
    }
    
    Node *new_node = malloc(sizeof(Node));
    if (!new_node) return false;
    
    new_node->key = key;
    new_node->value = value;
    new_node->next = ht->buckets[bucket];
    ht->buckets[bucket] = new_node;
    ht->size++;
    
    return true;
}

bool mc_lookup(HashTable *ht, int key, int *value) {
    if (!ht) return false;
    
    size_t bucket = hash_function(key, ht->bucket_count);
    
    Node *current = ht->buckets[bucket];
    while (current) {
        if (current->key == key) {
            if (value) *value = current->value;
            return true;
        }
        current = current->next;
    }
    
    return false;
}

bool mc_remove(HashTable *ht, int key) {
    if (!ht) return false;
    
    size_t bucket = hash_function(key, ht->bucket_count);
    
    Node *current = ht->buckets[bucket];
    Node *prev = NULL;
    
    while (current) {
        if (current->key == key) {
            if (prev) {
                prev->next = current->next;
            } else {
                ht->buckets[bucket] = current->next;
            }
            free(current);
            ht->size--;
            return true;
        }
        prev = current;
        current = current->next;
    }
    
    return false;
}

void mc_clear(HashTable *ht) {
    if (!ht) return;
    
    for (size_t i = 0; i < ht->bucket_count; i++) {
        free_chain(ht->buckets[i]);
        ht->buckets[i] = NULL;
    }
    
    ht->size = 0;
}

size_t mc_size(HashTable *ht) {
    return ht ? ht->size : 0;
}

BenchmarkResult bench_insert_sequential(size_t count) {
    BenchmarkResult result = {0};
    
    size_t buckets = count / 2;
    if (buckets < 1024) buckets = 1024;
    
    HashTable *ht = mc_create(buckets);
    if (!ht) {
        result.failed_ops = count;
        return result;
    }
    
    clock_t start = clock();
    for (size_t i = 0; i < count; i++) {
        if (mc_insert(ht, i, i * 2)) {
            result.successful_ops++;
        } else {
            result.failed_ops++;
        }
    }
    clock_t end = clock();
    
    result.total_time = (double)(end - start) / CLOCKS_PER_SEC;
    result.operations = count;
    
    printf("(bucket_count=%zu, avg_chain_len=%.2f) ", 
           ht->bucket_count, (double)ht->size / ht->bucket_count);
    
    mc_destroy(ht);
    return result;
}

BenchmarkResult bench_insert_random(size_t count) {
    BenchmarkResult result = {0};
    
    int *keys = malloc(count * sizeof(int));
    if (!keys) {
        result.failed_ops = count;
        return result;
    }
    
    srand(12345);
    for (size_t i = 0; i < count; i++) {
        keys[i] = rand();
    }
    
    size_t buckets = count / 2;
    if (buckets < 1024) buckets = 1024;
    
    HashTable *ht = mc_create(buckets);
    if (!ht) {
        free(keys);
        result.failed_ops = count;
        return result;
    }
    
    clock_t start = clock();
    for (size_t i = 0; i < count; i++) {
        if (mc_insert(ht, keys[i], i)) {
            result.successful_ops++;
        } else {
            result.failed_ops++;
        }
    }
    clock_t end = clock();
    
    result.total_time = (double)(end - start) / CLOCKS_PER_SEC;
    result.operations = count;
    
    printf("(bucket_count=%zu, avg_chain_len=%.2f) ", 
           ht->bucket_count, (double)ht->size / ht->bucket_count);
    
    free(keys);
    mc_destroy(ht);
    return result;
}

BenchmarkResult bench_lookup_sequential(size_t count) {
    BenchmarkResult result = {0};
    
    size_t buckets = count / 2;
    if (buckets < 1024) buckets = 1024;
    
    HashTable *ht = mc_create(buckets);
    if (!ht) {
        result.failed_ops = count;
        return result;
    }
    
    for (size_t i = 0; i < count; i++) {
        mc_insert(ht, i, i * 2);
    }
    
    int value;
    clock_t start = clock();
    for (size_t i = 0; i < count; i++) {
        if (mc_lookup(ht, i, &value)) {
            result.successful_ops++;
        } else {
            result.failed_ops++;
        }
    }
    clock_t end = clock();
    
    result.total_time = (double)(end - start) / CLOCKS_PER_SEC;
    result.operations = count;
    
    mc_destroy(ht);
    return result;
}

BenchmarkResult bench_lookup_random(size_t count) {
    BenchmarkResult result = {0};
    
    int *keys = malloc(count * sizeof(int));
    if (!keys) {
        result.failed_ops = count;
        return result;
    }
    
    srand(12345);
    for (size_t i = 0; i < count; i++) {
        keys[i] = rand();
    }
    
    size_t buckets = count / 2;
    if (buckets < 1024) buckets = 1024;
    
    HashTable *ht = mc_create(buckets);
    if (!ht) {
        free(keys);
        result.failed_ops = count;
        return result;
    }
    
    for (size_t i = 0; i < count; i++) {
        mc_insert(ht, keys[i], i);
    }
    
    int value;
    clock_t start = clock();
    for (size_t i = 0; i < count; i++) {
        if (mc_lookup(ht, keys[i], &value)) {
            result.successful_ops++;
        } else {
            result.failed_ops++;
        }
    }
    clock_t end = clock();
    
    result.total_time = (double)(end - start) / CLOCKS_PER_SEC;
    result.operations = count;
    
    free(keys);
    mc_destroy(ht);
    return result;
}

BenchmarkResult bench_mixed_workload(size_t count) {
    BenchmarkResult result = {0};
    
    size_t buckets = count / 2;
    if (buckets < 1024) buckets = 1024;
    
    HashTable *ht = mc_create(buckets);
    if (!ht) {
        result.failed_ops = count;
        return result;
    }
    
    srand(12345);
    int value;
    
    clock_t start = clock();
    for (size_t i = 0; i < count; i++) {
        int op = rand() % 3;
        int key = rand() % (count * 2);
        
        if (op == 0) {
            if (mc_insert(ht, key, key * 2)) {
                result.successful_ops++;
            }
        } else if (op == 1) {
            if (mc_lookup(ht, key, &value)) {
                result.successful_ops++;
            }
        } else {
            if (mc_remove(ht, key)) {
                result.successful_ops++;
            }
        }
    }
    clock_t end = clock();
    
    result.total_time = (double)(end - start) / CLOCKS_PER_SEC;
    result.operations = count;
    
    mc_destroy(ht);
    return result;
}
