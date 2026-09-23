# When Garbage Collection Trumps Consensus: The Anatomy of a Spurious Failover

Clocks make terrible failure detectors. Distributed consensus protocols like Raft rely on periodic leader heartbeats to suppress follower elections. The algorithm treats an elapsed timer as proof that the leader crashed or the network partitioned. In production, however, heartbeats disappear for reasons unrelated to machine failure.

In managed environments like the JVM or Go runtime, memory management breaks this timing invariant. Under sustained write load, runtimes regularly pause application threads for hundreds of milliseconds to sweep heap allocations. While the process freezes, network traffic keeps arriving at the physical NIC. The Linux kernel processes incoming TCP segments during softirq routines, returns TCP ACKs to the leader without delay, and deposits payload bytes into the socket receive buffer (`SO_RCVBUF`). From the leader's perspective, the link is fine. Network latency metrics look nominal.

```python
def poll_heartbeats(sock: socket.socket, candidate_timer: Timer) -> None:
    # While application threads stall, the OS happily ACKs incoming packets
    while True:
        payload = sock.recv(1024)
        if not payload:
            break
        candidate_timer.reset()
```

Inside the user-space process, nobody is reading the socket. If the memory pause outlasts the follower's 300-millisecond candidate timer, the deadline fires inside the runtime before the worker thread can drain its queued frames. The follower wakes up, assumes the leader is dead, increments its local term counter, and broadcasts vote requests.

When the healthy leader sees that higher term number on an incoming RPC, Raft's core safety invariant forces it to step down on the spot. Client writes stall across the cluster while nodes elect a new leader. The original leader was fully operational, yet Raft deposed it due to a local memory pause on a single follower.

Bumping the heartbeat timeout to multiple seconds masks the symptom, but it degrades recovery times when a node actually loses power. Diego Ongaro's fix (the Pre-Vote protocol) changes the dynamic: followers must first query peers to verify whether the current leader is truly unreachable before bumping their term. If the rest of the cluster is still receiving heartbeats, the delayed follower gets rejected, returns to follower status, and leaves the operational leader alone.
