# CPU

## eigen

`--eigen <N>`: Start N eigen workers

### Options

- `--eigen-method <method>`: "all"
- `--eigen-ops <N>`: stop after N Eigen Matrix computation
- `--eigen-size <N>`: specify the 2D matrix size N x N. Default is 32 x 32.


## CPU synchronized loads stressor

`--syncload <N>`: Start N workers. By default repeated cycles of 125ms busy load followed by 62.5ms sleep occur across all the workers in step to create bursts of load to exercise C state transitions and CPU frequency scaling. The busy load and sleeps have +/-10% jitter added to try exercising scheduling patterns.

### Options

- `--syncload-msbusy <M>`: specify the busy load duration in milliseconds
- `--syncload-mssleep <M>`: specify the sleep duration in milliseconds.
- `--syncload-ops <N>`: stop workers after N load/sleep cycles.

## String hashing stressor

`--hash <N>`: Start N workers. 

### Options

- `--hash-method <method>`: "all"
- `--hash-ops <N>`: stops after N hashing rounds

## CPU stressor

`-c <N>, --cpu <N>`: Start N workers

### Options

- `-l <P>, --cpu-load <P>`: load CPU with P percent loading for CPU stress workers. 0 is no load (sleep), and 100 is full loading.
- `--cpu-load-slice S`: CPU load is broken into multiple busy and idle cycles. Use this option to specify the duration of a busy time slice. It is useful only when load is less than 100%
- `--cpu-method <method>`: "all"
- `--cpu-ops <N>`: stop workers after N bogo operations.

## Monte Carlo computations of pi and e and various integrals

`--monte-carlo <N>`: Start N workers.

### Options

- `--monte-carlo-method <[all|e|exp|pi|sin|sqrt]>`
- `--monte-carlo-ops N`: stop after N experiments
- `--monte-carlo-rand <method>`: "all"
- `--monte-carlo-samples <N>`: specify the number of random number samples to use to compute. Default is 100000.

## Crypt Stressor

`--crypt N`: start N wokers

### Options

- `--crypt-ops N`: stop after N bogo encryption operations 

## JPEG compression stressor

`--jpeg <N>`: start N wokers.

### Options

- `--jpeg-height <H>`: use RGB sample image height of H pixels. Default is 512 pixels.
- `--jpeg-image <[brown|flat|gradient|noise|plasma|xstripes]>`
- `--jpeg-ops <N>`: stop after N jpeg compression ops.
- `--jpeg-quality <Q>`: use the compression quality Q. Default is 95
- `--jpeg-width <H>`: use RGB sample image widh of H pixels. Default is 512 pixels.

# IO

## Asynchronous I/O stressor (POSIX AIO)

`--aio <N>`: start N workers. 

### Options

- `--aio-ops <N>`: stop workers after N bogo asynchronous I/O requests.
- `--aio-requests <N>`: specify the number of POSIX asynchronous I/O requests each worker should issue. Default is 16. Max 4096.

# Memory

## Memory allocate and write stressor

`-m N, --vm N`: start N workers.

### Options

- `--vm-bytes <N>`: mmap N bytes per vm worker. Default is 256MB. Can be sepcified as % of total available memory or in units of bytes, kbytes, mbytes, gbytes using suffix, b, k, m or g.
- `--vm-hang <N>`: sleep N seconds before unmapping memory. Default is 0 seconds. 
- `--vm-keep`: do not continually unmap and map memory, just keep on re-writing to it.
- `--vm-locked`: Lock the pages of the mapped region into memory using mmap MAP_LOCKED.
- `--vm-madvice <advice>`: Specify the madvice 'advice' option used on the memory mapped regions used in the vm stressor.
- `--vm-method <method>`: specify a vm stress method. 
- `--vm-ops <N>`: stop workers after N bogo operations.
- `--vm-populate`: populate page tables for the memory mappings, this can stress swapping.

## Random list stressor

`--randlist <N>`: start N workers that creates a list of objects in randomized memory order and traverses the list setting and reading the objects. This is designed to exerise memory and cache thrashing. Normally the objects are allocated on the heap, however for objects of page size or larger there is a 1 in 16 chance of objects being allocated using shared anonymous memory mapping to mix up the address spaces of the allocations to create more TLB thrashing.

### Options

- `--randist-compact`: Allocate all the list objects using one large heap allocation and divide this up for all the list objects. Uses less memory.
- `--randlist-items <N>`: Allocate N items on the list. Default 100,000.
- `--randlist-ops <N>`: stop workers after N list traversals.
- `--randlist-size <N>`: Allocate each item to be N bytes in size. Default is 64 bytes of data payload + the list handling pointer overhead.

## System resources stressor

