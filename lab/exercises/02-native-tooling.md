# Exercise 2: Native Tooling Migration

## Objectives

- Use native Cassandra tools for data migration
- Practice with COPY command for small datasets
- Use SSTableLoader for bulk data loading
- Compare performance of different approaches
- Validate data integrity after migration

## Prerequisites

- Completed Exercise 1: Environment Setup
- DSE cluster with sample data
- HCD cluster with schema created

**Note:** This exercise assumes you are working from the `lab` directory. If starting fresh, run `cd lab` from the project root.

## Duration

45-60 minutes

## Overview

This exercise demonstrates using native Cassandra tools (COPY command and SSTableLoader) to migrate data from DSE to HCD. These tools are built into Cassandra and don't require additional software.

## Part 1: COPY Command Migration
> Note: In this section we will only migrate data for tables: users, products and orders! So, not user_activity.

### Step 1: Export Data from DSE Using COPY

```bash
# Access the tools container
docker exec -it tools bash

# Create export directory
mkdir -p /exports/copy

# Export users table
cqlsh dse-node -e "
COPY training.users TO '/exports/copy/users.csv' 
WITH HEADER = true;
"

# Export products table
cqlsh dse-node -e "
COPY training.products TO '/exports/copy/products.csv' 
WITH HEADER = true;
"

# Export orders table (smaller subset for testing)
cqlsh dse-node -e "
COPY training.orders TO '/exports/copy/orders.csv' 
WITH HEADER = true 
AND MAXREQUESTS = 10 
AND PAGESIZE = 100;
"

# Verify exports
ls -lh /exports/copy/
wc -l /exports/copy/*.csv
```

**Expected Output:**
```
users.csv: ~1001 lines (1000 data + 1 header)
products.csv: ~501 lines (500 data + 1 header)
orders.csv: ~2001 lines (2000 data + 1 header)
```

### Step 2: Import Data to HCD Using COPY

```bash
# Still in tools container

# Import users
cqlsh hcd-node -e "
COPY training.users FROM '/exports/copy/users.csv' 
WITH HEADER = true;
"

# Import products
cqlsh hcd-node -e "
COPY training.products FROM '/exports/copy/products.csv' 
WITH HEADER = true;
"

# Import orders
cqlsh hcd-node -e "
COPY training.orders FROM '/exports/copy/orders.csv' 
WITH HEADER = true 
AND CHUNKSIZE = 100;
"

# Exit container
exit
```

### Step 3: Validate COPY Migration

Use the validation script to verify the migration:

```bash
# Run comprehensive validation
docker exec tools bash -c "
pip install -q cassandra-driver && \
python3 /scripts/validate_migration.py
"
```

**Expected Output:**
```
============================================================
Migration Consistency Validation
============================================================

Validating table: users
  DSE count: 1,000
  HCD count: 1,000
  Count check: ✓ PASS
  Validating sample data...
  Sample check: ✓ PASS (100 rows validated)

Validating table: products
  DSE count: 500
  HCD count: 500
  Count check: ✓ PASS
  Validating sample data...
  Sample check: ✓ PASS (100 rows validated)

Validating table: orders
  DSE count: 2,000
  HCD count: 2,000
  Count check: ✓ PASS
  Validating sample data...
  Sample check: ✓ PASS (100 rows validated)

Validating table: user_activity
  DSE count: 5,000
  HCD count: 0
  Count check: ✗ FAIL (difference: 5000)

============================================================
✗ Validation failed - investigate discrepancies
============================================================
```

**Validation Checklist:**
- [ ] All row counts match between DSE and HCD
- [ ] Sample data validation passes for all tables
- [ ] No errors during import

## Part 2: SSTableLoader Migration

### Step 4: Create Snapshot on DSE

```bash
# Access DSE node
docker exec -it dse-node bash

# Create snapshot of training keyspace
nodetool snapshot training -t migration_snapshot

# List snapshots
nodetool listsnapshots

# Find snapshot location
find /var/lib/cassandra/data/training -name migration_snapshot -type d
```

### Step 5: Prepare SSTables on DSE Node

```bash
# Create staging directory
mkdir -p /tmp/sstables/training/user_activity

# Copy SSTables from snapshot
cp /var/lib/cassandra/data/training/user_activity-*/snapshots/migration_snapshot/* \
   /tmp/sstables/training/user_activity/

# Verify files
ls -lh /tmp/sstables/training/user_activity/

# You should see files like:
# - *-Data.db (actual data)
# - *-Index.db (index)
# - *-Statistics.db (statistics)
# - *-Summary.db (summary)
# etc.
```

### Step 6: Load SSTables to HCD Using sstableloader

```bash
# Still in DSE node container

# Verify HCD is reachable via CQL (port 9042)
cqlsh hcd-node -e "SELECT cluster_name FROM system.local;"

# Ensure user_activity is empty (we didn't copy it in the previous excercise
cqlsh hcd-node -e "SELECT * from training.user_activity;"

# Use sstableloader to stream data from DSE to HCD
# Note: sstableloader is in /opt/dse/resources/cassandra/bin/
# This will likely fail (or crash the DSE node) due to SSTable format incompatibility
# DSE 5.1 uses 'mc' format, Cassandra 4.1 uses 'na/nb' format
# The -d flag specifies the initial contact point for the target cluster
/opt/dse/resources/cassandra/bin/sstableloader \
  -d hcd-node \
  /tmp/sstables/training/user_activity

# Exit DSE node
exit
```

