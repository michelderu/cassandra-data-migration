# Exercise 3: DSBulk Migration

## Objectives

- Install and configure DSBulk
- Export data from DSE using DSBulk
- Import data to HCD using DSBulk
- Compare DSBulk performance with native tools
- Handle large datasets efficiently

## Prerequisites

- Completed Exercise 1 and 2
- DSE cluster with sample data
- HCD cluster with schema created

## Duration

45-60 minutes

## Overview

DSBulk (DataStax Bulk Loader) is a high-performance tool for loading and unloading data. It's significantly faster than the native COPY command and handles large datasets efficiently.

## Part 1: DSBulk Setup

### Step 1: Verify DSBulk Installation

```bash
# Access migration-tools container (DSBulk should be pre-installed)
docker exec -it migration-tools bash

# Verify DSBulk is available
which dsbulk
dsbulk --version

# Expected output: DataStax Bulk Loader v1.10.0 or similar

# If not installed, install it:
# cd /tmp
# wget https://downloads.datastax.com/dsbulk/dsbulk-1.10.0.tar.gz
# tar -xzf dsbulk-1.10.0.tar.gz
# export PATH=$PATH:/tmp/dsbulk-1.10.0/bin
```

### Step 2: Create DSBulk Configuration

```bash
# Still in migration-tools container

# Create configuration directory
mkdir -p /config/dsbulk

# Create base configuration file
cat > /config/dsbulk/dsbulk.conf << 'EOF'
dsbulk {
  connector {
    name = csv
    csv {
      header = true
      delimiter = ","
      maxConcurrentFiles = 4
    }
  }
  
  executor {
    maxPerSecond = 10000
    maxInFlight = 1024
  }
  
  driver {
    query {
      consistency = LOCAL_QUORUM
    }
    socket {
      readTimeout = 60 seconds
    }
  }
  
  batch {
    mode = PARTITION_KEY
    maxBatchSize = 32
  }
  
  log {
    directory = "/exports/logs"
    verbosity = 1
  }
}
EOF

# Create log directory
mkdir -p /exports/logs
```

## Part 2: Export Data from DSE

### Step 3: Export Users Table

```bash
# Still in migration-tools container

# Create export directory
mkdir -p /exports/dsbulk

# Export users table
dsbulk unload \
  -h dse-node1 \
  -k training \
  -t users \
  -url /exports/dsbulk/users \
  -f /config/dsbulk/dsbulk.conf

# Check export
ls -lh /exports/dsbulk/users/
wc -l /exports/dsbulk/users/*.csv
```

**Expected Output:**
```
Exported 1,000 rows from training.users
Files created in /exports/dsbulk/users/
```

### Step 4: Export All Tables

```bash
# Export products
dsbulk unload \
  -h dse-node1 \
  -k training \
  -t products \
  -url /exports/dsbulk/products \
  -f /config/dsbulk/dsbulk.conf

# Export orders
dsbulk unload \
  -h dse-node1 \
  -k training \
  -t orders \
  -url /exports/dsbulk/orders \
  -f /config/dsbulk/dsbulk.conf

# Export user_activity
dsbulk unload \
  -h dse-node1 \
  -k training \
  -t user_activity \
  -url /exports/dsbulk/user_activity \
  -f /config/dsbulk/dsbulk.conf

# Verify all exports
du -sh /exports/dsbulk/*
```

### Step 5: Export with Custom Query

```bash
# Export only active users
dsbulk unload \
  -h dse-node1 \
  -k training \
  -url /exports/dsbulk/active_users \
  --schema.query "SELECT user_id, username, email, status FROM training.users WHERE status = 'active' ALLOW FILTERING" \
  -f /config/dsbulk/dsbulk.conf

# Export recent orders (last 30 days simulation)
dsbulk unload \
  -h dse-node1 \
  -k training \
  -url /exports/dsbulk/recent_orders \
  --schema.query "SELECT * FROM training.orders LIMIT 500" \
  -f /config/dsbulk/dsbulk.conf
```

## Part 3: Import Data to HCD

### Step 6: Import Users Table

```bash
# Import users to HCD
dsbulk load \
  -h hcd-node1 \
  -k training \
  -t users \
  -url /exports/dsbulk/users \
  -f /config/dsbulk/dsbulk.conf

# Verify import
cqlsh hcd-node1 -e "SELECT COUNT(*) FROM training.users;"
```

### Step 7: Import All Tables

