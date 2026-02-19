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

### Step 1: Export Data from DSE Using COPY

```bash
# Access the migration tools container
docker exec -it migration-tools bash

# Create export directory
mkdir -p /exports/copy

# Export users table
cqlsh dse-node1 -e "
COPY training.users TO '/exports/copy/users.csv' 
WITH HEADER = true;
"

# Export products table
cqlsh dse-node1 -e "
COPY training.products TO '/exports/copy/products.csv' 
WITH HEADER = true;
"

# Export orders table (smaller subset for testing)
cqlsh dse-node1 -e "
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
# Still in migration-tools container

# Import users
cqlsh hcd-node1 -e "
COPY training.users FROM '/exports/copy/users.csv' 
WITH HEADER = true;
"

# Import products
cqlsh hcd-node1 -e "
COPY training.products FROM '/exports/copy/products.csv' 
WITH HEADER = true;
"

# Import orders
cqlsh hcd-node1 -e "
COPY training.orders FROM '/exports/copy/orders.csv' 
WITH HEADER = true 
AND CHUNKSIZE = 100;
"

# Exit container
exit
```

### Step 3: Validate COPY Migration

```bash
# Compare row counts
echo "=== DSE Row Counts ==="
docker exec dse-node1 cqlsh -e "
SELECT COUNT(*) FROM training.users;
SELECT COUNT(*) FROM training.products;
SELECT COUNT(*) FROM training.orders;
"

echo "=== HCD Row Counts ==="
docker exec hcd-node1 cqlsh -e "
SELECT COUNT(*) FROM training.users;
SELECT COUNT(*) FROM training.products;
SELECT COUNT(*) FROM training.orders;
"

# Sample data comparison
echo "=== Sample Data from DSE ==="
docker exec dse-node1 cqlsh -e "
SELECT user_id, username, email FROM training.users LIMIT 5;
"

echo "=== Sample Data from HCD ==="
docker exec hcd-node1 cqlsh -e "
SELECT user_id, username, email FROM training.users LIMIT 5;
"
```

**Validation Checklist:**
- [ ] Row counts match between DSE and HCD
- [ ] Sample data looks identical
- [ ] No errors during import

## Part 2: SSTableLoader Migration

### Step 4: Create Snapshot on DSE

```bash
# Create snapshot of training keyspace
docker exec dse-node1 nodetool snapshot training -t migration_snapshot

# List snapshots
docker exec dse-node1 nodetool listsnapshots

# Find snapshot location
docker exec dse-node1 find /var/lib/cassandra/data/training -name migration_snapshot -type d
```

### Step 5: Copy SSTables to Staging Area

```bash
# Access DSE node
docker exec -it dse-node1 bash

# Create staging directory
mkdir -p /tmp/sstables/training/users

# Copy SSTables from snapshot
cp /var/lib/cassandra/data/training/users-*/snapshots/migration_snapshot/* \
   /tmp/sstables/training/users/

# Verify files
ls -lh /tmp/sstables/training/users/

# Exit DSE node
exit

# Copy from DSE container to host
docker cp dse-node1:/tmp/sstables /tmp/sstables

# Copy from host to migration-tools container
docker cp /tmp/sstables migration-tools:/exports/
```

### Step 6: Load SSTables to HCD

```bash
# Access migration-tools container
docker exec -it migration-tools bash

# Use sstableloader to stream data to HCD
# Note: This requires the SSTables to be in the correct format
# For this lab, we'll demonstrate the command structure

# First, verify HCD cluster is accessible
nodetool -h hcd-node1 status

# Load SSTables (this may fail due to format differences between DSE 5.1 and Cassandra 4.1)
# This is expected and demonstrates a real-world challenge
sstableloader \
  -d hcd-node1,hcd-node2,hcd-node3 \
  -u cassandra \
  -pw cassandra \
  /exports/sstables/training/users

# Exit container
exit
```

**Note:** SSTableLoader may fail due to SSTable format incompatibility between DSE 5.1 (mc format) and Cassandra 4.1 (na/nb format). This is a real limitation and why other tools like DSBulk are often preferred.

### Step 7: Clean Up Snapshots

```bash
# Clear snapshot on DSE
docker exec dse-node1 nodetool clearsnapshot -t migration_snapshot training

# Verify snapshot removed
docker exec dse-node1 nodetool listsnapshots
```

## Part 3: Performance Comparison

### Step 8: Measure COPY Performance

