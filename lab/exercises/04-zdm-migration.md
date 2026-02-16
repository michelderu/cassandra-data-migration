# Exercise 4: Zero Downtime Migration with ZDM Proxy

## Objectives

- Configure ZDM Proxy for zero-downtime migration
- Enable dual-write mode
- Perform gradual read migration
- Monitor migration progress
- Complete cutover to HCD

## Prerequisites

- Completed Exercises 1-3
- DSE cluster with data
- HCD cluster with schema and data
- ZDM Proxy container running

## Duration

60-90 minutes

## Overview

This exercise demonstrates using ZDM (Zero Downtime Migration) Proxy to migrate from DSE to HCD without any downtime. The proxy sits between applications and clusters, enabling dual-write and gradual read migration.

## Part 1: ZDM Proxy Configuration

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
cat lab/zdm-config/zdm-config.yml

# The configuration should look like this:
# origin_contact_points: "dse-node1,dse-node2,dse-node3"
# target_contact_points: "hcd-node1,hcd-node2,hcd-node3"
# proxy_listen_port: 9042
# read_mode: "PRIMARY_ONLY"
# primary_cluster: "ORIGIN"
```

### Step 3: Test ZDM Proxy Connectivity

```bash
# Access migration-tools container
docker exec -it migration-tools bash

# Test connection through ZDM Proxy
cqlsh zdm-proxy 9042 -e "SELECT cluster_name FROM system.local;"

# Expected: Should connect successfully
# Note: The cluster name will be from the origin (DSE) cluster

# Test basic query
cqlsh zdm-proxy 9042 -e "SELECT COUNT(*) FROM training.users;"

# Exit container
exit
```

## Part 2: Phase 1 - Dual-Write Mode

### Step 4: Enable Dual-Write

The ZDM Proxy is already configured for dual-write mode. Let's verify it's working:

```bash
# Access migration-tools container
docker exec -it migration-tools bash

# Insert test data through proxy
cqlsh zdm-proxy 9042 -e "
INSERT INTO training.users (user_id, username, email, status, created_at)
VALUES (uuid(), 'zdm_test_user', 'zdm@test.com', 'active', toTimestamp(now()));
"

# Verify data exists on both clusters
echo "=== Checking DSE ==="
cqlsh dse-node1 -e "
SELECT username, email FROM training.users WHERE username = 'zdm_test_user' ALLOW FILTERING;
"

echo "=== Checking HCD ==="
cqlsh hcd-node1 -e "
SELECT username, email FROM training.users WHERE username = 'zdm_test_user' ALLOW FILTERING;
"

# Both should show the new user
```

### Step 5: Bulk Write Test

```bash
# Still in migration-tools container

# Create test script for bulk writes
cat > /scripts/test_dual_write.py << 'EOF'
from cassandra.cluster import Cluster
import uuid
from datetime import datetime

# Connect through ZDM Proxy
cluster = Cluster(['zdm-proxy'], port=9042)
session = cluster.connect('training')

# Prepare statement
insert_stmt = session.prepare("""
    INSERT INTO users (user_id, username, email, status, created_at)
    VALUES (?, ?, ?, ?, ?)
""")

print("Inserting 100 test users through ZDM Proxy...")

for i in range(100):
    session.execute(insert_stmt, (
        uuid.uuid4(),
        f'zdm_bulk_user_{i}',
        f'zdm_bulk_{i}@test.com',
        'active',
        datetime.now()
    ))
    
    if (i + 1) % 10 == 0:
        print(f"  Inserted {i + 1} users...")

print("✓ Bulk insert complete")

cluster.shutdown()
EOF

# Run the test
python3 /scripts/test_dual_write.py

# Verify on both clusters
echo "=== DSE Count ==="
cqlsh dse-node1 -e "
SELECT COUNT(*) FROM training.users WHERE username LIKE 'zdm_bulk_user_%' ALLOW FILTERING;
"

echo "=== HCD Count ==="
cqlsh hcd-node1 -e "
SELECT COUNT(*) FROM training.users WHERE username LIKE 'zdm_bulk_user_%' ALLOW FILTERING;
"

