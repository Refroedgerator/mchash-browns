use tikv_jemallocator::Jemalloc;

#[global_allocator]
static GLOBAL: Jemalloc = Jemalloc;

use fuser::{
    FileAttr, FileType, Filesystem, MountOption, ReplyAttr, ReplyData, ReplyDirectory, ReplyEntry,
    ReplyOpen, ReplyWrite, Request,
};
use libc::{ENOENT, EIO};
use std::ffi::OsStr;
use std::sync::Mutex;
use std::time::{Duration, Instant, UNIX_EPOCH};

struct Node {
    key: i64,
    value: i64,
    next: Option<Box<Node>>,
}

struct HashTable {
    buckets: Vec<Option<Box<Node>>>,
    bucket_count: usize,
    size: usize,
}

impl HashTable {
    fn mc_new(bucket_count: usize) -> Self {
        let mut buckets = Vec::with_capacity(bucket_count);
        for _ in 0..bucket_count {
            buckets.push(None);
        }
        HashTable { buckets, bucket_count, size: 0 }
    }

    fn mc_hash(&self, key: i64) -> usize {
        let mut h = key as u64;
        h = h.wrapping_mul(2654435761);
        (h % self.bucket_count as u64) as usize
    }

    fn mc_insert(&mut self, key: i64, value: i64) {
        let idx = self.mc_hash(key);
        let mut current = &mut self.buckets[idx];
        while let Some(node) = current {
            if node.key == key {
                node.value = value;
                return;
            }
            current = &mut node.next;
        }
        let new_node = Box::new(Node {
            key,
            value,
            next: self.buckets[idx].take(),
        });
        self.buckets[idx] = Some(new_node);
        self.size += 1;
    }

    fn mc_lookup(&self, key: i64) -> Option<i64> {
        let idx = self.mc_hash(key);
        let mut current = &self.buckets[idx];
        while let Some(node) = current {
            if node.key == key {
                return Some(node.value);
            }
            current = &node.next;
        }
        None
    }
}

const TTL: Duration = Duration::from_secs(1);
const FILE_NAME: &str = "mcfrier";
const FILE_INO: u64 = 2;

struct McFrierFS {
    ht: Mutex<Option<HashTable>>,
    result_buffer: Mutex<String>,
}

impl McFrierFS {
    fn new() -> Self {
        Self {
            ht: Mutex::new(None),
            result_buffer: Mutex::new(String::from("READY\n")),
        }
    }
}

impl Filesystem for McFrierFS {
    fn lookup(&mut self, _req: &Request, parent: u64, name: &OsStr, reply: ReplyEntry) {
        if parent == 1 && name.to_str() == Some(FILE_NAME) {
            let len = self.result_buffer.lock().unwrap().len() as u64;
            reply.entry(&TTL, &file_attr(FILE_INO, len), 0);
        } else {
            reply.error(ENOENT);
        }
    }

    fn getattr(&mut self, _req: &Request, ino: u64, reply: ReplyAttr) {
        match ino {
            1 => reply.attr(&TTL, &dir_attr(1)),
            FILE_INO => {
                let len = self.result_buffer.lock().unwrap().len() as u64;
                reply.attr(&TTL, &file_attr(FILE_INO, len))
            },
            _ => reply.error(ENOENT),
        }
    }

    fn open(&mut self, _req: &Request, ino: u64, _flags: i32, reply: ReplyOpen) {
        if ino == FILE_INO {
            reply.opened(0, 1 << 0);
        } else {
            reply.error(ENOENT);
        }
    }

    fn read(&mut self, _req: &Request, ino: u64, _fh: u64, offset: i64, _size: u32, _flags: i32, _lock_owner: Option<u64>, reply: ReplyData) {
        if ino == FILE_INO {
            let data = self.result_buffer.lock().unwrap();
            let bytes = data.as_bytes();
            if offset as usize >= bytes.len() {
                reply.data(&[]);
            } else {
                reply.data(&bytes[offset as usize..]);
            }
        } else {
            reply.error(ENOENT);
        }
    }

