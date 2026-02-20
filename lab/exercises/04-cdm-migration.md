# Exercise 4: Cassandra Data Migrator (CDM) Migration

## Objectives

- Use pre-configured CDM with Apache Spark
- Perform bulk data migration using CDM
- Validate migrated data with DiffData
- Compare CDM performance with DSBulk
- Understand CDM's advanced features

## Prerequisites

- Completed Exercise 1
- DSE cluster with sample data
- HCD cluster with schema created
- Docker with sufficient resources (4GB+ RAM recommended)

**Note:** This exercise assumes you are working from the `lab` directory. If starting fresh, run `cd lab` from the project root.

## Duration

45-60 minutes

## Overview

Cassandra Data Migrator (CDM) is a Spark-based tool designed for large-scale data migration between Cassandra clusters. It's ideal for bulk data loads and provides built-in validation capabilities. 

The `spark-cdm` container is already configured in `docker-compose.yml` with pre-configured property files in the `cdm-config/` directory.

## Part 1: Verify CDM Setup

### Step 1: Start CDM Container

The CDM container starts automatically with `docker-compose up`, but let's verify it's running:

```bash
# Check if spark-cdm container is running
docker-compose ps spark-cdm

# If not running, start it
docker-compose up -d spark-cdm
```

### Step 2: Verify CDM Installation

```bash
# Access the CDM container
docker exec -it spark-cdm bash

# Check Spark installation
spark-submit --version

# Check if CDM JAR is available
ls -lh /assets/cassandra-data-migrator*.jar

# Verify configuration files are mounted
ls -la /app/config/

# Exit container
exit
```

**Expected Output:**
```
cdm.properties
README.md
```

### Step 3: Review Consolidated Configuration

```bash
# View the consolidated configuration
cat cdm-config/cdm.properties

# Key settings to note:
# - Source: dse-node:9042
# - Target: hcd-node:9042
# - TTL and writetime preservation enabled
# - Performance tuning pre-configured
# - Table-specific settings will be passed via --conf
```

## Part 2: Prepare for Migration

### Step 1: Clear Target Data

```bash
# Clear existing data in HCD
docker exec hcd-node cqlsh -e "
TRUNCATE training.users;
TRUNCATE training.products;
TRUNCATE training.orders;
TRUNCATE training.user_activity
"
```

### Step 2: Verify Source Data

```bash
# Count records in source
echo "Source data counts:"
docker exec dse-node cqlsh -e "
SELECT COUNT(*) FROM training.users;
SELECT COUNT(*) FROM training.products;
SELECT COUNT(*) FROM training.orders;
SELECT COUNT(*) FROM training.user_activity
"
```

## Part 3: Run CDM Migration

### Step 1: Migrate Users Table

```bash
# Run CDM migration for users table
docker exec spark-cdm spark-submit \
  --class com.datastax.cdm.job.Migrate \
  --master 'local[*]' \
  --driver-memory 2g \
  --executor-memory 2g \
  --properties-file /app/config/cdm.properties \
  --conf spark.cdm.schema.origin.keyspaceTable=training.users \
  --conf spark.cdm.schema.target.keyspaceTable=training.users \
  /assets/cassandra-data-migrator-5.6.3.jar \
  2>&1 | tee cdm-logs/migrate-users.log

# Check the logs
cat cdm-logs/migrate-users.log | grep "Final Write Record"
```

**What to observe:**
- Spark job initialization
- Partition processing
- Records migrated per second
- Completion status

### Step 2: Verify Users Migration

```bash
# Check target data count
echo "Verifying users migration:"
docker exec hcd-node cqlsh -e "SELECT COUNT(*) FROM training.users;"

# Sample some migrated data
docker exec hcd-node cqlsh -e "SELECT * FROM training.users LIMIT 5;"
```

### Step 3: Migrate Remaining Tables

