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

This exercise demonstrates using ZDM (Zero Downtime Migration) Proxy to migrate from DSE to HCD without any downtime. The ZDM methodology follows the official DataStax 5-phase approach:

**Preparation**: Plan and prepare infrastructure
1. **Phase 1: Deploy ZDM Proxy and Connect Applications** - Deploy proxy, connect apps, enable dual-writes
2. **Phase 2: Migrate and Validate Data** - Backfill historical data using CDM/DSBulk
3. **Phase 3: Enable Asynchronous Dual Reads** (Optional) - Test target performance
4. **Phase 4: Route Reads to Target** - Switch primary to target
5. **Phase 5: Connect Directly to Target** - Final cutover, remove proxy

> **Important:** This lab follows the official DataStax ZDM process as documented at https://docs.datastax.com/en/data-migration/introduction.html

## Preparation: Setup and Verification

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

## Phase 1: Deploy ZDM Proxy and Connect Client Applications

In this phase, we deploy ZDM Proxy and connect applications to it. This activates the dual-write logic: writes are sent to both origin and target databases, while reads are executed on the origin only.

### Step 4: Enable Dual-Write Mode

The ZDM Proxy is already configured for dual-write mode. This is the "cutting point" - from this moment forward, all new writes will go to both DSE (Origin) and HCD (Target), while reads continue from DSE only.

> **Key Concept:** Phase 1 enables dual-writes BEFORE migrating historical data. This ensures the target never falls behind while we backfill old data in Phase 2.

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

## Phase 2: Migrate and Validate Data

In this phase, we use Cassandra Data Migrator (CDM) to copy existing data to the target database. ZDM Proxy continues dual writes, so we can focus on migrating data that existed before ZDM Proxy was connected.

> **Why CDM:** CDM is the recommended tool for ZDM backfill operations. It provides superior performance through Spark-based parallel processing, built-in validation with DiffData, resumability, TTL/writetime preservation, and guardrails to prevent migration issues.

### Step 7: Migrate Historical Data with CDM

Now that dual-writes are active, we can safely migrate historical data from DSE to HCD using CDM. Any data updated during this process will be handled correctly by the dual-write mechanism.

**CDM Benefits:**
- **Performance**: Spark-based parallel processing handles multi-TB datasets efficiently
- **Validation**: Built-in DiffData job ensures consistency
- **Resumability**: Can resume interrupted migrations without starting over
- **Data Fidelity**: Preserves TTL and writetime values
- **Guardrails**: Prevents migration of oversized rows that could cause issues
- **AutoCorrect**: Automatically fixes missing/mismatched data

```bash
# Migrate users table
echo "=== Migrating users table ==="
docker exec spark-cdm spark-submit \
  --properties-file /app/config/cdm.properties \
  --conf spark.cdm.schema.origin.keyspaceTable="training.users" \
  --master 'local[*]' \
  --driver-memory 2g \
  --executor-memory 2g \
  --class com.datastax.cdm.job.Migrate \
  /assets/cassandra-data-migrator-5.6.3.jar \
  2>&1 | tee cdm-logs/migrate-users.log

# Migrate products table
echo "=== Migrating products table ==="
docker exec spark-cdm spark-submit \
  --properties-file /app/config/cdm.properties \
  --conf spark.cdm.schema.origin.keyspaceTable="training.products" \
  --master 'local[*]' \
  --driver-memory 2g \
  --executor-memory 2g \
  --class com.datastax.cdm.job.Migrate \
  /assets/cassandra-data-migrator-5.6.3.jar \
  2>&1 | tee cdm-logs/migrate-products.log

# Migrate orders table
echo "=== Migrating orders table ==="
docker exec spark-cdm spark-submit \
  --properties-file /app/config/cdm.properties \
  --conf spark.cdm.schema.origin.keyspaceTable="training.orders" \
  --master 'local[*]' \
  --driver-memory 2g \
  --executor-memory 2g \
  --class com.datastax.cdm.job.Migrate \
  /assets/cassandra-data-migrator-5.6.3.jar \
  2>&1 | tee cdm-logs/migrate-orders.log

# Migrate user_activity table
echo "=== Migrating user_activity table ==="
docker exec spark-cdm spark-submit \
  --properties-file /app/config/cdm.properties \
  --conf spark.cdm.schema.origin.keyspaceTable="training.user_activity" \
  --master 'local[*]' \
  --driver-memory 2g \
  --executor-memory 2g \
  --class com.datastax.cdm.job.Migrate \
  /assets/cassandra-data-migrator-5.6.3.jar \
  2>&1 | tee cdm-logs/migrate-user_activity.log
```