```bash
# Access migration-tools container
docker exec -it migration-tools bash

# Time the export
time cqlsh dse-node1 -e "
COPY training.user_activity TO '/exports/copy/user_activity.csv' 
WITH HEADER = true;
"

# Time the import
time cqlsh hcd-node1 -e "
COPY training.user_activity FROM '/exports/copy/user_activity.csv' 
WITH HEADER = true;
"

# Exit container
exit
```

**Record Results:**
- Export time: _____ seconds
- Import time: _____ seconds
- Total time: _____ seconds

### Step 9: Analyze Performance

```bash
# Check table statistics on HCD
docker exec hcd-node1 nodetool tablestats training.user_activity

# Check compaction stats
docker exec hcd-node1 nodetool compactionstats

# Check if repair is needed
docker exec hcd-node1 nodetool repair training
```

## Part 4: Data Validation

### Step 10: Comprehensive Validation

```bash
# Create validation script
docker exec -it migration-tools bash

cat > /scripts/validate_migration.sh << 'EOF'
#!/bin/bash

KEYSPACE="training"
TABLES=("users" "products" "orders" "user_activity")

echo "=== Migration Validation Report ==="
echo "Generated: $(date)"
echo ""

for TABLE in "${TABLES[@]}"; do
  echo "Table: $TABLE"
  
  # Get counts
  DSE_COUNT=$(cqlsh dse-node1 -e "SELECT COUNT(*) FROM $KEYSPACE.$TABLE;" | grep -oP '\d+' | head -1)
  HCD_COUNT=$(cqlsh hcd-node1 -e "SELECT COUNT(*) FROM $KEYSPACE.$TABLE;" | grep -oP '\d+' | head -1)
  
  echo "  DSE count: $DSE_COUNT"
  echo "  HCD count: $HCD_COUNT"
  
  if [ "$DSE_COUNT" -eq "$HCD_COUNT" ]; then
    echo "  Status: ✓ PASS"
  else
    echo "  Status: ✗ FAIL (mismatch)"
  fi
  echo ""
done

echo "=== Validation Complete ==="
EOF

chmod +x /scripts/validate_migration.sh

# Run validation
/scripts/validate_migration.sh

# Exit container
exit
```

### Step 11: Sample Data Verification

```bash
# Create Python validation script
docker exec -it migration-tools bash

cat > /scripts/validate_data.py << 'EOF'
from cassandra.cluster import Cluster
import sys

def validate_table(keyspace, table):
    # Connect to both clusters
    dse_cluster = Cluster(['dse-node1'])
    hcd_cluster = Cluster(['hcd-node1'])
    
    dse_session = dse_cluster.connect(keyspace)
    hcd_session = hcd_cluster.connect(keyspace)
    
    # Get sample from DSE
    dse_rows = dse_session.execute(f"SELECT * FROM {table} LIMIT 100")
    
    mismatches = 0
    for row in dse_rows:
        # Build WHERE clause from primary key
        # For users table: user_id is primary key
        pk_value = row.user_id
        
        # Query HCD
        hcd_result = hcd_session.execute(
            f"SELECT * FROM {table} WHERE user_id = %s",
            [pk_value]
        )
        
        hcd_row = hcd_result.one()
        
        if hcd_row is None:
            print(f"Missing row in HCD: {pk_value}")
            mismatches += 1
        elif row != hcd_row:
            print(f"Data mismatch for: {pk_value}")
            mismatches += 1
    
    print(f"\nValidation complete for {table}")
    print(f"Checked: 100 rows")
    print(f"Mismatches: {mismatches}")
    
    dse_cluster.shutdown()
    hcd_cluster.shutdown()
    
    return mismatches == 0

if __name__ == "__main__":
    # Install driver if needed
    import subprocess
    subprocess.run(["pip", "install", "-q", "cassandra-driver"])
    
    success = validate_table("training", "users")
    sys.exit(0 if success else 1)
EOF

# Run validation
python3 /scripts/validate_data.py

# Exit container
exit
```

## Troubleshooting

### Issue: COPY command times out

```bash
# Increase timeout
docker exec -it migration-tools bash

cqlsh dse-node1 --request-timeout=300 -e "
COPY training.users TO '/exports/copy/users.csv' 
WITH HEADER = true;
"

exit
```

### Issue: Out of memory during COPY

```bash
# Reduce page size
docker exec -it migration-tools bash

cqlsh dse-node1 -e "
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
docker exec -u root -it dse-node1 bash

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
docker exec migration-tools rm -rf /exports/copy/*

# Clear snapshots
docker exec dse-node1 nodetool clearsnapshot --all

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
**Next Exercise:** [DSBulk Migration](03-dsbulk-migration.md)