```bash
# Import products
dsbulk load \
  -h hcd-node1 \
  -k training \
  -t products \
  -url /exports/dsbulk/products \
  -f /config/dsbulk/dsbulk.conf

# Import orders
dsbulk load \
  -h hcd-node1 \
  -k training \
  -t orders \
  -url /exports/dsbulk/orders \
  -f /config/dsbulk/dsbulk.conf

# Import user_activity
dsbulk load \
  -h hcd-node1 \
  -k training \
  -t user_activity \
  -url /exports/dsbulk/user_activity \
  -f /config/dsbulk/dsbulk.conf

# Verify all imports
cqlsh hcd-node1 -e "
SELECT COUNT(*) FROM training.users;
SELECT COUNT(*) FROM training.products;
SELECT COUNT(*) FROM training.orders;
SELECT COUNT(*) FROM training.user_activity;
"
```

## Part 4: Advanced DSBulk Features

### Step 8: Export with Compression

```bash
# Export with gzip compression
dsbulk unload \
  -h dse-node1 \
  -k training \
  -t user_activity \
  -url /exports/dsbulk/user_activity_compressed \
  --connector.csv.compression gzip \
  -f /config/dsbulk/dsbulk.conf

# Compare file sizes
ls -lh /exports/dsbulk/user_activity/*.csv
ls -lh /exports/dsbulk/user_activity_compressed/*.csv.gz

# Import compressed data
dsbulk load \
  -h hcd-node1 \
  -k training \
  -t user_activity \
  -url /exports/dsbulk/user_activity_compressed \
  --connector.csv.compression gzip \
  -f /config/dsbulk/dsbulk.conf
```

### Step 9: Parallel Processing

```bash
# Export with increased parallelism
dsbulk unload \
  -h dse-node1 \
  -k training \
  -t user_activity \
  -url /exports/dsbulk/user_activity_parallel \
  --connector.csv.maxConcurrentFiles 8 \
  --executor.maxPerSecond 50000 \
  -f /config/dsbulk/dsbulk.conf

# Import with high performance settings
dsbulk load \
  -h hcd-node1,hcd-node2,hcd-node3 \
  -k training \
  -t user_activity \
  -url /exports/dsbulk/user_activity_parallel \
  --connector.csv.maxConcurrentFiles 8 \
  --executor.maxPerSecond 50000 \
  --executor.maxInFlight 2048 \
  -f /config/dsbulk/dsbulk.conf
```

### Step 10: Error Handling and Dry Run

```bash
# Dry run to test without loading
dsbulk load \
  -h hcd-node1 \
  -k training \
  -t users \
  -url /exports/dsbulk/users \
  --dryRun true \
  -f /config/dsbulk/dsbulk.conf

# Load with error handling
dsbulk load \
  -h hcd-node1 \
  -k training \
  -t users \
  -url /exports/dsbulk/users \
  --executor.maxErrors 100 \
  --executor.maxErrorRatio 0.01 \
  --log.directory /exports/logs/users_import \
  -f /config/dsbulk/dsbulk.conf

# Check logs for errors
cat /exports/logs/users_import/operation.log
```

## Part 5: Performance Benchmarking

### Step 11: Benchmark Export Performance

```bash
# Create benchmark script
cat > /scripts/benchmark_export.sh << 'EOF'
#!/bin/bash

echo "=== DSBulk Export Benchmark ==="
echo "Starting: $(date)"

# Benchmark user_activity table (5000 rows)
START=$(date +%s)

dsbulk unload \
  -h dse-node1 \
  -k training \
  -t user_activity \
  -url /exports/dsbulk/benchmark_export \
  --connector.csv.maxConcurrentFiles 8 \
  --executor.maxPerSecond 50000 \
  -f /config/dsbulk/dsbulk.conf

END=$(date +%s)
DURATION=$((END - START))

echo "Completed: $(date)"
echo "Duration: ${DURATION} seconds"
echo "Rows: 5000"
echo "Throughput: $((5000 / DURATION)) rows/sec"
EOF

chmod +x /scripts/benchmark_export.sh
/scripts/benchmark_export.sh
```

### Step 12: Benchmark Import Performance