### Step 8: Validate Migration with CDM

After migrating the data, use CDM's DiffData job to validate consistency:

```bash
# Validate users table
echo "=== Validating users table ==="
docker exec spark-cdm spark-submit \
  --properties-file /app/config/cdm.properties \
  --conf spark.cdm.schema.origin.keyspaceTable="training.users" \
  --master 'local[*]' \
  --driver-memory 2g \
  --executor-memory 2g \
  --class com.datastax.cdm.job.DiffData \
  /assets/cassandra-data-migrator-5.6.3.jar \
  2>&1 | tee cdm-logs/diffdata-users.log

# Validate products table
echo "=== Validating products table ==="
docker exec spark-cdm spark-submit \
  --properties-file /app/config/cdm.properties \
  --conf spark.cdm.schema.origin.keyspaceTable="training.products" \
  --master 'local[*]' \
  --driver-memory 2g \
  --executor-memory 2g \
  --class com.datastax.cdm.job.DiffData \
  /assets/cassandra-data-migrator-5.6.3.jar \
  2>&1 | tee cdm-logs/diffdata-products.log

# Validate orders table
echo "=== Validating orders table ==="
docker exec spark-cdm spark-submit \
  --properties-file /app/config/cdm.properties \
  --conf spark.cdm.schema.origin.keyspaceTable="training.orders" \
  --master 'local[*]' \
  --driver-memory 2g \
  --executor-memory 2g \
  --class com.datastax.cdm.job.DiffData \
  /assets/cassandra-data-migrator-5.6.3.jar \
  2>&1 | tee cdm-logs/diffdata-orders.log

# Validate user_activity table
echo "=== Validating user_activity table ==="
docker exec spark-cdm spark-submit \
  --properties-file /app/config/cdm.properties \
  --conf spark.cdm.schema.origin.keyspaceTable="training.user_activity" \
  --master 'local[*]' \
  --driver-memory 2g \
  --executor-memory 2g \
  --class com.datastax.cdm.job.DiffData \
  /assets/cassandra-data-migrator-5.6.3.jar \
  2>&1 | tee cdm-logs/diffdata-user_activity.log

# Verify data counts match
echo "=== Verifying row counts ==="
echo "DSE counts:"
docker exec dse-node cqlsh -e "SELECT COUNT(*) FROM training.users;"
docker exec dse-node cqlsh -e "SELECT COUNT(*) FROM training.products;"
docker exec dse-node cqlsh -e "SELECT COUNT(*) FROM training.orders;"
docker exec dse-node cqlsh -e "SELECT COUNT(*) FROM training.user_activity;"

echo "HCD counts:"
docker exec hcd-node cqlsh -e "SELECT COUNT(*) FROM training.users;"
docker exec hcd-node cqlsh -e "SELECT COUNT(*) FROM training.products;"
docker exec hcd-node cqlsh -e "SELECT COUNT(*) FROM training.orders;"
docker exec hcd-node cqlsh -e "SELECT COUNT(*) FROM training.user_activity;"
```

**Key Point:** Because dual-writes are already enabled, any data that gets updated during this backfill process will be correctly synchronized by the ZDM Proxy. This prevents data gaps or inconsistencies.

## Phase 3: Enable Asynchronous Dual Reads (Optional but Recommended)

This phase is optional but recommended. Enable asynchronous dual reads to test the target database's ability to handle production workload before permanently switching applications.

### Step 9: Configure Read Routing

For this lab, we'll simulate read routing by updating the ZDM Proxy configuration. In production, you would do this gradually.

