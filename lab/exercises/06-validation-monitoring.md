# Exercise 6: Validation and Monitoring

## Objectives

- Implement comprehensive data validation
- Set up monitoring dashboards
- Create automated validation scripts
- Monitor cluster health and performance
- Establish alerting for migration issues

## Prerequisites

- Completed Exercises 1-5
- Both clusters running with data
- Monitoring stack (Prometheus/Grafana) running

**Note:** This exercise assumes you are working from the `lab` directory. If starting fresh, run `cd lab` from the project root.

## Duration

45-60 minutes

## Overview

This exercise focuses on validation and monitoring techniques essential for ensuring a successful migration. You'll learn to validate data integrity, monitor cluster health, and set up alerts for potential issues.

## Part 1: Data Validation

### Step 1: Row Count Validation

```bash
# Access tools container
docker exec -it tools bash

# Create comprehensive row count validation script
cat > /scripts/validate_row_counts.sh << 'EOF'
#!/bin/bash

KEYSPACE="training"
TABLES=("users" "products" "orders" "user_activity")

echo "=========================================="
echo "Row Count Validation Report"
echo "Generated: $(date)"
echo "=========================================="
echo ""

TOTAL_MISMATCHES=0

for TABLE in "${TABLES[@]}"; do
  echo "Table: $KEYSPACE.$TABLE"
  
  # Get counts from both clusters
  DSE_COUNT=$(cqlsh dse-node -e "SELECT COUNT(*) FROM $KEYSPACE.$TABLE;" 2>/dev/null | grep -oP '\d+' | head -1)
  HCD_COUNT=$(cqlsh hcd-node -e "SELECT COUNT(*) FROM $KEYSPACE.$TABLE;" 2>/dev/null | grep -oP '\d+' | head -1)
  
  echo "  DSE: $DSE_COUNT rows"
  echo "  HCD: $HCD_COUNT rows"
  
  if [ "$DSE_COUNT" -eq "$HCD_COUNT" ]; then
    echo "  Status: ✓ PASS"
  else
    DIFF=$((DSE_COUNT - HCD_COUNT))
    echo "  Status: ✗ FAIL (difference: $DIFF)"
    TOTAL_MISMATCHES=$((TOTAL_MISMATCHES + 1))
  fi
  echo ""
done

echo "=========================================="
if [ $TOTAL_MISMATCHES -eq 0 ]; then
  echo "✓ All tables validated successfully!"
  exit 0
else
  echo "✗ $TOTAL_MISMATCHES table(s) have mismatches"
  exit 1
fi
EOF

chmod +x /scripts/validate_row_counts.sh
/scripts/validate_row_counts.sh
```

### Step 2: Sample Data Validation

```bash
# Still in tools container

# Create sample data validation script
cat > /scripts/validate_sample_data.py << 'EOF'
from cassandra.cluster import Cluster
import sys
import hashlib

def hash_row(row):
    """Create hash of row data for comparison"""
    row_str = str(sorted([(k, v) for k, v in row._asdict().items()]))
    return hashlib.md5(row_str.encode()).hexdigest()

def validate_table_sample(keyspace, table, sample_size=100):
    """Validate sample data between clusters"""
    print(f"\nValidating {keyspace}.{table} (sample size: {sample_size})")
    
    # Connect to both clusters
    dse = Cluster(['dse-node']).connect(keyspace)
    hcd = Cluster(['hcd-node']).connect(keyspace)
    
    # Get sample from DSE
    dse_rows = list(dse.execute(f"SELECT * FROM {table} LIMIT {sample_size}"))
    
    if not dse_rows:
        print(f"  No data in table")
        return True
    
    # Get primary key column name (first column)
    pk_column = dse_rows[0]._fields[0]
    
    mismatches = 0
    missing = 0
    
    for dse_row in dse_rows:
        pk_value = getattr(dse_row, pk_column)
        
        # Query HCD for same row
        hcd_result = hcd.execute(
            f"SELECT * FROM {table} WHERE {pk_column} = %s",
            [pk_value]
        )
        
        hcd_row = hcd_result.one()
        
        if hcd_row is None:
            missing += 1
            print(f"  Missing in HCD: {pk_column}={pk_value}")
        elif hash_row(dse_row) != hash_row(hcd_row):
            mismatches += 1
            print(f"  Data mismatch: {pk_column}={pk_value}")
    
    # Summary
    validated = len(dse_rows) - missing - mismatches
    print(f"  Validated: {validated}/{len(dse_rows)}")
    print(f"  Missing: {missing}")
    print(f"  Mismatches: {mismatches}")
    
    success = (missing == 0 and mismatches == 0)
    print(f"  Status: {'✓ PASS' if success else '✗ FAIL'}")
    
    dse.shutdown()
    hcd.shutdown()
    
    return success

def main():
    tables = ['users', 'products', 'orders', 'user_activity']
    
    print("=" * 60)
    print("Sample Data Validation Report")
    print("=" * 60)
    
    all_passed = True
    for table in tables:
        if not validate_table_sample('training', table, 100):
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All sample validations passed!")
    else:
        print("✗ Some validations failed")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
EOF

python3 /scripts/validate_sample_data.py
```