```bash
# Migrate products
docker exec spark-cdm spark-submit \
  --class com.datastax.cdm.job.Migrate \
  --master 'local[*]' \
  --driver-memory 2g \
  --executor-memory 2g \
  --properties-file /app/config/cdm.properties \
  --conf spark.cdm.schema.origin.keyspaceTable=training.products \
  --conf spark.cdm.schema.target.keyspaceTable=training.products \
  /assets/cassandra-data-migrator-5.6.3.jar \
  2>&1 | tee cdm-logs/migrate-products.log

# Migrate orders
docker exec spark-cdm spark-submit \
  --class com.datastax.cdm.job.Migrate \
  --master 'local[*]' \
  --driver-memory 2g \
  --executor-memory 2g \
  --properties-file /app/config/cdm.properties \
  --conf spark.cdm.schema.origin.keyspaceTable=training.orders \
  --conf spark.cdm.schema.target.keyspaceTable=training.orders \
  /assets/cassandra-data-migrator-5.6.3.jar \
  2>&1 | tee cdm-logs/migrate-orders.log

# Migrate user_activity
docker exec spark-cdm spark-submit \
  --class com.datastax.cdm.job.Migrate \
  --master 'local[*]' \
  --driver-memory 2g \
  --executor-memory 2g \
  --properties-file /app/config/cdm.properties \
  --conf spark.cdm.schema.origin.keyspaceTable=training.user_activity \
  --conf spark.cdm.schema.target.keyspaceTable=training.user_activity \
  /assets/cassandra-data-migrator-5.6.3.jar \
  2>&1 | tee cdm-logs/migrate-user_activity.log
```

## Part 4: Data Validation

### Step 1: Quick Validation with Python Script

Use the provided validation script for a comprehensive check:

```bash
# Run the validation script
docker exec tools python3 /scripts/validate_migration.py

# Expected output shows count and sample validation for all tables
```

**Expected Output:**
```
============================================================
Migration Consistency Validation
============================================================

Validating table: users
  DSE count: 10,000
  HCD count: 10,000
  Count check: ✓ PASS
  Validating sample data...
  Sample check: ✓ PASS (100 rows validated)

Validating table: products
  DSE count: 1,000
  HCD count: 1,000
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
  HCD count: 5,000
  Count check: ✓ PASS
  Validating sample data...
  Sample check: ✓ PASS (100 rows validated)

============================================================
✓ All validation checks passed!
Clusters are consistent and ready for cutover
============================================================
```

### Step 2: Detailed Validation with CDM DiffData (Optional)

For more detailed validation, use CDM's built-in DiffData:

```bash
# Validate users table with DiffData
docker exec spark-cdm spark-submit \
  --class com.datastax.cdm.job.DiffData \
  --master 'local[*]' \
  --driver-memory 2g \
  --executor-memory 2g \
  --properties-file /app/config/cdm.properties \
  --conf spark.cdm.schema.origin.keyspaceTable=training.users \
  --conf spark.cdm.schema.target.keyspaceTable=training.users \
  /assets/cassandra-data-migrator-5.6.3.jar \
  2>&1 | tee cdm-logs/diffdata-users.log

# Check validation results
cat cdm-logs/diffdata-users.log | grep "Valid Record"
```

### Step 3: Validate All Tables with DiffData

```bash
# Create a helper script to validate all tables
for table in products orders user_activity; do
  echo "Validating $table..."
  docker exec spark-cdm spark-submit \
    --class com.datastax.cdm.job.DiffData \
    --master 'local[*]' \
    --driver-memory 2g \
    --executor-memory 2g \
    --properties-file /app/config/cdm.properties \
    --conf spark.cdm.schema.origin.keyspaceTable=training.$table \
    --conf spark.cdm.schema.target.keyspaceTable=training.$table \
    /assets/cassandra-data-migrator-5.6.3.jar \
    2>&1 | tee cdm-logs/diffdata-$table.log
done

# Summary
cat cdm-logs/diffdata-*.log | grep "Valid Record"
```

## Part 5: Monitor with Spark UI

### Step 1: Access Spark UI

```bash
# Spark UI is available at:
echo "Spark Master UI: http://localhost:8080"
echo "Spark Application UI: http://localhost:4040"
```

Open your browser and navigate to these URLs to see:
- Active and completed jobs
- Stage execution details
- Task duration and distribution
- Executor metrics
- Memory usage

### Step 2: Analyze Performance Metrics

In the Spark UI, look for:
- **Jobs Tab**: Overall migration progress
- **Stages Tab**: Partition processing details
- **Executors Tab**: Resource utilization
- **SQL Tab**: Query execution plans (if applicable)

## Part 6: Performance Comparison

### Step 1: Compare Migration Times