> **Official Guidance:** This phase tests target performance without impacting applications. Asynchronous reads are sent to target while synchronous reads continue from origin.

```bash
# View current read mode
docker exec zdm-proxy cat /config/zdm-config.yml | grep -A 2 "read_mode"

# The proxy is configured with:
# read_mode: "PRIMARY_ONLY"
# primary_cluster: "ORIGIN"
# This means all reads go to DSE
```

### Step 10: Test Read Performance

```bash
# Access tools container
docker exec -it tools bash

# Run the read performance test script
/scripts/test_read_performance.sh

exit
```

### Step 11: Validate Data Consistency

Before proceeding, verify that both clusters have consistent data:

```bash
# Access tools container
docker exec -it tools bash

# Run the validation script
python3 /scripts/validate_zdm_migration.py

exit
```

### Step 12: Application Simulation

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

## Phase 4: Route Reads to the Target Database

In this phase, we switch read routing to the target database so all reads are executed on target. Writes are still sent to both databases in case rollback is needed.

### Step 13: Monitor ZDM Proxy Before Switching Reads

Before switching reads to target, verify the system is stable:

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

### Step 14: Monitor Cluster Health

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

### Step 15: Switch Primary Cluster to Target

```bash
# Final validation before switching reads
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

> **Production Step:** In production, you would update ZDM Proxy config to set `primary_cluster: "TARGET"` and restart the proxy. This switches all reads to target while maintaining dual-writes for rollback capability.

For this lab, we'll simulate the target-primary state by testing read performance:

```bash
# Access tools container
docker exec -it tools bash

# Test read performance from target
/scripts/test_read_performance.sh

exit
```

## Phase 5: Connect Directly to the Target Database (Final Cutover)

In the final phase, we move client applications off ZDM Proxy and connect them directly to the target database. Once this happens, the migration is complete.

### Step 16: Simulate Final Cutover

In a real migration, you would:
1. Update application connection strings from `zdm-proxy-host` to `target-node1,target-node2,target-node3`
2. Restart applications gradually
3. Monitor for issues
4. Decommission ZDM Proxy
5. Backup and optionally decommission origin cluster

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

> **Important:** After Phase 5, the origin database is no longer synchronized with the target database. The origin won't contain writes that happen after you disconnect ZDM Proxy.

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
- ✅ Historical data backfilled from DSE to HCD using CDM
- ✅ Data validated using CDM DiffData job
- ✅ Data consistency validated between clusters
- ✅ Dual-read mode tested successfully
- ✅ Monitoring metrics are available
- ✅ Ready for production cutover

## Key Takeaways

1. **Official 5-Phase Approach**:
   - **Preparation**: Plan and prepare infrastructure
   - **Phase 1**: Deploy ZDM Proxy and connect applications (dual-write activation)
   - **Phase 2**: Migrate and validate data (use CDM for production, DSBulk for small datasets)
   - **Phase 3**: Enable asynchronous dual reads (optional, test target performance)
   - **Phase 4**: Route reads to target (target becomes primary)
   - **Phase 5**: Connect directly to target (final cutover, migration complete)

2. **Dual-Write First**: Enable dual-writes in Phase 1 BEFORE migrating historical data in Phase 2 to prevent data gaps

3. **Safe Backfill**: Historical data migration happens while dual-writes are active, ensuring consistency

4. **Zero Downtime**: ZDM Proxy enables true zero-downtime migration with rollback capability until Phase 5

5. **Gradual Migration**: Read traffic can be shifted gradually from origin to target

6. **Schema Matching Required**: Origin and target must have matching schemas (keyspace names, table names, column names, data types)

7. **Monitoring**: Comprehensive metrics for tracking migration progress

8. **Validation**: Continuous validation ensures data consistency

9. **Rollback Capability**: Can rollback at any point before Phase 5 by changing proxy configuration

10. **Production Backfill Tool**: Use **CDM (not DSBulk)** for production backfill operations - CDM provides superior performance, validation, and data fidelity for large-scale migrations

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