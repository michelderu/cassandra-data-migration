# Exercise 5: Zero Downtime Migration with ZDM Proxy

## Objectives

- Configure ZDM Proxy for zero-downtime migration
- Enable dual-write mode
- Perform gradual read migration
- Monitor migration progress
- Complete cutover to HCD

## Prerequisites

- Completed Exercises 1-4
- DSE cluster with data
- HCD cluster with schema and data
- ZDM Proxy container running

**Note:** This exercise assumes you are working from the `lab` directory. If starting fresh, run `cd lab` from the project root.

## Duration

60-90 minutes

## Overview

This exercise demonstrates using ZDM (Zero Downtime Migration) Proxy to migrate from DSE to HCD without any downtime. The ZDM methodology follows a 5-phase approach:

1. **Phase 1: Proxy Deployment (Origin Only)** - Deploy proxy, route all traffic through Origin
2. **Phase 2: Enable Dual Writes** - Write to both clusters, read from Origin only
3. **Phase 3: Backfill Historical Data** - Migrate pre-existing data while dual-writes continue
4. **Phase 4: Enable Dual Reads** - Read from both clusters, Origin is primary
5. **Phase 5: Cutover** - Switch to Target as primary, eventually remove proxy

## Phase 1: Proxy Deployment (Origin Only)

### Step 0: Ensure HCD Target is cleared
```bash
docker exec hcd-node cqlsh -e "
TRUNCATE training.users;
TRUNCATE training.products;
TRUNCATE training.orders;
TRUNCATE training.user_activity
"
```

### Step 1: Verify ZDM Proxy Container

```bash
# Check if ZDM Proxy is running
docker-compose ps zdm-proxy

# Check ZDM Proxy logs
docker logs zdm-proxy

# If not running, start it
docker-compose up -d zdm-proxy
```

### Step 2: Configure ZDM Proxy

```bash
# View current configuration
cat zdm-config/zdm-config.yml

# The configuration should look like this:
# origin_contact_points: "dse-node"
# target_contact_points: "hcd-node"
# proxy_listen_port: 9042
# read_mode: "PRIMARY_ONLY"
# primary_cluster: "ORIGIN"
```

### Step 3: Test ZDM Proxy Connectivity

```bash
# Access tools container
docker exec -it tools bash

# Test connection through ZDM Proxy
cqlsh zdm-proxy 9042 -e "SELECT cluster_name FROM system.local;"

# Expected: Should connect successfully
# Note: The cluster name will be from the origin (DSE) cluster

# Test basic query
cqlsh zdm-proxy 9042 -e "SELECT COUNT(*) FROM training.users;"

# Exit container
exit
```

## Phase 2: Enable Dual Writes

### Step 4: Enable Dual-Write Mode

The ZDM Proxy is already configured for dual-write mode. This is the "cutting point" - from this moment forward, all new writes will go to both DSE (Origin) and HCD (Target), while reads continue from DSE only.

**Important:** We enable dual-writes BEFORE migrating historical data. This ensures the Target never falls behind while we backfill old data.

```bash
# Access tools container
docker exec -it tools bash

# Insert test data through proxy
cqlsh zdm-proxy 9042 -e "
INSERT INTO training.users (user_id, username, email, status, created_at)
VALUES (uuid(), 'zdm_test_user', 'zdm@test.com', 'active', toTimestamp(now()));
"

# Verify data exists on both clusters
echo "=== Checking DSE ==="
cqlsh dse-node -e "
SELECT username, email FROM training.users WHERE username = 'zdm_test_user' ALLOW FILTERING;
"

echo "=== Checking HCD ==="
cqlsh hcd-node -e "
SELECT username, email FROM training.users WHERE username = 'zdm_test_user' ALLOW FILTERING;
"

# Both should show the new user
exit
```

### Step 5: Bulk Write Test

```bash
# Still in tools container

# The test script is provided at /scripts/test_dual_write.py
# Run the bulk write test
python3 /scripts/test_dual_write.py

# Verify on both clusters
echo "=== DSE Count ==="
cqlsh dse-node -e "
SELECT username FROM training.users
" | grep zdm_bulk | wc -l

echo "=== HCD Count ==="
cqlsh hcd-node -e "
SELECT username FROM training.users
" | grep zdm_bulk | wc -l

# Exit container
exit
```