    fn write(&mut self, _req: &Request, ino: u64, _fh: u64, _offset: i64, data: &[u8], _write_flags: u32, _flags: i32, _lock_owner: Option<u64>, reply: ReplyWrite) {
        if ino != FILE_INO {
            reply.error(ENOENT);
            return;
        }

        let command = String::from_utf8_lossy(data);
        let parts: Vec<&str> = command.trim().split_whitespace().collect();

        if parts.is_empty() {
            reply.error(EIO);
            return;
        }

        let op = parts[0];
        let count: i64 = parts.get(1).and_then(|s| s.parse().ok()).unwrap_or(0);

        if op == "INSERT_SEQ" {
            println!("[RUST] Inserting {} items...", count);
            let buckets = std::cmp::max(count as usize / 2, 1024);
            let mut new_ht = HashTable::mc_new(buckets);

            let start = Instant::now();
            for i in 0..count {
                new_ht.mc_insert(i, i * 2);
            }
            let duration = start.elapsed();

            {
                let mut ht_guard = self.ht.lock().unwrap();
                *ht_guard = Some(new_ht);
            }

            let response = format!("OK {:.6}\n", duration.as_secs_f64());
            *self.result_buffer.lock().unwrap() = response;
        } 
        else if op == "LOOKUP_SEQ" {
            println!("[RUST] Looking up {} items...", count);
            let ht_guard = self.ht.lock().unwrap();
            if let Some(ht) = ht_guard.as_ref() {
                let start = Instant::now();
                for i in 0..count {
                    ht.mc_lookup(i);
                }
                let duration = start.elapsed();

                let response = format!("OK {:.6}\n", duration.as_secs_f64());
                *self.result_buffer.lock().unwrap() = response;
            } else {
                *self.result_buffer.lock().unwrap() = "ERROR NO_TABLE\n".to_string();
            }
        }

        reply.written(data.len() as u32);
    }

    fn readdir(&mut self, _req: &Request, ino: u64, _fh: u64, offset: i64, mut reply: ReplyDirectory) {
        if ino != 1 { reply.error(ENOENT); return; }
        if offset == 0 {
            let _ = reply.add(1, 0, FileType::Directory, ".");
            let _ = reply.add(1, 1, FileType::Directory, "..");
            let _ = reply.add(FILE_INO, 2, FileType::RegularFile, FILE_NAME);
        }
        reply.ok();
    }
}

fn dir_attr(ino: u64) -> FileAttr {
    FileAttr {
        ino, size: 0, blocks: 0, atime: UNIX_EPOCH, mtime: UNIX_EPOCH, ctime: UNIX_EPOCH, crtime: UNIX_EPOCH,
        kind: FileType::Directory, perm: 0o755, nlink: 2, uid: unsafe { libc::getuid() }, gid: unsafe { libc::getgid() }, rdev: 0, blksize: 512, flags: 0,
    }
}

fn file_attr(ino: u64, size: u64) -> FileAttr {
    FileAttr {
        ino, size, blocks: 1, atime: UNIX_EPOCH, mtime: UNIX_EPOCH, ctime: UNIX_EPOCH, crtime: UNIX_EPOCH,
        kind: FileType::RegularFile, perm: 0o666, nlink: 1, uid: unsafe { libc::getuid() }, gid: unsafe { libc::getgid() }, rdev: 0, blksize: 512, flags: 0,
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if let Some(mountpoint) = args.last() {
        let options = vec![
            MountOption::RW, 
            MountOption::FSName("mcfrier_rust".to_string())
        ];
        fuser::mount2(McFrierFS::new(), mountpoint, &options).unwrap();
    } else {
        eprintln!("Usage: {} <mountpoint>", args[0]);
    }
}