# Exit container
exit
```

### Step 6: Monitor ZDM Proxy Metrics

```bash
# Check ZDM Proxy metrics
curl http://localhost:14001/metrics | grep -E "zdm_proxy_(requests|errors)"

# Key metrics to watch:
# - zdm_proxy_requests_total
# - zdm_proxy_errors_total
# - zdm_proxy_origin_requests_total
# - zdm_proxy_target_requests_total

# View in Prometheus
# Open browser: http://localhost:9090
# Query: rate(zdm_proxy_requests_total[5m])
```

## Part 3: Phase 2 - Read Migration

### Step 7: Configure Read Routing

For this lab, we'll simulate read routing by updating the ZDM Proxy configuration. In production, you would do this gradually.

```bash
# View current read mode
docker exec zdm-proxy cat /config/zdm-config.yml | grep -A 2 "read_mode"

# The proxy is configured with:
# read_mode: "PRIMARY_ONLY"
# primary_cluster: "ORIGIN"
# This means all reads go to DSE
```

### Step 8: Test Read Performance

```bash
# Access migration-tools container
docker exec -it migration-tools bash

# Create read performance test
cat > /scripts/test_read_performance.sh << 'EOF'
#!/bin/bash

echo "=== Read Performance Test ==="

# Test reads through proxy (currently from DSE)
echo "Testing reads through ZDM Proxy..."
START=$(date +%s%N)
for i in {1..100}; do
  cqlsh zdm-proxy 9042 -e "SELECT * FROM training.users LIMIT 10;" > /dev/null 2>&1
done
END=$(date +%s%N)
PROXY_TIME=$(( (END - START) / 1000000 ))
echo "ZDM Proxy (DSE): ${PROXY_TIME}ms for 100 queries"

# Test direct reads from DSE
echo "Testing direct reads from DSE..."
START=$(date +%s%N)
for i in {1..100}; do
  cqlsh dse-node1 -e "SELECT * FROM training.users LIMIT 10;" > /dev/null 2>&1
done
END=$(date +%s%N)
DSE_TIME=$(( (END - START) / 1000000 ))
echo "Direct DSE: ${DSE_TIME}ms for 100 queries"

# Test direct reads from HCD
echo "Testing direct reads from HCD..."
START=$(date +%s%N)
for i in {1..100}; do
  cqlsh hcd-node1 -e "SELECT * FROM training.users LIMIT 10;" > /dev/null 2>&1
done
END=$(date +%s%N)
HCD_TIME=$(( (END - START) / 1000000 ))
echo "Direct HCD: ${HCD_TIME}ms for 100 queries"

echo ""
echo "=== Performance Summary ==="
echo "ZDM Proxy overhead: $(( PROXY_TIME - DSE_TIME ))ms"
echo "HCD vs DSE: $(( HCD_TIME - DSE_TIME ))ms difference"
EOF

chmod +x /scripts/test_read_performance.sh
/scripts/test_read_performance.sh

exit
```

## Part 4: Phase 3 - Validation

### Step 9: Data Consistency Validation

```bash
# Access migration-tools container
docker exec -it migration-tools bash

# Create comprehensive validation script
cat > /scripts/validate_zdm_migration.py << 'EOF'
from cassandra.cluster import Cluster
import sys

