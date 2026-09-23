# Implementing a Lock-Free SPSC Queue in Rust

This guide demonstrates how to build a bounded, lock-free single-producer single-consumer (SPSC) queue in Rust. The implementation uses atomic head and tail indices to coordinate buffer access between two threads without mutex locks.

```rust
use std::cell::UnsafeCell;
use std::mem::MaybeUninit;
use std::sync::atomic::{AtomicUsize, Ordering};

#[repr(align(64))]
pub struct CachePadded<T>(pub T);

pub struct SpscQueue<T, const N: usize> {
    head: CachePadded<AtomicUsize>,
    tail: CachePadded<AtomicUsize>,
    buffer: [UnsafeCell<MaybeUninit<T>>; N],
}
```

## Preventing False Sharing with Cacheline Alignment

On x86-64 and modern ARM processors, L1 caches operate on 64-byte blocks known as cache lines. If `head` and `tail` occupy the same 64-byte slice of memory, writes by the producer invalidate the consumer's L1 cache entry even though the two threads modify different variables. This hardware contention, known as false sharing, triggers continuous cacheline invalidations across CPU interconnects.

The wrapper struct `CachePadded<T>` specifies `#[repr(align(64))]`. This alignment attribute instructs the compiler to place each index on a dedicated cache line, allowing both CPU cores to update their respective pointer without invalidating peer cache lines.

## Coordinating Writes with Acquire-Release Semantics

The queue coordinates slot ownership through two atomic counters:

```rust
impl<T, const N: usize> SpscQueue<T, N> {
    pub fn push(&self, value: T) -> Result<(), T> {
        let head = self.head.0.load(Ordering::Relaxed);
        let tail = self.tail.0.load(Ordering::Acquire);
        if head.wrapping_sub(tail) >= N {
            return Err(value);
        }
        unsafe {
            let slot = self.buffer[head % N].get();
            (*slot).write(value);
        }
        self.head.0.store(head.wrapping_add(1), Ordering::Release);
        Ok(())
    }
}
```

When inserting an item, the producer writes the payload into `self.buffer` before storing the incremented `head` with `Ordering::Release`. The release store acts as a memory barrier: all writes preceding the store must commit to cache before the updated index becomes visible to other CPU cores.

On the consumer side, reading the index with `Ordering::Acquire` pairs directly with the producer's release store. This pairing prevents the CPU from speculatively loading the slot before validating that a new item exists. The consumer is guaranteed to read the newly written payload rather than uninitialized memory.
