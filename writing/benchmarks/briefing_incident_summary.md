# Production Incident Briefing: API Gateway Cache Eviction Failure

## 1. Executive Summary

At 09:12 UTC, a configuration commit slashed edge Redis TTLs to 60 seconds. This change triggered concurrent cache stampedes on core database replicas. The database stalled. Median query latency climbed from 4.2ms to 890ms. European checkout requests suffered a 6.8% error rate for 24 minutes.

Reverting the bad commit restored healthy read latency at 09:36 UTC. Queued transactions completed safely. Zero rows were lost.

---

## 2. Operational Impact and Telemetry

The incident impacted primary billing paths across two cloud regions:
- **Duration:** 24 minutes (09:12 UTC to 09:36 UTC).
- **Failed Requests:** 14,200 HTTP 504 gateway timeout responses recorded at edge proxies.
- **Database Load:** PostgreSQL primary CPU saturation reached 99.4%, exhausting the 500-client connection pool within 180 seconds.
- **Financial Impact:** Direct customer delays totaled \$42,000 USD; all orders processed successfully following pool recovery.

---

## 3. Mechanical Root Cause

The deployment tool lacked schema checks for cache parameters. An engineer wrote `60` without time units. The orchestrator parsed the value as raw seconds instead of intended minutes. 

Workers purged cached profiles after 60 seconds. This eviction pattern sent 45,000 unindexed join queries per second directly to primary replicas. Pool starvation halted write progress.

---

## 4. Corrective Actions

1. **Parameter Validation:** Added strict compile-time unit validation to the deployment pipeline in commit `d7a4f91`.
2. **Connection Rate Limiting:** Configured PgBouncer transaction pooling; query queues cap at 250 client connections.
3. **Automated Rollback:** Deployed canary monitors that revert updates if pool saturation exceeds 85%.
