# McHash Browns

**DISCLAIMER:** This is a project built for educational purposes only.  Do not take too seriously the benchmarks or methods provided, it was meant for the development and growth of the author.  Thanks for understanding!

## Description
The McHash Browns tool is a systems benchmarking tool designed to stress-test memory allocation throughput in both C and Rust.  By implementing an identical **Separate Chaining Hash Table** (Linked List) in both languages and exposing them via a **FUSE filesystem** with Direct I/O, this tool eliminates kernel-level caching to measure raw application performance.

## Performance Guidelines
It is recommended you manually change the operations being ran based on your own system and the following guidelines to avoid running out of memory and properly completing the benchmark:

| System RAM | Safe "Race Mode" Operations (Est.) |
| :--- | :--- |
| **8 GB** | 50M |
| **16 GB** | 100M |
| **32 GB** | 250M |
| **64 GB** | 500M |

To change the operations based on your specific usage target, edit mchash-browns.py and change the following line to match:

`OPERATION_COUNTS = [100_000, 1_000_000, 10_000_000, 100_000_000, 500_000_000]`

## Setup

The McHash Browns Benchmarking Tool requires Rust to be installed.  Please refer to Rust's documentation to complete this step.

### 1. Install system libraries:

  #### RHEL Dirivatives
  `sudo dnf install gcc make git fuse3-devel jemalloc-devel python3 python3-pip python3-tkinter`

  #### Debian Derivatives
  `sudo apt update`
  
  `sudo apt install build-essential git libfuse3-dev libjemalloc-dev python3 python3-pip python3-tk`

### 2. Install Python Dependencies
  `pip install matplotlib`

### 3. Clone this Repository
  `git clone https://github.com/Refroedgerator/mchash-browns.git`
  
  `cd mchash-browns`
  
### 4. Start McHash Browns
  `python3 mchash-browns.py`

## Findings
The benchmark was conducted on Fedora Linux 43 with 64GB of RAM.  Please refer to the performance chart (above) to reconduct this experiment based on your own specifications.

1. **Low Load:** At low operation counts when utilizing the CPU cache, C and Rust have comparable performance.
2. **High Load:** When the dataset exceeds physical RAM availability Rust outperforms C.

## Conclusions
When both languages utilize the same allocator, whether it be Jemalloc vs Jemalloc or glibc vs glibc, Rust performs better at scale.  This is due to the benchmark hitting the "memory wall" where Rust's strict ownership model allows
the compiler to adhere to strict aliasing (proving pointers do not overlap), enabling optimizations that the C compiler cannot make.

## FINAL NOTE
This isn't to claim that Rust is superior to C in all aspects of performance, just to demonstrate how the compiler and the allocator specifically play a large factor in performance when comparing a Linked List implementation of a Hash Table.  Other more complex and modern implementations may have different outcomes.

## Author
Refroedgerator