### Step 6: Monitor ZDM Proxy Metrics

```bash
# Check all ZDM Proxy metrics
curl -s http://localhost:14001/metrics | grep zdm_

# Key metrics to monitor:

# 1. Request counts by type
echo "=== Request Counts ==="
curl -s http://localhost:14001/metrics | grep "zdm_proxy_request_duration_seconds_count"
# Shows: reads_origin, reads_target, writes

# 2. Failed writes (critical for dual-write validation)
echo "=== Failed Writes ==="
curl -s http://localhost:14001/metrics | grep "zdm_proxy_failed_writes_total"
# Shows: failed_on="both", failed_on="origin", failed_on="target"

# 3. Request latency histograms
echo "=== Request Latency ==="
curl -s http://localhost:14001/metrics | grep "zdm_proxy_request_duration_seconds_sum"
# Calculate average: sum / count

# 4. Origin vs Target request distribution
echo "=== Origin Requests ==="
curl -s http://localhost:14001/metrics | grep "zdm_origin_request_duration_seconds_count"

echo "=== Target Requests ==="
curl -s http://localhost:14001/metrics | grep "zdm_target_request_duration_seconds_count"

# 5. Connection status
echo "=== Connections ==="
curl -s http://localhost:14001/metrics | grep "zdm_.*_connections_total"

# 6. In-flight requests
echo "=== In-Flight Requests ==="
curl -s http://localhost:14001/metrics | grep "zdm_proxy_inflight_requests_total"

# View in Prometheus (optional)
# Open browser: http://localhost:9090
# Useful queries:
# - rate(zdm_proxy_request_duration_seconds_count[5m])
# - zdm_proxy_failed_writes_total
# - histogram_quantile(0.95, rate(zdm_proxy_request_duration_seconds_bucket[5m]))
```

**Understanding the Metrics:**

- `zdm_proxy_request_duration_seconds_count{type="writes"}` - Total write requests through proxy
- `zdm_origin_request_duration_seconds_count` - Requests sent to Origin (DSE)
- `zdm_target_request_duration_seconds_count` - Requests sent to Target (HCD)
- `zdm_proxy_failed_writes_total{failed_on="target"}` - Writes that failed on Target only (expected during initial setup)
- `zdm_proxy_failed_writes_total{failed_on="both"}` - Critical failures (investigate immediately)

## Phase 3: Backfill Historical Data

### Step 7: Migrate Historical Data

Now that dual-writes are active, we can safely migrate historical data from DSE to HCD. Any data updated during this process will be handled correctly by the dual-write mechanism.

```bash
# Access tools container
docker exec -it tools bash

# Export data from DSE
echo "Exporting historical data from DSE..."
dsbulk unload \
  -h dse-node \
  -k training \
  -t users \
  -url /data/export/users

dsbulk unload \
  -h dse-node \
  -k training \
  -t products \
  -url /data/export/products

dsbulk unload \
  -h dse-node \
  -k training \
  -t orders \
  -url /data/export/orders

dsbulk unload \
  -h dse-node \
  -k training \
  -t user_activity \
  -url /data/export/user_activity

# Import data to HCD
echo "Importing historical data to HCD..."
dsbulk load \
  -h hcd-node \
  -k training \
  -t users \
  -url /data/export/users

dsbulk load \
  -h hcd-node \
  -k training \
  -t products \
  -url /data/export/products

dsbulk load \
  -h hcd-node \
  -k training \
  -t orders \
  -url /data/export/orders

dsbulk load \
  -h hcd-node \
  -k training \
  -t user_activity \
  -url /data/export/user_activity

# Verify data counts match
echo "=== Verifying backfill ==="
echo "DSE counts:"
cqlsh dse-node -e "SELECT COUNT(*) FROM training.users;"
cqlsh dse-node -e "SELECT COUNT(*) FROM training.products;"
cqlsh dse-node -e "SELECT COUNT(*) FROM training.orders;"
cqlsh dse-node -e "SELECT COUNT(*) FROM training.user_activity;"

echo "HCD counts:"
cqlsh hcd-node -e "SELECT COUNT(*) FROM training.users;"
cqlsh hcd-node -e "SELECT COUNT(*) FROM training.products;"
cqlsh hcd-node -e "SELECT COUNT(*) FROM training.orders;"
cqlsh hcd-node -e "SELECT COUNT(*) FROM training.user_activity;"

exit
```

