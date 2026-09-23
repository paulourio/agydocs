Run `ss -s` to track sockets. Run `netstat -s | grep "listen drops"` to detect backlog drops.

Epoll edge-triggered (`EPOLLET`) mode combined with a single-accept loop drops SYN packets. Under heavy load, multiple SYNs arrive between `epoll_wait` wakeups. If the thread accepts exactly one connection and sleeps, the backlog fills up to `net.core.somaxconn`. Linux drops subsequent SYN packets silently.

Check kernel logs for drops:
```bash
dmesg -T | grep "TCP: request_sock_TCP: Possible SYN flooding"
```

Inspect system limits:
```bash
sysctl net.ipv4.tcp_max_syn_backlog
sysctl net.core.somaxconn
```

Buffer the burst temporarily:
```bash
sysctl -w net.core.somaxconn=65535
sysctl -w net.ipv4.tcp_max_syn_backlog=65535
sysctl -w net.ipv4.tcp_syncookies=1
```

The underlying fix drains the backlog fully until `EAGAIN` returns.

```c
// Fixed: loop until EAGAIN
while (1) {
    struct sockaddr_in client_addr;
    socklen_t client_len = sizeof(client_addr);
    int conn_fd = accept(listen_fd, (struct sockaddr *)&client_addr, &client_len);
    
    if (conn_fd == -1) {
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
            break;
        }
        perror("accept error");
        break;
    }
    
    setnonblocking(conn_fd);
    add_to_epoll(conn_fd);
}
```

Enable `SO_REUSEPORT` on the listening socket. The kernel shards incoming TCP connections across multiple threads automatically.