### Step 3: Schema Validation

```bash
# Still in tools container

# Create schema validation script
cat > /scripts/validate_schema.sh << 'EOF'
#!/bin/bash

KEYSPACE="training"

echo "=========================================="
echo "Schema Validation Report"
echo "=========================================="
echo ""

# Export schemas
echo "Exporting schemas..."
cqlsh dse-node -e "DESC KEYSPACE $KEYSPACE" > /tmp/dse_schema.cql 2>/dev/null
cqlsh hcd-node -e "DESC KEYSPACE $KEYSPACE" > /tmp/hcd_schema.cql 2>/dev/null

# Normalize schemas (remove datacenter-specific settings)
sed 's/dc1/datacenter1/g' /tmp/dse_schema.cql | \
  grep -v "^$" | \
  sort > /tmp/dse_schema_normalized.cql

sed 's/datacenter1/datacenter1/g' /tmp/hcd_schema.cql | \
  grep -v "^$" | \
  sort > /tmp/hcd_schema_normalized.cql

# Compare
echo "Comparing schemas..."
if diff -u /tmp/dse_schema_normalized.cql /tmp/hcd_schema_normalized.cql > /tmp/schema_diff.txt; then
  echo "✓ Schemas match"
  echo ""
else
  echo "✗ Schema differences found:"
  echo ""
  cat /tmp/schema_diff.txt
  echo ""
fi

# List tables
echo "Tables in DSE:"
cqlsh dse-node -e "DESC TABLES" 2>/dev/null | grep training

echo ""
echo "Tables in HCD:"
cqlsh hcd-node -e "DESC TABLES" 2>/dev/null | grep training

echo ""
echo "=========================================="
EOF

chmod +x /scripts/validate_schema.sh
/scripts/validate_schema.sh

exit
```

## Part 2: Performance Monitoring

### Step 4: Cluster Health Monitoring

```bash
# Create cluster health monitoring script
docker exec -it tools bash

cat > /scripts/monitor_cluster_health.sh << 'EOF'
#!/bin/bash

echo "=========================================="
echo "Cluster Health Monitoring"
echo "Timestamp: $(date)"
echo "=========================================="

# DSE Cluster
echo ""
echo "=== DSE Cluster ==="
echo "Status:"
docker exec dse-node nodetool status 2>/dev/null | grep -E "^(UN|DN)"

echo ""
echo "Info:"
docker exec dse-node nodetool info 2>/dev/null | grep -E "Load|Heap|Uptime"

echo ""
echo "Thread Pools:"
docker exec dse-node nodetool tpstats 2>/dev/null | grep -E "Pool Name|ReadStage|MutationStage" | head -4

# HCD Cluster
echo ""
echo "=== HCD Cluster ==="
echo "Status:"
docker exec hcd-node nodetool status 2>/dev/null | grep -E "^(UN|DN)"

echo ""
echo "Info:"
docker exec hcd-node nodetool info 2>/dev/null | grep -E "Load|Heap|Uptime"

echo ""
echo "Thread Pools:"
docker exec hcd-node nodetool tpstats 2>/dev/null | grep -E "Pool Name|ReadStage|MutationStage" | head -4

echo ""
echo "=========================================="
EOF

chmod +x /scripts/monitor_cluster_health.sh
/scripts/monitor_cluster_health.sh
```

### Step 5: Performance Metrics Collection