```bash
# Create benchmark script
cat > /scripts/benchmark_import.sh << 'EOF'
#!/bin/bash

echo "=== DSBulk Import Benchmark ==="
echo "Starting: $(date)"

# Clear target table
cqlsh hcd-node1 -e "TRUNCATE training.user_activity;"

# Benchmark import
START=$(date +%s)

dsbulk load \
  -h hcd-node1,hcd-node2,hcd-node3 \
  -k training \
  -t user_activity \
  -url /exports/dsbulk/benchmark_export \
  --connector.csv.maxConcurrentFiles 8 \
  --executor.maxPerSecond 50000 \
  --executor.maxInFlight 2048 \
  -f /config/dsbulk/dsbulk.conf

END=$(date +%s)
DURATION=$((END - START))

echo "Completed: $(date)"
echo "Duration: ${DURATION} seconds"
echo "Rows: 5000"
echo "Throughput: $((5000 / DURATION)) rows/sec"

# Verify
COUNT=$(cqlsh hcd-node1 -e "SELECT COUNT(*) FROM training.user_activity;" | grep -oP '\d+' | head -1)
echo "Verified count: $COUNT"
EOF

chmod +x /scripts/benchmark_import.sh
/scripts/benchmark_import.sh
```

## Part 6: Complete Migration Script

### Step 13: Create Automated Migration Script

```bash
# Create comprehensive migration script
cat > /scripts/migrate_with_dsbulk.sh << 'EOF'
#!/bin/bash

set -e

KEYSPACE="training"
TABLES=("users" "products" "orders" "user_activity")
DSE_HOST="dse-node1"
HCD_HOSTS="hcd-node1,hcd-node2,hcd-node3"
EXPORT_DIR="/exports/dsbulk"
LOG_DIR="/exports/logs"

echo "=========================================="
echo "DSE to HCD Migration using DSBulk"
echo "=========================================="
echo "Start time: $(date)"
echo ""

# Create directories
mkdir -p $EXPORT_DIR $LOG_DIR

# Export schema
echo "Exporting schema..."
cqlsh $DSE_HOST -e "DESC KEYSPACE $KEYSPACE" > $EXPORT_DIR/schema.cql

# Migrate each table
for TABLE in "${TABLES[@]}"; do
  echo ""
  echo "=========================================="
  echo "Migrating table: $TABLE"
  echo "=========================================="
  
  # Get source count
  echo "Getting source row count..."
  DSE_COUNT=$(cqlsh $DSE_HOST -e "SELECT COUNT(*) FROM $KEYSPACE.$TABLE;" | grep -oP '\d+' | head -1)
  echo "Source rows: $DSE_COUNT"
  
  # Export
  echo "Exporting from DSE..."
  dsbulk unload \
    -h $DSE_HOST \
    -k $KEYSPACE \
    -t $TABLE \
    -url $EXPORT_DIR/$TABLE \
    --connector.csv.maxConcurrentFiles 8 \
    --executor.maxPerSecond 50000 \
    --log.directory $LOG_DIR/unload_$TABLE \
    -f /config/dsbulk/dsbulk.conf
  
  # Import
  echo "Importing to HCD..."
  dsbulk load \
    -h $HCD_HOSTS \
    -k $KEYSPACE \
    -t $TABLE \
    -url $EXPORT_DIR/$TABLE \
    --connector.csv.maxConcurrentFiles 8 \
    --executor.maxPerSecond 50000 \
    --executor.maxInFlight 2048 \
    --log.directory $LOG_DIR/load_$TABLE \
    -f /config/dsbulk/dsbulk.conf
  
  # Verify
  echo "Verifying migration..."
  HCD_COUNT=$(cqlsh hcd-node1 -e "SELECT COUNT(*) FROM $KEYSPACE.$TABLE;" | grep -oP '\d+' | head -1)
  echo "Target rows: $HCD_COUNT"
  
  if [ "$DSE_COUNT" -eq "$HCD_COUNT" ]; then
    echo "✓ Table $TABLE migrated successfully"
  else
    echo "✗ Row count mismatch for table $TABLE"
    echo "  DSE: $DSE_COUNT, HCD: $HCD_COUNT"
    exit 1
  fi
done

echo ""
echo "=========================================="
echo "Migration Complete!"
echo "=========================================="
echo "End time: $(date)"
EOF

chmod +x /scripts/migrate_with_dsbulk.sh

# Run the migration
/scripts/migrate_with_dsbulk.sh

# Exit container
exit
```

## Part 7: Validation and Monitoring

### Step 14: Validate Migration