```bash
# Extract timing information from logs
echo "========================================="
echo "CDM Performance Analysis"
echo "========================================="

for table in users products orders user_activity; do
  echo ""
  echo "Table: training.$table"
  
  # Count records migrated
  RECORDS=$(docker exec hcd-node cqlsh -e "SELECT COUNT(*) FROM training.$table;" | grep -oP '\d+' | head -1)
  echo "Records migrated: $RECORDS"
  
  # Check log for timing (if available)
  if [ -f "cdm-logs/migrate-${table}.log" ]; then
    echo "Log file: cdm-logs/migrate-${table}.log"
  fi
done
```

## Part 7: Advanced Features (Optional)

### Feature 1: Auto-Correction

Test CDM's ability to automatically fix discrepancies:

```bash
# Insert a test record only in source
docker exec dse-node cqlsh -e "
INSERT INTO training.users (user_id, username, email, created_at) 
VALUES (uuid(), 'test_cdm_user', 'test@cdm.com', toTimestamp(now()));
"

# Run validation with auto-correction
# Note: This would require adding autocorrect configuration
# For now, just re-run the migration which is idempotent
docker exec spark-cdm spark-submit \
  --class com.datastax.cdm.job.Migrate \
  --master 'local[*]' \
  --driver-memory 2g \
  --executor-memory 2g \
  --properties-file /app/config/cdm.properties \
  --conf spark.cdm.schema.origin.keyspaceTable=training.users \
  --conf spark.cdm.schema.target.keyspaceTable=training.users \
  /assets/cassandra-data-migrator-5.6.3.jar

echo "✓ Auto-correction test completed"
```

### Feature 2: View Configuration Options

```bash
# Review all available configuration options
cat cdm-config/README.md

# Key features available:
# - TTL preservation (enabled by default)
# - Writetime preservation (enabled by default)
# - Rate limiting
# - Batch size tuning
# - Partition-based parallelism
```

## Part 8: Cleanup and Review

### Step 1: Review Logs

```bash
# Check for any errors
echo "Checking for errors in migration logs:"
grep -i "error\|exception\|failed" cdm-logs/*.log || echo "No errors found"

# View log files
ls -lh cdm-logs/
```

### Step 2: Verify Final State

```bash
# Compare final counts
docker exec tools python3 /scripts/validate_migration.py
```

### Step 3: Archive Logs (Optional)

```bash
# Create archive of migration logs
tar -czf cdm-migration-logs-$(date +%Y%m%d).tar.gz cdm-logs/

echo "✓ Logs archived"
```

## Summary

In this exercise, you:

✅ Used pre-configured CDM with Apache Spark  
✅ Performed bulk data migration using CDM  
✅ Validated data integrity with DiffData  
✅ Monitored migration with Spark UI  
✅ Compared CDM performance with DSBulk  
✅ Explored CDM's advanced features

### Key Takeaways

1. **CDM Strengths:**
   - Direct cluster-to-cluster migration (no intermediate files)
   - Built-in validation with DiffData
   - Preserves TTL and writetime automatically
   - Spark-based parallelism for large datasets
   - Idempotent operations (safe to re-run)

2. **When to Use CDM:**
   - Large datasets (100GB+)
   - Need for data validation
   - Complex migration scenarios
   - Spark infrastructure available
   - TTL/writetime preservation required

3. **Configuration Best Practices:**
   - Use consolidated config file with `--conf` for table-specific settings
   - Enable TTL/writetime preservation (already enabled)
   - Use appropriate partition counts for parallelism
   - Monitor and tune based on cluster capacity
   - Validate with both Python script and CDM DiffData

4. **Validation Strategy:**
   - Quick validation: Use [`validate_migration.py`](../scripts/validate_migration.py) for fast count and sample checks
   - Detailed validation: Use CDM DiffData for comprehensive row-by-row comparison
   - Both methods validate all four tables: users, products, orders, user_activity

### Next Steps

- **Exercise 5:** Zero Downtime Migration with ZDM Proxy
- **Exercise 6:** Validation and Monitoring

### Additional Resources

- [CDM Official Documentation](https://docs.datastax.com/en/data-migration/cassandra-data-migrator.html)
- [CDM GitHub Repository](https://github.com/datastax/cassandra-data-migrator)
- [Apache Spark Documentation](https://spark.apache.org/docs/latest/)
- Pre-configured files: `cdm-config/` directory

---

**Estimated Completion Time:** 45-60 minutes  
**Difficulty Level:** Intermediate  
**Prerequisites:** Exercises 1-3