```bash
# Still in tools container

cat > /scripts/collect_performance_metrics.sh << 'EOF'
#!/bin/bash

OUTPUT_DIR="/exports/metrics"
mkdir -p $OUTPUT_DIR

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Collecting performance metrics..."

# DSE Metrics
echo "=== DSE Metrics ===" > $OUTPUT_DIR/dse_metrics_$TIMESTAMP.txt
docker exec dse-node nodetool tablestats training >> $OUTPUT_DIR/dse_metrics_$TIMESTAMP.txt 2>&1
docker exec dse-node nodetool proxyhistograms >> $OUTPUT_DIR/dse_metrics_$TIMESTAMP.txt 2>&1

# HCD Metrics
echo "=== HCD Metrics ===" > $OUTPUT_DIR/hcd_metrics_$TIMESTAMP.txt
docker exec hcd-node nodetool tablestats training >> $OUTPUT_DIR/hcd_metrics_$TIMESTAMP.txt 2>&1
docker exec hcd-node nodetool proxyhistograms >> $OUTPUT_DIR/hcd_metrics_$TIMESTAMP.txt 2>&1

echo "Metrics saved to $OUTPUT_DIR/"
ls -lh $OUTPUT_DIR/*$TIMESTAMP*
EOF

chmod +x /scripts/collect_performance_metrics.sh
/scripts/collect_performance_metrics.sh

exit
```

## Part 3: Monitoring Dashboard Setup

### Step 6: Configure Prometheus

```bash
# Verify Prometheus is scraping metrics
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

# Check if ZDM Proxy metrics are available
curl http://localhost:9090/api/v1/query?query=zdm_proxy_requests_total | jq '.data.result'
```

### Step 7: Access Pre-configured Grafana Dashboards

