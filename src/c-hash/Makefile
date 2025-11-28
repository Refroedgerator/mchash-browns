CC = gcc
CFLAGS = -Wall -Wextra -D_FILE_OFFSET_BITS=64 -O2 -g

FUSE_CFLAGS := $(shell pkg-config --cflags fuse3 2>/dev/null || pkg-config --cflags fuse)
FUSE_LIBS := $(shell pkg-config --libs fuse3 2>/dev/null || pkg-config --libs fuse)

SRCS = mchash-browns.c main.c
OBJS = $(SRCS:.c=.o)

all: fuse_mount

fuse_mount: $(OBJS)
	$(CC) $(CFLAGS) -o fuse_mount $(OBJS) $(FUSE_LIBS) -ljemalloc
	@echo "Built fuse_mount successfully"

%.o: %.c mchash-browns.h
	$(CC) $(CFLAGS) $(FUSE_CFLAGS) -c $< -o $@

check-fuse:
	@echo "Checking FUSE installation..."
	@pkg-config --modversion fuse3 2>/dev/null && echo "Found FUSE3" || \
	 (pkg-config --modversion fuse 2>/dev/null && echo "Found FUSE2") || \
	 echo "ERROR: No FUSE found"

clean:
	rm -f fuse_mount *.o

.PHONY: all check-fuse clean