`--resources <N>` start N workers that consume various system resources. Each worker will spawn 1024 child processes that iterate 1024 times consuming shared memory, heap, stack, temporary files and various file descriptors (eventfds, memoryfds, userfaultfds, pipes and sockets).

### Options

- `--resources-mlock`: attempt to mlock mmap'd pages into memory causing more memory pressure by preventing pages from being swapped out.
- `--resources-ops <N>`: stop after N child forks.

# Network

## Network socket stressor

`-S <N>, --sock <N>` start N workers that perform various socket stress activity. This involves a pair of client/server processes performing rapid connect, send and receives and disconnects on the local host.

### Options

- `--sock-domain <D>`: specify the domain to use, the default is ipv4. Supported options ipv4, ipv6, and unix.
- `--sock-if <NAME>`: use network interface NAME. if the interface NAME does not exist, is not up or does not support the domain then the loopback (lo) interface is used as default.
- `--sock-msgs <N>`: send N messages per connect, send/receive, disconnect iteration. Default is 1000 messages.
- `--sock-nodelay': Disable the TCP Nagle algorithm, so data segments are always setn as soon as possible.
- `--sock-ops <N>`: stop after N bogo operations
- `--sock-opts <[random|send|sendmsg|sendmmsg]>`: Default is send(2). 
- `--sock-port <P>`: start at port P. For N socket worker processors, ports P to P -1 are used.
- `--sock-protocol <P>`: Use the specified protocol P, default is tcp. Options are tcp and mptcp.
- `--sock-type <[stream|seqpacket]>`: specify the socket type to use. Default is stream.
- `--sock-zerocopy`: enable zerocopy for send and recv calls if the MSG_ZEROCOPY is supported.

## Socket I/O stressor

`--sockpair N` start N workers that perform socket pair I/O read/writes. This involves a pair of client/server processes performing randomly sized socket I/O operations.

### Options

- `--sockpair-ops N`: stop workers after N bogo operations.

## UDP network stressor

`--udp N` start N workers that transmit data using UDP. This involves a pair of client/server processes performing rapid connect, send and receives and disconnects on the local host.

### Options

- `--udp-domain <D>`: specify the domain to use, Default is ipv4. ipv4 and ipv6 is supported.
- `--udp-gro`: enable UDP-GRO (Generic Receive Offload) if supported.
- `--udp-if <NAME>`: use network interface NAME.
- `--udp-lite`: use the UDP-List (RFC 3828) protocol
- `--udp-ops <N>`: stop workers after N bogo operations.

# Filesystem

## Copy file stressor

`--copy-file <N>` start N stressors that copy a file using the Linux copy_file_range(2) system call. 128 KB chunks of data are copied from random locations from one file to random locations to a destination file. By default, the files are 256 MB in size. Data is sync'd to the filesystem after each copy_file_range(2) call.

### Options 

- `--copy-file-bytes <N>`: copy file size. The default is 256 MB. Specify as % of free space on filesystem or in units, b, k, m or g.
- `--copy-file-ops <N>`: stop after N `copy_file_range()` calls.

## IO mixing stressor

`--iomix <N>` start N workers that perform a mix of sequential, random and memory mapped read/write operations as well as random copy file read/writes, forced sync'ing and (if run as root) cache dropping. Multiple child processes are spawned to all share a single file and perform different I/O operations on the same file.

### Options

- `--iomix-bytes <N>`: write N bytes for each iomix worker process, default is 1GB.
- `--iomix-ops <N>`: stop workers after N bogo iomix I/O operations.

# Hybrid

## Partial file syncing (sync_file_range) stressor

`--sync-file <N>` start N workers that perform a range of data syncs across a file using sync_file_range(2). Three mixes of syncs are performed, from start to the end of the file, from end of the file to the start, and a random mix. A random selection of valid sync types are used, covering the SYNC_FILE_RANGE_WAIT_BEFORE, SYNC_FILE_RANGE_WRITE and SYNC_FILE_RANGE_WAIT_AFTER flag bits.

### Options

- `--sync-file-bytes <N>`: specify the size of the file to be sync'd.
- `--sync-file-ops <N>`: stop workers after N bogo sync operations.

## Zlib stressor

`--zlib <N>` start N workers compressing and decompressing random data using zlib. Each worker has two processes, one that compresses random data and pipes it to another process that decompresses the data. This stressor exercises CPU, cache and memory.

### Options

- `--zlib-level <L>`: specify the compression level (0..9), where 0 = no compression, 9 = best compression.
- `--zlib-mem-level <L>`: specify the reserved compression state memory for zlib. Default is 8.
- `--zlib-method <method>`: Specify the type of random data to send to the zlib library. Default is random.
- `--zlib-ops <N>`: stop after N bogo compression operations. Each operation is a compression of 64K of random data.
- `--zlib-strategy <S>`: specifies the strategy to use when deflating data. It is used to tune the compression algorithm. Default is 0.
- `--zlib-stream-bytes <S>`: specify the amount of bytes to deflate until defulat should finish the block and return with Z_STREAM_END. 
- `--zlib-window-bites <W>`: specify the window bits used to specify the history buffer size. Default is 15.

## Libc string functions stressor

`--str <N>` start N workers that exercise various libc string functions on random strings.

### Options

- `--str-method <strfunc>`: select a specific libc string function to stress. Default is 'all'.
- `--str-ops <N>`: stop after N bogo string operations.

## Judy array stressor

`--judy <N>` start N workers that insert, search and delete 32 bit integers in a Judy array using a predictable yet sparse array index. By default, there are 131072 integers used in the Judy array. This is a useful method to exercise random access of memory and processor cache.

### Options

- `--judy-ops <N>`: stop workers after N bogo judy operations.
- `--judy-size <N>`: specify the size in the Judy array to exercise. Can be from 1K to 4M 32 bit integers.

## Tree data structures stressor

`--tree N` start N workers that exercise tree data structures. The default is to add, find and remove 250,000 64 bit integers into AVL (avl), Red-Black (rb), Splay (splay), btree and binary trees. The intention of this stressor is to exercise memory and cache with the various tree operations.

### Options

- `--tree-method <[all|avl|binary|btree|rb|splay]>`: specify the tree to be used. Default is 'all'
- `--tree-ops <N>`: stop stressors after N bogo ops. A bogo op convers the addition, finding and removing all the items into the tress.
- `--tree-size <N>`: specify the size of the tree, where N is the number of 64 bit integers to be added into the tree.

## Libc wide character string function stressor

`--wcs N` start N workers that exercise various libc wide character string functions on random strings.

### Options

- `--wcs-method <wcsfunc>`: select a specific libc wide character string function to stress. Default is all.
- `--wcs-ops N`: stop after N bogo wide character string operations.

## 3D Matrix stressor

`--matrix-3d N` start N workers that perform various 3D matrix operations on floating point values. Testing on 64 bit x86 hardware shows that this provides a good mix of memory, cache and floating point operations and is an excellent way to make a CPU run hot.

### Options

- `--matrix-3d-method method`: specify a 3D matrix stress method. Default is all.
- `--matrix-3d-ops N`: stop workers after N bogo operations.
- `--matrix-3d-size N`: specify the N x N x N size of the matrices. Smaller values result in floating point compute throughput bound stressor, where as large values result in a cache and/or memory bandwidth bound stressor.
- `--matrix-3d-zyx`: perform matrix operations in order z by y by x rather than the default x by y by z. This is suboptimal method.


## Sparse matrix stressor

`--sparsematrix N` start N workers that exercise 3 different sparse matrix implementations based on hashing, Judy array (for 64 bit systems), 2-d circular linked-lists, memory mapped 2-d matrix (non-sparse), quick hashing (on preallocated nodes) and red-black tree. The sparse matrix is populated with values, random values potentially non-existing values are read, known existing values are read and known existing values are marked as zero. This default 500 × 500 sparse matrix is used and 5000 items are put into the sparse matrix making it 2% utilized.

### Options

- `--sparcematrix-items N`: populate the sparse matrix with N items. 
- `--sparsematrix-method [all|hash|hashjudy|judy|list|mmap|qhash|rb]`: specify the type of sparse matrix implementation to use.
- `--sparsematrix-ops N`: stop after N test iterations.
- `--sparsematrix-size N`: use a N x N sized sparse matrix.

## STREAM memory stressor

`--stream N` start N workers exercising a memory bandwidth stressor very loosely based on the STREAM "Sustainable Memory Bandwidth in High Performance Computers" benchmarking tool by John D. McCalpin, Ph.D. This stressor allocates buffers that are at least 4 times the size of the CPU L2 cache and continually performs rounds of following computations on large arrays of double precision floating point numbers.

### Options

- `--stream-index N`: specify number of stream indices used to index into the data arrays a, b and c.
- `--stream-l3-size N`: specify the CPU level 3 cache size in bytes. If not specified, stress-ng will try to determine the size, and if fails uses default of 4MB.
- `--stream-mlock`: attempt to mlock the stream buffers into memory to prevent them from begin swapped out.
- `--stream-madvise [collapse|hugepage|nohugepage|normal]`: specify the madvice options used on the memory mapped buffer used in the stream stressor.
- `--stream-ops N`: stop after N bogo operations. A bogo operation is one round of copy, scale, add and triad operations.