The lab environment includes three pre-configured Grafana dashboards from the [ZDM Proxy Automation repository](https://github.com/datastax/zdm-proxy-automation/tree/main/grafana-dashboards):

1. **ZDM Proxy Dashboard** - Main monitoring dashboard for ZDM operations
2. **ZDM Go Runtime Metrics** - Go runtime metrics for the proxy
3. **Node Exporter Full** - System-level metrics (requires node-exporter)

```bash
# Access Grafana: http://localhost:3000
# Login: admin / admin

# Navigate to: Dashboards → ZDM Migration folder

# The following dashboards are automatically provisioned:
# - ZDM Proxy Dashboard v1
# - ZDM Go Runtime Metrics v1
# - Node Exporter Full

# Key metrics to monitor:
# - Request rates and latencies
# - Read/write routing (Origin vs Target)
# - Error rates and types
# - Connection pool statistics
# - Dual write performance
# - Memory and CPU usage
```

**Dashboard Features:**

**ZDM Proxy Dashboard** monitors:
- Total request rate
- Read vs Write operations
- Origin (DSE) vs Target (HCD) routing
- Error rates by type
- Latency percentiles (p50, p95, p99)
- Async read performance
- Connection pool health

**ZDM Go Runtime Metrics** tracks:
- Memory usage and GC statistics
- Goroutine counts
- Heap allocations
- GC pause times
- CPU usage

For more details, see [`../monitoring/README.md`](../monitoring/README.md).

### Step 8: Verify Dashboard Data

```bash
# Check that dashboards are receiving data
# In Grafana UI, verify:
# 1. Prometheus datasource is connected (green indicator)
# 2. Panels show data (not "No data")
# 3. Time range is appropriate (Last 15 minutes)

# If no data appears, check ZDM Proxy metrics endpoint:
curl http://localhost:14001/metrics | grep zdm_proxy

# Verify Prometheus is scraping:
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="zdm-proxy")'
```

## Part 4: Automated Validation

### Step 9: Continuous Validation Script

```bash
# Access tools container
docker exec -it tools bash

cat > /scripts/continuous_validation.sh << 'EOF'
#!/bin/bash

INTERVAL=60  # Check every 60 seconds
LOG_FILE="/exports/logs/continuous_validation.log"

mkdir -p /exports/logs

echo "Starting continuous validation (interval: ${INTERVAL}s)"
echo "Log file: $LOG_FILE"
echo "Press Ctrl+C to stop"
echo ""

while true; do
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
  echo "[$TIMESTAMP] Running validation..." | tee -a $LOG_FILE
  
  # Run validation
  /scripts/validate_row_counts.sh >> $LOG_FILE 2>&1
  
  if [ $? -eq 0 ]; then
    echo "[$TIMESTAMP] ✓ Validation passed" | tee -a $LOG_FILE
  else
    echo "[$TIMESTAMP] ✗ Validation failed - check log" | tee -a $LOG_FILE
  fi
  
  sleep $INTERVAL
done
EOF

chmod +x /scripts/continuous_validation.sh

# Run in background (for demo, run for 5 minutes)
timeout 300 /scripts/continuous_validation.sh &

# Check logs
tail -f /exports/logs/continuous_validation.log

exit
```

### Step 10: Alerting Configuration

```bash
# Create alerting rules for Prometheus
cat > monitoring/prometheus-alerts.yml << 'EOF'
groups:
  - name: migration_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(zdm_proxy_errors_total[5m]) > 10
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate in ZDM Proxy"
          description: "Error rate is {{ $value }} errors/sec"
      
      - alert: DataCountMismatch
        expr: abs(dse_row_count - hcd_row_count) > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Row count mismatch detected"
          description: "Difference: {{ $value }} rows"
      
      - alert: HighLatency
        expr: histogram_quantile(0.99, rate(zdm_proxy_requests_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "P99 latency: {{ $value }}s"
      
      - alert: ClusterDown
        expr: up{job="cassandra"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Cassandra node is down"
          description: "Node {{ $labels.instance }} is unreachable"
EOF

echo "Alert rules created"
```

## Part 5: Comprehensive Validation Report

### Step 11: Generate Migration Report

```bash
# Access tools container
docker exec -it tools bash

cat > /scripts/generate_migration_report.sh << 'EOF'
#!/bin/bash

REPORT_FILE="/exports/migration_report_$(date +%Y%m%d_%H%M%S).txt"

cat > $REPORT_FILE << 'REPORT'
========================================
DSE to HCD Migration Report
========================================
Generated: $(date)

1. CLUSTER STATUS
========================================

DSE Cluster:
$(docker exec dse-node nodetool status 2>/dev/null)

HCD Cluster:
$(docker exec hcd-node nodetool status 2>/dev/null)

2. DATA VALIDATION
========================================

Row Counts:
$(bash /scripts/validate_row_counts.sh 2>&1)

3. PERFORMANCE METRICS
========================================

DSE Performance:
$(docker exec dse-node nodetool tablestats training 2>/dev/null | grep -A 5 "Table: users")

HCD Performance:
$(docker exec hcd-node nodetool tablestats training 2>/dev/null | grep -A 5 "Table: users")

4. ZDM PROXY METRICS
========================================

$(curl -s http://zdm-proxy:14001/metrics 2>/dev/null | grep -E "zdm_proxy_(requests|errors)_total")

5. RECOMMENDATIONS
========================================

- Review any validation failures above
- Monitor cluster health continuously
- Verify application connectivity
- Plan cutover window
- Prepare rollback procedure

========================================
End of Report
========================================
REPORT

echo "Migration report generated: $REPORT_FILE"
cat $REPORT_FILE
EOF

chmod +x /scripts/generate_migration_report.sh
/scripts/generate_migration_report.sh

exit
```

## Troubleshooting

### Issue: Validation failures

```bash
# Check for replication lag
docker exec dse-node nodetool repair training
docker exec hcd-node nodetool repair training

# Re-run validation
docker exec tools /scripts/validate_row_counts.sh
```

### Issue: Prometheus not scraping

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Restart Prometheus
docker-compose restart prometheus

# Check logs
docker logs prometheus
```

### Issue: Grafana dashboard not showing data

```bash
# Verify Prometheus data source
curl http://localhost:3000/api/datasources

# Check Prometheus connectivity from Grafana
docker exec grafana wget -O- http://prometheus:9090/api/v1/query?query=up
```

## Success Criteria

You have successfully completed this exercise when:

- ✅ Row count validation passes for all tables
- ✅ Sample data validation shows no mismatches
- ✅ Schema validation confirms compatibility
- ✅ Monitoring dashboards are operational
- ✅ Automated validation scripts are running
- ✅ Migration report generated successfully

## Key Takeaways

1. **Validation**: Multiple validation layers ensure data integrity
2. **Monitoring**: Continuous monitoring catches issues early
3. **Automation**: Automated scripts reduce manual effort
4. **Metrics**: Comprehensive metrics guide decision-making
5. **Reporting**: Regular reports document migration progress

## Next Steps

You have completed all lab exercises! You now have:
- Hands-on experience with multiple migration tools
- Understanding of zero-downtime migration
- Validation and monitoring skills
- Production-ready migration scripts

## Clean Up

```bash
# Stop continuous validation
pkill -f continuous_validation

# Archive reports
docker exec tools tar -czf /exports/migration_reports.tar.gz /exports/*.txt

# Optional: Reset environment
cd lab
docker-compose down -v
```

---

**Time to Complete:** 45-60 minutes  
**Difficulty:** Advanced  
**Congratulations!** You've completed the DSE to HCD migration training!