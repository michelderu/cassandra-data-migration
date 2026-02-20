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

**Note:** This exercise assumes you are working from the `lab` directory. If starting fresh, run `cd lab` from the project root.

## Duration

45-60 minutes

## Overview

DSBulk (DataStax Bulk Loader) is a high-performance tool for loading and unloading data. It's significantly faster than the native COPY command and handles large datasets efficiently.

## Part 1: DSBulk Setup

### Step 0: Ensure HCD Target is cleared
```bash
docker exec hcd-node cqlsh -e "
TRUNCATE training.users;
TRUNCATE training.products;
TRUNCATE training.orders;
TRUNCATE training.user_activity
"
```

### Step 1: Verify DSBulk Installation

```bash
# Access tools container (DSBulk should be pre-installed)
docker exec -it tools bash

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
# Still in tools container

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
  
  batch {
    mode = PARTITION_KEY
    maxBatchStatements = 32
  }
  
  log {
    directory = "/exports/logs"
    verbosity = normal
  }
}
EOF

# Create log directory
mkdir -p /exports/logs
```

## Part 2: Export Data from DSE

### Step 3: Export Users Table

```bash
# Still in tools container

# Create export directory
mkdir -p /exports/dsbulk

# Export users table
dsbulk unload \
  -h dse-node \
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
  -h dse-node \
  -k training \
  -t products \
  -url /exports/dsbulk/products \
  -f /config/dsbulk/dsbulk.conf

# Export orders
dsbulk unload \
  -h dse-node \
  -k training \
  -t orders \
  -url /exports/dsbulk/orders \
  -f /config/dsbulk/dsbulk.conf

# Export user_activity
dsbulk unload \
  -h dse-node \
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
  -h dse-node \
  -k training \
  -url /exports/dsbulk/active_users \
  --schema.query "SELECT user_id, username, email, status FROM training.users WHERE status = 'active' ALLOW FILTERING" \
  -f /config/dsbulk/dsbulk.conf

# Export recent orders (last 30 days simulation)
dsbulk unload \
  -h dse-node \
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
  -h hcd-node \
  -k training \
  -t users \
  -url /exports/dsbulk/users \
  -f /config/dsbulk/dsbulk.conf

# Verify import
cqlsh hcd-node -e "SELECT COUNT(*) FROM training.users;"
```

### Step 7: Import All Tables

```bash
# Import products
dsbulk load \
  -h hcd-node \
  -k training \
  -t products \
  -url /exports/dsbulk/products \
  -f /config/dsbulk/dsbulk.conf

# Import orders
dsbulk load \
  -h hcd-node \
  -k training \
  -t orders \
  -url /exports/dsbulk/orders \
  -f /config/dsbulk/dsbulk.conf

# Import user_activity
dsbulk load \
  -h hcd-node \
  -k training \
  -t user_activity \
  -url /exports/dsbulk/user_activity \
  -f /config/dsbulk/dsbulk.conf

# Verify all imports
cqlsh hcd-node -e "
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
  -h dse-node \
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
  -h hcd-node \
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
  -h dse-node \
  -k training \
  -t user_activity \
  -url /exports/dsbulk/user_activity_parallel \
  --connector.csv.maxConcurrentFiles 8 \
  --executor.maxPerSecond 50000 \
  -f /config/dsbulk/dsbulk.conf

# Import with high performance settings
dsbulk load \
  -h hcd-node \
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
  -h hcd-node \
  -k training \
  -t users \
  -url /exports/dsbulk/users \
  --dryRun true \
  -f /config/dsbulk/dsbulk.conf

# Load with error handling
dsbulk load \
  -h hcd-node \
  -k training \
  -t users \
  -url /exports/dsbulk/users \
  --executor.maxErrors 100 \
  --executor.maxErrorRatio 0.01 \
  --log.directory /exports/logs/users_import \
  -f /config/dsbulk/dsbulk.conf

# Check logs for errors
cat /exports/logs/users_import/LOAD*/operation.log
```

## Part 5: Validation and Monitoring

### Step 11: Validate Migration

```bash
# Run comprehensive validation
python3 /scripts/validate_migration.py

exit
```

### Step 12: Monitor HCD Health

```bash
# Check HCD cluster health
docker exec hcd-node nodetool status

# Check table statistics
docker exec hcd-node nodetool tablestats training

# Check compaction
docker exec hcd-node nodetool compactionstats

# Check if repair is needed
docker exec hcd-node nodetool repair training
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
  -h hcd-node \
  -k training \
  -t users \
  -url /exports/dsbulk/users \
  -f /config/dsbulk/dsbulk-timeout.conf
```

### Issue: Out of memory

```bash
# Reduce batch size and concurrency
dsbulk load \
  -h hcd-node \
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
  -h hcd-node \
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
- ✅ Validation passed

## Key Takeaways

1. **Performance**: DSBulk is 6-10x faster than COPY
2. **Scalability**: Handles large datasets efficiently
3. **Flexibility**: Supports compression, filtering, and custom queries
4. **Error Handling**: Robust error handling and logging
5. **Production Ready**: Suitable for production migrations

## Next Steps

Proceed to [Exercise 4: Cassandra Data Migrator (CDM)](04-cdm-migration.md) to learn about using CDM for large-scale data migration.

## Clean Up

```bash
# Remove export files
docker exec tools rm -rf /exports/dsbulk/*

# Remove logs
docker exec tools rm -rf /exports/logs/*

# Truncate HCD tables if needed
docker exec hcd-node cqlsh -e "
TRUNCATE training.users;
TRUNCATE training.products;
TRUNCATE training.orders;
TRUNCATE training.user_activity;
"
```

---

**Time to Complete:** 45-60 minutes  
**Difficulty:** Intermediate
**Next Exercise:** [Cassandra Data Migrator (CDM)](04-cdm-migration.md)