```bash
# Access migration-tools container
docker exec -it migration-tools bash

# Run comprehensive validation
cat > /scripts/validate_dsbulk_migration.py << 'EOF'
from cassandra.cluster import Cluster
import sys

def validate_migration():
    tables = ['users', 'products', 'orders', 'user_activity']
    
    dse = Cluster(['dse-node1']).connect('training')
    hcd = Cluster(['hcd-node1']).connect('training')
    
    print("=" * 50)
    print("DSBulk Migration Validation Report")
    print("=" * 50)
    
    all_passed = True
    
    for table in tables:
        print(f"\nTable: {table}")
        
        # Count validation
        dse_count = dse.execute(f"SELECT COUNT(*) FROM {table}").one()[0]
        hcd_count = hcd.execute(f"SELECT COUNT(*) FROM {table}").one()[0]
        
        print(f"  DSE count: {dse_count:,}")
        print(f"  HCD count: {hcd_count:,}")
        
        if dse_count == hcd_count:
            print(f"  Status: ✓ PASS")
        else:
            print(f"  Status: ✗ FAIL")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("All tables validated successfully!")
    else:
        print("Validation failed for some tables")
    print("=" * 50)
    
    dse.shutdown()
    hcd.shutdown()
    
    return all_passed

if __name__ == "__main__":
    success = validate_migration()
    sys.exit(0 if success else 1)
EOF

python3 /scripts/validate_dsbulk_migration.py

exit
```

### Step 15: Monitor HCD Cluster

```bash
# Check HCD cluster health
docker exec hcd-node1 nodetool status

# Check table statistics
docker exec hcd-node1 nodetool tablestats training

# Check compaction
docker exec hcd-node1 nodetool compactionstats

# Check if repair is needed
docker exec hcd-node1 nodetool repair training
```

## Troubleshooting

### Issue: Connection timeout

```bash
# Increase timeout in configuration
cat > /config/dsbulk/dsbulk-timeout.conf << 'EOF'
dsbulk {
  driver {
    advanced {
      connection {
        init-query-timeout = "30 seconds"
        set-keyspace-timeout = "30 seconds"
      }
    }
    socket {
      readTimeout = "120 seconds"
    }
  }
}
EOF

# Use with timeout config
dsbulk load \
  -h hcd-node1 \
  -k training \
  -t users \
  -url /exports/dsbulk/users \
  -f /config/dsbulk/dsbulk-timeout.conf
```

### Issue: Out of memory

```bash
# Reduce batch size and concurrency
dsbulk load \
  -h hcd-node1 \
  -k training \
  -t users \
  -url /exports/dsbulk/users \
  --executor.maxPerSecond 1000 \
  --connector.csv.maxConcurrentFiles 2 \
  --executor.maxInFlight 512
```

### Issue: Data format errors

```bash
# Check CSV format
head -n 5 /exports/dsbulk/users/*.csv

# Validate with dry run
dsbulk load \
  -h hcd-node1 \
  -k training \
  -t users \
  -url /exports/dsbulk/users \
  --dryRun true

# Check error logs
tail -f /exports/logs/operation.log
```

## Performance Comparison

### DSBulk vs COPY Command

| Metric | COPY | DSBulk | Improvement |
|--------|------|--------|-------------|
| 1K rows | ~30s | ~5s | 6x faster |
| 10K rows | ~5min | ~30s | 10x faster |
| 100K rows | ~50min | ~5min | 10x faster |
| Parallelism | Single | Multi | N/A |
| Memory | High | Optimized | Better |
| Error handling | Basic | Advanced | Better |

## Success Criteria

You have successfully completed this exercise when:

- ✅ DSBulk is installed and configured
- ✅ Exported all tables from DSE
- ✅ Imported all tables to HCD
- ✅ Row counts match between clusters
- ✅ Performance benchmarks completed
- ✅ Validation passed

## Key Takeaways

1. **Performance**: DSBulk is 6-10x faster than COPY
2. **Scalability**: Handles large datasets efficiently
3. **Flexibility**: Supports compression, filtering, and custom queries
4. **Error Handling**: Robust error handling and logging
5. **Production Ready**: Suitable for production migrations

## Next Steps

Proceed to [Exercise 4: ZDM Proxy Migration](04-zdm-migration.md) to learn about zero-downtime migration using ZDM Proxy.

## Clean Up

```bash
# Remove export files
docker exec migration-tools rm -rf /exports/dsbulk/*

# Remove logs
docker exec migration-tools rm -rf /exports/logs/*

# Truncate HCD tables if needed
docker exec hcd-node1 cqlsh -e "
TRUNCATE training.users;
TRUNCATE training.products;
TRUNCATE training.orders;
TRUNCATE training.user_activity;
"
```

---

**Time to Complete:** 45-60 minutes  
**Difficulty:** Intermediate  
**Next Exercise:** [ZDM Proxy Migration](04-zdm-migration.md)