**Key Point:** Because dual-writes are already enabled, any data that gets updated during this backfill process will be correctly synchronized by the ZDM Proxy. This prevents data gaps or inconsistencies.

## Phase 4: Enable Dual Reads

### Step 8: Configure Read Routing

For this lab, we'll simulate read routing by updating the ZDM Proxy configuration. In production, you would do this gradually.

```bash
# View current read mode
docker exec zdm-proxy cat /config/zdm-config.yml | grep -A 2 "read_mode"

# The proxy is configured with:
# read_mode: "PRIMARY_ONLY"
# primary_cluster: "ORIGIN"
# This means all reads go to DSE
```

### Step 9: Validate Data Consistency

Before enabling dual reads, verify that both clusters have consistent data:

```bash
# Access tools container
docker exec -it tools bash

# Run the validation script
python3 /scripts/validate_zdm_migration.py

exit
```

### Step 10: Test Read Performance

```bash
# Access tools container
docker exec -it tools bash

# Run the read performance test script
/scripts/test_read_performance.sh

exit
```

### Step 11: Application Simulation

Simulate realistic application traffic through the ZDM Proxy to test dual-write and dual-read functionality:

```bash
# Access tools container
docker exec -it tools bash

# Run the application simulation script (default: 30 seconds)
python3 /scripts/simulate_app_traffic.py

# Or run with custom parameters:
# - Run for 60 seconds with 1 second delay between operations
python3 /scripts/simulate_app_traffic.py --duration 60 --delay 1.0

# - Adjust read/write ratio (80% reads, 20% writes)
python3 /scripts/simulate_app_traffic.py --read-ratio 0.8

# - Run for 2 minutes with faster operations
python3 /scripts/simulate_app_traffic.py --duration 120 --delay 0.2

exit
```

**What the script does:**
- Connects through ZDM Proxy to simulate real application behavior
- Performs a mix of read and write operations (default: 75% reads, 25% writes)
- Uses various query patterns: LIMIT, FILTER, COUNT, INSERT, UPDATE
- Provides real-time operation logging
- Displays comprehensive statistics at the end

**Expected output:**
```
Simulating application traffic through ZDM Proxy
Duration: 30 seconds
Read ratio: 75%
Write ratio: 25%

[1] Read (LIMIT): Retrieved 10 users
[2] Write (INSERT): Created user app_user_2_1234
[3] Read (FILTER): Retrieved 5 active users
...

Simulation Summary
Duration: 30.1 seconds
Total operations: 60
Operations/second: 1.99

Reads: 45 (75.0%)
Writes: 15 (25.0%)

✅ All operations completed successfully!
```

## Phase 5: Cutover to Target

### Step 12: Monitor ZDM Proxy

```bash
# View ZDM Proxy metrics
curl -s http://localhost:14001/metrics | grep -E "zdm_proxy" | head -20

# Check request distribution
echo "=== Request Distribution ==="
curl -s http://localhost:14001/metrics | grep "zdm_origin_requests_total"
curl -s http://localhost:14001/metrics | grep "zdm_proxy_target_requests_total"

# Check error rates
echo "=== Error Rates ==="
curl -s http://localhost:14001/metrics | grep "zdm_proxy_errors_total"
```

### Step 13: Monitor Cluster Health

```bash
# Check DSE cluster
echo "=== DSE Cluster Status ==="
docker exec dse-node nodetool status

# Check HCD cluster
echo "=== HCD Cluster Status ==="
docker exec hcd-node nodetool status

# Check compaction on HCD (should be active due to writes)
echo "=== HCD Compaction Status ==="
docker exec hcd-node nodetool compactionstats

# Check table statistics
echo "=== HCD Table Statistics ==="
docker exec hcd-node nodetool tablestats training.users | grep -E "Table:|Number of partitions|Memtable|Compacted"
```

### Step 14: Prepare for Cutover