def validate_consistency():
    print("=" * 60)
    print("ZDM Migration Consistency Validation")
    print("=" * 60)
    
    # Connect to both clusters
    dse = Cluster(['dse-node1']).connect('training')
    hcd = Cluster(['hcd-node1']).connect('training')
    
    tables = ['users', 'products', 'orders', 'user_activity']
    all_passed = True
    
    for table in tables:
        print(f"\nValidating table: {table}")
        
        # Count validation
        dse_count = dse.execute(f"SELECT COUNT(*) FROM {table}").one()[0]
        hcd_count = hcd.execute(f"SELECT COUNT(*) FROM {table}").one()[0]
        
        print(f"  DSE count: {dse_count:,}")
        print(f"  HCD count: {hcd_count:,}")
        
        if dse_count == hcd_count:
            print(f"  Count check: ✓ PASS")
        else:
            print(f"  Count check: ✗ FAIL (difference: {abs(dse_count - hcd_count)})")
            all_passed = False
            continue
        
        # Sample data validation
        print(f"  Validating sample data...")
        dse_sample = list(dse.execute(f"SELECT * FROM {table} LIMIT 100"))
        
        mismatches = 0
        for row in dse_sample:
            # Get primary key (assuming first column is PK for simplicity)
            pk_col = row._fields[0]
            pk_value = getattr(row, pk_col)
            
            # Query HCD
            hcd_result = hcd.execute(
                f"SELECT * FROM {table} WHERE {pk_col} = %s",
                [pk_value]
            )
            
            hcd_row = hcd_result.one()
            if hcd_row is None:
                mismatches += 1
        
        if mismatches == 0:
            print(f"  Sample check: ✓ PASS (100 rows validated)")
        else:
            print(f"  Sample check: ✗ FAIL ({mismatches} mismatches)")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All validation checks passed!")
        print("Clusters are consistent and ready for cutover")
    else:
        print("✗ Validation failed - investigate discrepancies")
    print("=" * 60)
    
    dse.shutdown()
    hcd.shutdown()
    
    return all_passed

if __name__ == "__main__":
    success = validate_consistency()
    sys.exit(0 if success else 1)
EOF

python3 /scripts/validate_zdm_migration.py

exit
```

### Step 10: Application Simulation

```bash
# Access migration-tools container
docker exec -it migration-tools bash

# Create application simulation script
cat > /scripts/simulate_app_traffic.py << 'EOF'
from cassandra.cluster import Cluster
import uuid
import random
import time
from datetime import datetime

# Connect through ZDM Proxy
cluster = Cluster(['zdm-proxy'], port=9042)
session = cluster.connect('training')

print("Simulating application traffic through ZDM Proxy...")
print("Press Ctrl+C to stop")
print()