**Note:** SSTableLoader may fail due to SSTable format incompatibility between DSE 5.1 (mc format) and Cassandra 4.1 (na/nb format). This is a real limitation and why other tools like DSBulk are often preferred.

### Step 7: Clean Up Snapshots

```bash
# Clear snapshot on DSE
docker exec dse-node nodetool clearsnapshot -t migration_snapshot training

# Verify snapshot removed
docker exec dse-node nodetool listsnapshots
```

## Part 3: Health Check

### Step 8: Analyze Health

```bash
# Check table statistics on HCD
docker exec hcd-node nodetool tablestats training.user_activity

# Check compaction stats
docker exec hcd-node nodetool compactionstats

# Check if repair is needed
docker exec hcd-node nodetool repair training
```

## Part 4: Data Validation

### Step 9: Sample Data Verification

Use the comprehensive validation script:

```bash
# Run the validation script from the tools container
# This script validates all tables with row counts and sample data checks
docker exec tools bash -c "
pip install -q cassandra-driver && \
python3 /scripts/validate_migration.py
"
```

**Expected Output:**
```
============================================================
Migration Consistency Validation
============================================================

Validating table: users
  DSE count: 1,000
  HCD count: 1,000
  Count check: ✓ PASS
  Validating sample data...
  Sample check: ✓ PASS (100 rows validated)

Validating table: products
  DSE count: 500
  HCD count: 500
  Count check: ✓ PASS
  Validating sample data...
  Sample check: ✓ PASS (100 rows validated)

Validating table: orders
  DSE count: 2,000
  HCD count: 2,000
  Count check: ✓ PASS
  Validating sample data...
  Sample check: ✓ PASS (100 rows validated)

Validating table: user_activity
  DSE count: 5,000
  HCD count: 0
  Count check: ✗ FAIL (difference: 5000)

============================================================
✗ Validation failed - investigate discrepancies
============================================================
```

## Troubleshooting

### Issue: COPY command times out

```bash
# Increase timeout
docker exec -it tools bash

cqlsh dse-node --request-timeout=300 -e "
COPY training.users TO '/exports/copy/users.csv' 
WITH HEADER = true;
"

exit
```

### Issue: Out of memory during COPY

```bash
# Reduce page size
docker exec -it tools bash

cqlsh dse-node -e "
COPY training.users TO '/exports/copy/users.csv' 
WITH HEADER = true 
AND PAGESIZE = 100;
"

exit
```

### Issue: SSTableLoader format incompatibility

**Solution:** This is expected. DSE 5.1 uses SSTable format 'mc' while Cassandra 4.1 uses 'na/nb'. Use DSBulk instead (covered in Exercise 3).

### Issue: Permission denied accessing SSTables

```bash
# Run as root in container
docker exec -u root -it dse-node bash

# Copy files with proper permissions
cp -r /var/lib/cassandra/data/training/users-*/snapshots/migration_snapshot/* \
   /tmp/sstables/training/users/

chmod -R 755 /tmp/sstables/

exit
```

## Performance Analysis

### COPY Command Performance

**Pros:**
- Simple to use
- No additional tools required
- Human-readable CSV format
- Good for small datasets (< 100GB)

**Cons:**
- Slow for large datasets
- Single-threaded
- High memory usage
- No compression

**Typical Performance:**
- Small tables (< 10K rows): 1-2 minutes
- Medium tables (10K-100K rows): 5-15 minutes
- Large tables (> 100K rows): Not recommended

### SSTableLoader Performance

**Pros:**
- Fast bulk loading
- Efficient streaming
- Parallel processing
- Direct SSTable access

**Cons:**
- Requires filesystem access
- Format compatibility issues
- Complex setup
- No transformation capability

**Typical Performance:**
- 1GB data: 5-10 minutes
- 10GB data: 30-60 minutes
- 100GB data: 5-10 hours

## Success Criteria

You have successfully completed this exercise when:

- ✅ Exported data from DSE using COPY command
- ✅ Imported data to HCD using COPY command
- ✅ Validated row counts match
- ✅ Understood SSTableLoader limitations
- ✅ Compared performance characteristics
- ✅ Validated data integrity

## Key Takeaways

1. **COPY Command**: Simple but slow, best for small datasets
2. **SSTableLoader**: Fast but has format compatibility issues
3. **Validation**: Always verify data after migration
4. **Performance**: Native tools have limitations for large datasets
5. **Format Issues**: DSE and HCD SSTable formats differ

## Next Steps

Proceed to [Exercise 3: DSBulk Migration](03-dsbulk-migration.md) to learn about using DSBulk for high-performance data migration.

## Clean Up

```bash
# Remove exported files
docker exec tools rm -rf /exports/copy/*

# Clear snapshots
docker exec dse-node nodetool clearsnapshot --all

# Truncate HCD tables if needed
docker exec hcd-node cqlsh -e "
TRUNCATE training.users;
TRUNCATE training.products;
TRUNCATE training.orders;
TRUNCATE training.user_activity
"
```

---

**Time to Complete:** 45-60 minutes  
**Difficulty:** Intermediate  
**Next Exercise:** [DSBulk Migration](03-dsbulk-migration.md)