```bash
# Final validation before cutover
docker exec -it tools bash

# Run final consistency check
python3 /scripts/validate_zdm_migration.py

# Check cluster health
nodetool -h dse-node status
nodetool -h hcd-node status

# Verify no pending compactions
nodetool -h hcd-node compactionstats

exit
```

### Step 15: Simulate Cutover

In a real migration, you would:
1. Update ZDM Proxy config to set `primary_cluster: "TARGET"`
2. Restart ZDM Proxy
3. Monitor for issues
4. Eventually remove ZDM Proxy and connect directly to HCD

For this lab, we'll simulate by testing direct HCD connections:

```bash
# Access tools container
docker exec -it tools bash

# Test direct connection to HCD
cqlsh hcd-node -e "
SELECT cluster_name, release_version FROM system.local;
SELECT COUNT(*) FROM training.users;
"

# Verify all data is accessible
cqlsh hcd-node -e "
SELECT COUNT(*) FROM training.users;
SELECT COUNT(*) FROM training.products;
SELECT COUNT(*) FROM training.orders;
SELECT COUNT(*) FROM training.user_activity;
"

# Test application queries
cqlsh hcd-node -e "
SELECT username, email, status FROM training.users 
WHERE status = 'active' LIMIT 10 ALLOW FILTERING;
"

exit
```

## Troubleshooting

### Issue: ZDM Proxy won't start

```bash
# Check logs
docker logs zdm-proxy

# Verify configuration
cat zdm-config/zdm-config.yml

# Check if clusters are accessible
docker exec tools ping dse-node
docker exec tools ping hcd-node

# Restart proxy
docker-compose restart zdm-proxy
```

### Issue: Writes not reaching both clusters

```bash
# Check ZDM Proxy logs
docker logs zdm-proxy | grep -i error

# Verify dual-write is enabled
curl http://localhost:14001/metrics | grep target_requests

# Test connectivity
docker exec tools cqlsh dse-node -e "SELECT COUNT(*) FROM training.users;"
docker exec tools cqlsh hcd-node -e "SELECT COUNT(*) FROM training.users;"
```

### Issue: High latency through proxy

```bash
# Check proxy metrics
curl http://localhost:14001/metrics | grep duration

# Check cluster latency
docker exec dse-node nodetool proxyhistograms
docker exec hcd-node nodetool proxyhistograms

# Verify network
docker exec tools ping -c 5 zdm-proxy
```

## Success Criteria

You have successfully completed this exercise when:

- ✅ ZDM Proxy deployed and routing traffic through Origin
- ✅ Dual-write mode enabled (writes go to both clusters)
- ✅ Historical data backfilled from DSE to HCD using DSBulk
- ✅ Data consistency validated between clusters
- ✅ Dual-read mode tested successfully
- ✅ Monitoring metrics are available
- ✅ Ready for production cutover

## Key Takeaways

1. **5-Phase Approach**: ZDM follows a structured methodology: Proxy Deployment → Dual Writes → Backfill → Dual Reads → Cutover
2. **Dual-Write First**: Enable dual-writes BEFORE migrating historical data to prevent data gaps
3. **Safe Backfill**: Historical data migration happens while dual-writes are active, ensuring consistency
4. **Zero Downtime**: ZDM Proxy enables true zero-downtime migration
5. **Gradual Migration**: Read traffic can be shifted gradually from Origin to Target
6. **Monitoring**: Comprehensive metrics for tracking migration progress
7. **Validation**: Continuous validation ensures data consistency
8. **Rollback**: Easy to rollback by changing proxy configuration

## Next Steps

Proceed to [Exercise 6: Validation and Monitoring](06-validation-monitoring.md) for comprehensive validation techniques and monitoring setup.

## Clean Up

```bash
# Stop ZDM Proxy
docker-compose stop zdm-proxy

# Remove test data
docker exec hcd-node cqlsh -e "
DELETE FROM training.users WHERE username LIKE 'zdm_%' ALLOW FILTERING;
DELETE FROM training.users WHERE username LIKE 'app_user_%' ALLOW FILTERING;
"

# Restart ZDM Proxy
docker-compose start zdm-proxy
```

---

**Time to Complete:** 60-90 minutes  
**Difficulty:** Advanced
**Next Exercise:** [Validation and Monitoring](06-validation-monitoring.md)