try:
    iteration = 0
    while True:
        iteration += 1
        
        # Mix of reads and writes
        operation = random.choice(['read', 'read', 'read', 'write'])
        
        if operation == 'read':
            # Random read
            result = session.execute("SELECT * FROM users LIMIT 10")
            print(f"[{iteration}] Read: Retrieved {len(list(result))} users")
        else:
            # Random write
            user_id = uuid.uuid4()
            session.execute("""
                INSERT INTO users (user_id, username, email, status, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, f'app_user_{iteration}', f'app_{iteration}@test.com', 
                  'active', datetime.now()))
            print(f"[{iteration}] Write: Created user app_user_{iteration}")
        
        time.sleep(0.5)  # Simulate realistic traffic
        
except KeyboardInterrupt:
    print("\n\nStopping simulation...")
    print(f"Completed {iteration} operations")

cluster.shutdown()
EOF

# Run simulation (let it run for 30 seconds, then Ctrl+C)
timeout 30 python3 /scripts/simulate_app_traffic.py || true

exit
```

## Part 5: Monitoring and Metrics

### Step 11: Monitor ZDM Proxy

```bash
# View ZDM Proxy metrics
curl -s http://localhost:14001/metrics | grep -E "zdm_proxy" | head -20

# Check request distribution
echo "=== Request Distribution ==="
curl -s http://localhost:14001/metrics | grep "zdm_proxy_origin_requests_total"
curl -s http://localhost:14001/metrics | grep "zdm_proxy_target_requests_total"

# Check error rates
echo "=== Error Rates ==="
curl -s http://localhost:14001/metrics | grep "zdm_proxy_errors_total"
```

### Step 12: Monitor Cluster Health

```bash
# Check DSE cluster
echo "=== DSE Cluster Status ==="
docker exec dse-node1 nodetool status

# Check HCD cluster
echo "=== HCD Cluster Status ==="
docker exec hcd-node1 nodetool status

# Check compaction on HCD (should be active due to writes)
echo "=== HCD Compaction Status ==="
docker exec hcd-node1 nodetool compactionstats

# Check table statistics
echo "=== HCD Table Statistics ==="
docker exec hcd-node1 nodetool tablestats training.users | grep -E "Table:|Number of partitions|Memtable|Compacted"
```

### Step 13: Grafana Dashboard

```bash
# Access Grafana
# Open browser: http://localhost:3000
# Login: admin / admin

# Create dashboard for ZDM monitoring:
# 1. Add Prometheus data source (http://prometheus:9090)
# 2. Create panels for:
#    - Request rate: rate(zdm_proxy_requests_total[5m])
#    - Error rate: rate(zdm_proxy_errors_total[5m])
#    - Origin requests: rate(zdm_proxy_origin_requests_total[5m])
#    - Target requests: rate(zdm_proxy_target_requests_total[5m])
```

## Part 6: Cutover Simulation

### Step 14: Prepare for Cutover

```bash
# Final validation before cutover
docker exec -it migration-tools bash

# Run final consistency check
python3 /scripts/validate_zdm_migration.py

# Check cluster health
nodetool -h dse-node1 status
nodetool -h hcd-node1 status

# Verify no pending compactions
nodetool -h hcd-node1 compactionstats

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
# Access migration-tools container
docker exec -it migration-tools bash

# Test direct connection to HCD
cqlsh hcd-node1 -e "
SELECT cluster_name, release_version FROM system.local;
SELECT COUNT(*) FROM training.users;
"

# Verify all data is accessible
cqlsh hcd-node1 -e "
SELECT COUNT(*) FROM training.users;
SELECT COUNT(*) FROM training.products;
SELECT COUNT(*) FROM training.orders;
SELECT COUNT(*) FROM training.user_activity;
"

# Test application queries
cqlsh hcd-node1 -e "
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
cat lab/zdm-config/zdm-config.yml

# Check if clusters are accessible
docker exec migration-tools ping dse-node1
docker exec migration-tools ping hcd-node1

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
docker exec migration-tools cqlsh dse-node1 -e "SELECT COUNT(*) FROM training.users;"
docker exec migration-tools cqlsh hcd-node1 -e "SELECT COUNT(*) FROM training.users;"
```

### Issue: High latency through proxy

```bash
# Check proxy metrics
curl http://localhost:14001/metrics | grep duration

# Check cluster latency
docker exec dse-node1 nodetool proxyhistograms
docker exec hcd-node1 nodetool proxyhistograms

# Verify network
docker exec migration-tools ping -c 5 zdm-proxy
```

## Success Criteria

You have successfully completed this exercise when:

- ✅ ZDM Proxy is running and accessible
- ✅ Dual-write mode is working (writes go to both clusters)
- ✅ Data consistency validated between clusters
- ✅ Monitoring metrics are available
- ✅ Application simulation runs successfully
- ✅ Ready for production cutover

## Key Takeaways

1. **Zero Downtime**: ZDM Proxy enables true zero-downtime migration
2. **Dual-Write**: All writes automatically go to both clusters
3. **Gradual Migration**: Read traffic can be shifted gradually
4. **Monitoring**: Comprehensive metrics for tracking migration
5. **Validation**: Continuous validation ensures data consistency
6. **Rollback**: Easy to rollback by changing proxy configuration

## Next Steps

Proceed to [Exercise 5: Validation and Monitoring](05-validation-monitoring.md) for comprehensive validation techniques and monitoring setup.

## Clean Up

```bash
# Stop ZDM Proxy
docker-compose stop zdm-proxy

# Remove test data
docker exec hcd-node1 cqlsh -e "
DELETE FROM training.users WHERE username LIKE 'zdm_%' ALLOW FILTERING;
DELETE FROM training.users WHERE username LIKE 'app_user_%' ALLOW FILTERING;
"

# Restart ZDM Proxy
docker-compose start zdm-proxy
```

---

**Time to Complete:** 60-90 minutes  
**Difficulty:** Advanced  
**Next Exercise:** [Validation and Monitoring](05-validation-monitoring.md)