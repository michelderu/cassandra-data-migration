# Cassandra Data Migrator (CDM) Approach

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Migration Operations](#migration-operations)
6. [Advanced Features](#advanced-features)
7. [Performance Tuning](#performance-tuning)
8. [Monitoring](#monitoring)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

## Overview

Cassandra Data Migrator (CDM) is an Apache Spark-based tool designed for migrating and validating data between Apache Cassandra® clusters. It's particularly effective for large-scale data migration and can be combined with other tools for zero-downtime scenarios.

### Official Documentation
For the most up-to-date information, refer to the official DataStax documentation:
- **Main Documentation**: https://docs.datastax.com/en/data-migration/cassandra-data-migrator.html
- **GitHub Repository**: https://github.com/datastax/cassandra-data-migrator

### Key Features

✅ **Spark-Based**: Leverages Apache Spark for distributed processing  
✅ **High Performance**: Parallel processing across multiple workers  
✅ **Flexible**: Supports various migration scenarios  
✅ **Data Validation**: Built-in consistency checking  
✅ **Transformation**: Can transform data during migration  
✅ **Resumable**: Can resume interrupted migrations  
✅ **Open Source**: Community-driven development

### When to Use CDM

**Ideal For:**
- Large-scale data migrations (multi-TB datasets)
- Initial bulk data load before enabling dual-write
- Data transformation during migration
- Complex data validation requirements
- Scenarios where Spark infrastructure is available

**Not Ideal For:**
- Real-time synchronization (use ZDM instead)
- Small datasets (< 100GB, simpler tools suffice)
- Environments without Spark
- Scenarios requiring immediate consistency

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│              Source DSE Cluster                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │  Node 1  │  │  Node 2  │  │  Node 3  │           │
│  └──────────┘  └──────────┘  └──────────┘           │
└─────────────────────────────────────────────────────┘
        │             │             │
        │   Read Data │             │
        ▼             ▼             ▼
┌─────────────────────────────────────────────────────┐
│         Spark Processing & Transformation           │
│  - Read from source                                 │
│  - Transform (optional)                             │
│  - Validate                                         │
│  - Write to target                                  │
└─────────────────────────────────────────────────────┘
        │             │             │
        │  Write Data │             │
        ▼             ▼             ▼
┌─────────────────────────────────────────────────────┐
│              Target HCD Cluster                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │  Node 1  │  │  Node 2  │  │  Node 3  │           │
│  └──────────┘  └──────────┘  └──────────┘           │
└─────────────────────────────────────────────────────┘
```

### Component Details

#### 1. Spark Driver (CDM Application)
- Coordinates migration job
- Manages task distribution
- Collects metrics and logs
- Handles failures and retries

#### 2. Spark Workers
- Execute migration tasks in parallel
- Read from source cluster
- Write to target cluster
- Perform data validation

#### 3. Source Cluster (DSE 5.1)
- Provides data to migrate
- Remains operational during migration
- No modifications required

#### 4. Target Cluster (HCD)
- Receives migrated data
- Schema must exist before migration
- Can be operational during migration

## Installation

### Prerequisites

**Required Software:**
- Apache Spark 3.5 or later (Spark 3.5.3 recommended)
- Java 11 or higher (Java 17 recommended)
- Scala 2.12
- Network connectivity to both source and target clusters

**Recommended Resources:**
- 4+ CPU cores per Spark executor
- 16+ GB RAM per executor
- High-bandwidth network connection between clusters
- Sufficient disk space for Spark shuffle operations

### Method 1: Download Pre-built JAR

The easiest way to get started is to download the pre-built JAR from GitHub releases:

```bash
# Download the latest CDM JAR (check GitHub for latest version)
wget https://github.com/datastax/cassandra-data-migrator/releases/latest/download/cassandra-data-migrator-assembly.jar

# Verify download
ls -lh cassandra-data-migrator-assembly.jar
```

### Method 2: Build from Source

Build from source if you need custom modifications or the latest development version:

```bash
# Clone repository
git clone https://github.com/datastax/cassandra-data-migrator.git
cd cassandra-data-migrator

# Build with SBT (Scala Build Tool)
sbt assembly

# JAR location
ls -lh target/scala-2.12/cassandra-data-migrator-assembly-*.jar
```

### Method 3: Docker Container

Use the Docker container for simplified deployment:

```bash
# Pull Docker image
docker pull datastax/cassandra-data-migrator:latest

# Run migration with mounted configuration
docker run -v $(pwd)/cdm.properties:/app/cdm.properties \
  datastax/cassandra-data-migrator:latest \
  spark-submit --properties-file /app/cdm.properties \
  --class com.datastax.cdm.job.Migrate \
  cassandra-data-migrator-assembly.jar
```

## Configuration

CDM uses a properties file for configuration. All configuration parameters use the `spark.` prefix.

### Basic Configuration

```properties
# cdm.properties - Basic migration configuration

# Spark Application Settings
spark.master=local[*]
spark.app.name=CDM-Migration

# Source Cluster Configuration
spark.cdm.connect.origin.host=dse-node1,dse-node2,dse-node3
spark.cdm.connect.origin.port=9042
spark.cdm.connect.origin.username=cassandra
spark.cdm.connect.origin.password=cassandra
spark.cdm.connect.origin.scb=                    # Optional: Secure Connect Bundle path

# Target Cluster Configuration
spark.cdm.connect.target.host=hcd-node1,hcd-node2,hcd-node3
spark.cdm.connect.target.port=9042
spark.cdm.connect.target.username=cassandra
spark.cdm.connect.target.password=cassandra
spark.cdm.connect.target.scb=                    # Optional: Secure Connect Bundle path

# Schema Configuration
spark.cdm.schema.origin.keyspaceTable=myapp.users
spark.cdm.schema.target.keyspaceTable=myapp.users

# Performance Settings
spark.cdm.perfops.numParts=100
spark.cdm.perfops.batchSize=5
spark.cdm.perfops.fetchSizeInRows=1000
```

**Note:** The configuration property names have been updated in recent CDM versions. Use `spark.cdm.connect.*` instead of the older `spark.origin.*` and `spark.target.*` format.

### Advanced Configuration

```properties
# cdm-advanced.properties - Production-ready configuration

# Spark Application Settings
spark.master=spark://spark-master:7077
spark.app.name=CDM-Production-Migration
spark.executor.instances=10
spark.executor.cores=4
spark.executor.memory=16g
spark.driver.memory=8g

# Source Cluster Configuration
spark.cdm.connect.origin.host=dse-node1,dse-node2,dse-node3
spark.cdm.connect.origin.port=9042
spark.cdm.connect.origin.username=cassandra
spark.cdm.connect.origin.password=cassandra
spark.cdm.connect.origin.localDC=dc1
spark.cdm.connect.origin.consistency=LOCAL_QUORUM

# Target Cluster Configuration
spark.cdm.connect.target.host=hcd-node1,hcd-node2,hcd-node3
spark.cdm.connect.target.port=9042
spark.cdm.connect.target.username=cassandra
spark.cdm.connect.target.password=cassandra
spark.cdm.connect.target.localDC=datacenter1
spark.cdm.connect.target.consistency=LOCAL_QUORUM

# Schema Configuration
spark.cdm.schema.origin.keyspaceTable=myapp.users
spark.cdm.schema.target.keyspaceTable=myapp.users

# Performance Tuning
spark.cdm.perfops.numParts=200
spark.cdm.perfops.batchSize=10
spark.cdm.perfops.fetchSizeInRows=1000
spark.cdm.perfops.ratelimit.origin=10000
spark.cdm.perfops.ratelimit.target=10000

# Data Validation and Correction
spark.cdm.autocorrect.missing=true
spark.cdm.autocorrect.mismatch=true

# Error Handling
spark.cdm.perfops.errorLimit=1000

# Partition Filtering (for parallel migrations)
spark.cdm.tokenrange.partitionFile=                # Path to partition file
```

### SSL/TLS Configuration

```properties
# cdm-ssl.properties - Secure connection configuration

# Source Cluster SSL/TLS
spark.cdm.connect.origin.tls.enabled=true
spark.cdm.connect.origin.tls.truststore.path=/path/to/origin-truststore.jks
spark.cdm.connect.origin.tls.truststore.password=truststore_password
spark.cdm.connect.origin.tls.truststore.type=JKS
spark.cdm.connect.origin.tls.keystore.path=/path/to/origin-keystore.jks
spark.cdm.connect.origin.tls.keystore.password=keystore_password
spark.cdm.connect.origin.tls.enabledAlgorithms=TLS_RSA_WITH_AES_128_CBC_SHA,TLS_RSA_WITH_AES_256_CBC_SHA

# Target Cluster SSL/TLS
spark.cdm.connect.target.tls.enabled=true
spark.cdm.connect.target.tls.truststore.path=/path/to/target-truststore.jks
spark.cdm.connect.target.tls.truststore.password=truststore_password
spark.cdm.connect.target.tls.truststore.type=JKS
spark.cdm.connect.target.tls.keystore.path=/path/to/target-keystore.jks
spark.cdm.connect.target.tls.keystore.password=keystore_password
spark.cdm.connect.target.tls.enabledAlgorithms=TLS_RSA_WITH_AES_128_CBC_SHA,TLS_RSA_WITH_AES_256_CBC_SHA
```

## Migration Operations

CDM supports three main operations: Migrate, DiffData, and Validation. Each serves a specific purpose in the migration workflow.

### Operation 1: Migrate (Data Migration)

The primary operation for migrating data from source to target cluster.

```bash
# Basic migration command
spark-submit \
  --class com.datastax.cdm.job.Migrate \
  --master spark://spark-master:7077 \
  --executor-memory 16g \
  --executor-cores 4 \
  --num-executors 10 \
  cassandra-data-migrator-assembly.jar \
  --properties-file cdm.properties
```

**Key Configuration for Migrate:**
```properties
# Schema mapping
spark.cdm.schema.origin.keyspaceTable=source_ks.source_table
spark.cdm.schema.target.keyspaceTable=target_ks.target_table

# Column selection (optional)
spark.cdm.schema.origin.column.names.to.target=col1,col2,col3  # Specific columns
# OR
spark.cdm.schema.origin.column.names.to.target=*               # All columns (default)
```

### Operation 2: DiffData (Data Validation)

Compare data between source and target clusters to identify discrepancies.

```bash
# Run data validation
spark-submit \
  --class com.datastax.cdm.job.DiffData \
  --master spark://spark-master:7077 \
  cassandra-data-migrator-assembly.jar \
  --properties-file cdm.properties
```

**Validation Output:**
- Missing records in target
- Mismatched records between source and target
- Summary statistics

### Operation 3: Validation with Auto-Correction

Validate and automatically fix discrepancies.

```properties
# Enable auto-correction
spark.cdm.autocorrect.missing=true      # Copy missing records
spark.cdm.autocorrect.mismatch=true     # Fix mismatched records
```

```bash
# Run validation with auto-correction
spark-submit \
  --class com.datastax.cdm.job.DiffData \
  --master spark://spark-master:7077 \
  cassandra-data-migrator-assembly.jar \
  --properties-file cdm-autocorrect.properties
```

### Parallel Migration Strategy

For large tables, split migration into parallel jobs using partition files:

**Step 1: Generate partition file**
```bash
# Create a file with token ranges (one per line)
# Example: partition-ranges.csv
# min_token,max_token
-9223372036854775808,-4611686018427387904
-4611686018427387904,0
0,4611686018427387904
4611686018427387904,9223372036854775807
```

**Step 2: Configure parallel jobs**
```properties
# Job 1 configuration
spark.cdm.tokenrange.partitionFile=/path/to/partition-ranges.csv
spark.cdm.tokenrange.partitionIndex=0  # First range

# Job 2 configuration
spark.cdm.tokenrange.partitionIndex=1  # Second range

# And so on...
```

**Step 3: Run parallel jobs**
```bash
# Launch multiple Spark jobs in parallel
for i in {0..3}; do
  spark-submit \
    --class com.datastax.cdm.job.Migrate \
    --master spark://spark-master:7077 \
    --conf spark.cdm.tokenrange.partitionIndex=$i \
    cassandra-data-migrator-assembly.jar \
    --properties-file cdm.properties &
done
wait
```

### Incremental Migration

Migrate only data modified after a specific timestamp:

```properties
# Enable writetime filtering
spark.cdm.feature.writetime.enabled=true
spark.cdm.feature.writetime.filter.min=1708099200000000  # Microseconds since epoch

# This migrates only rows with writetime >= specified value
```

### Column Mapping and Transformation

**Select specific columns:**
```properties
# Migrate only specific columns
spark.cdm.schema.origin.column.names.to.target=user_id,username,email,created_at
```

**Column name mapping:**
```properties
# Map source columns to different target column names
spark.cdm.schema.origin.column.names.to.target=src_col1:tgt_col1,src_col2:tgt_col2
```

**Constant value columns:**
```properties
# Add constant values to target columns
spark.cdm.transform.custom.writetime=1234567890
spark.cdm.transform.custom.ttl=86400
```

## Advanced Features

### 1. TTL and Writetime Preservation

CDM can preserve the original TTL (Time To Live) and writetime values from the source cluster:

```properties
# Preserve original TTL values
spark.cdm.feature.ttl.enabled=true

# Preserve original writetime values
spark.cdm.feature.writetime.enabled=true

# Both are critical for accurate data migration
# Without these, all data will have new timestamps and default TTL
```

**Important:** When these features are enabled, CDM uses the original timestamps and TTL values, ensuring data consistency between clusters.

### 2. Explode Map Feature

For tables with map columns, CDM can "explode" map entries into separate rows:

```properties
# Enable map explosion
spark.cdm.feature.explodeMap.enabled=true
spark.cdm.feature.explodeMap.origin.name=my_map_column
spark.cdm.feature.explodeMap.target.name=map_key,map_value
```

This is useful when migrating from a denormalized schema to a normalized one.

### 3. Constant Columns

Add constant values to all migrated rows:

```properties
# Add constant columns to target
spark.cdm.transform.custom.writetime=1234567890000000
spark.cdm.transform.custom.ttl=86400

# Useful for:
# - Setting migration metadata
# - Adding default values
# - Standardizing TTL across migrated data
```

### 4. Guardrails

Set limits to prevent migration of problematic data:

```properties
# Set size guardrails
spark.cdm.guardrail.colSizeInKB=1024      # Max column size: 1MB
spark.cdm.guardrail.rowSizeInKB=10240     # Max row size: 10MB

# Rows/columns exceeding guardrails are:
# - Logged to error file
# - Skipped during migration
# - Reported in summary
```

### 5. Data Filtering

Filter data during migration based on various criteria:

```properties
# Filter by writetime range
spark.cdm.feature.writetime.enabled=true
spark.cdm.feature.writetime.filter.min=1640000000000000
spark.cdm.feature.writetime.filter.max=1708099200000000

# Filter by token range (for parallel processing)
spark.cdm.tokenrange.partitionFile=/path/to/ranges.csv
spark.cdm.tokenrange.partitionIndex=0
```

### 6. Randomization for Testing

Randomize data for testing purposes:

```properties
# Enable randomization
spark.cdm.transform.custom.randomize=true

# Useful for:
# - Creating test datasets
# - Anonymizing production data
# - Performance testing
```

### 7. Java Driver Configuration

Fine-tune the Cassandra Java driver settings:

```properties
# Connection settings
spark.cdm.connect.origin.connections.maxPerHost=8
spark.cdm.connect.target.connections.maxPerHost=8

# Timeout settings
spark.cdm.connect.origin.socket.readTimeoutMillis=60000
spark.cdm.connect.target.socket.readTimeoutMillis=60000

# Retry policy
spark.cdm.connect.origin.retry.maxAttempts=10
spark.cdm.connect.target.retry.maxAttempts=10
```

## Performance Tuning

### 1. Spark Parallelism

Control the level of parallelism for optimal performance:

```properties
# Number of Spark partitions (primary parallelism control)
spark.cdm.perfops.numParts=500

# More partitions = more parallelism but more overhead
# Recommended: 2-3x the number of executor cores
# Example: 10 executors × 4 cores × 3 = 120 partitions

# Spark executor configuration
spark.executor.instances=20
spark.executor.cores=4
spark.executor.memory=16g
spark.driver.memory=8g
```

**Tuning Guidelines:**
- Start with `numParts = total_cores × 2`
- Increase if tasks complete too quickly (< 1 minute)
- Decrease if tasks are too slow or memory issues occur

### 2. Batch Size Optimization

```properties
# Rows per write batch to target
spark.cdm.perfops.batchSize=5

# Fetch size from source (rows per read)
spark.cdm.perfops.fetchSizeInRows=1000

# Tuning guidelines:
# - Smaller batchSize (1-5): Better for large rows
# - Larger batchSize (10-20): Better for small rows
# - Adjust based on row size and memory
```

### 3. Rate Limiting

Prevent overwhelming source or target clusters:

```properties
# Maximum reads per second from origin
spark.cdm.perfops.ratelimit.origin=20000

# Maximum writes per second to target
spark.cdm.perfops.ratelimit.target=20000

# Set based on cluster capacity:
# - Monitor cluster metrics during migration
# - Reduce if seeing timeouts or high latency
# - Increase gradually to find optimal rate
```

### 4. Connection Management

```properties
# Maximum connections per executor
spark.cdm.connect.origin.connections.maxPerHost=8
spark.cdm.connect.target.connections.maxPerHost=8

# Connection timeout
spark.cdm.connect.origin.socket.readTimeoutMillis=60000
spark.cdm.connect.target.socket.readTimeoutMillis=60000
```

### 5. Memory Optimization

```bash
# Spark memory configuration
spark-submit \
  --driver-memory 16g \
  --executor-memory 32g \
  --conf spark.memory.fraction=0.8 \
  --conf spark.memory.storageFraction=0.3 \
  --conf spark.sql.shuffle.partitions=200 \
  cassandra-data-migrator-assembly.jar \
  --properties-file cdm.properties
```

### 6. Performance Monitoring

Monitor these metrics during migration:

```bash
# Key metrics to watch:
# - Throughput (rows/sec)
# - Task duration
# - Executor memory usage
# - GC time
# - Network I/O
# - Cluster CPU/memory

# Access Spark UI at: http://spark-master:4040
```

### Performance Tuning Checklist

```properties
# Recommended starting configuration for 1TB dataset:

# Spark resources
spark.executor.instances=20
spark.executor.cores=4
spark.executor.memory=16g
spark.driver.memory=8g

# CDM performance
spark.cdm.perfops.numParts=240          # 20 executors × 4 cores × 3
spark.cdm.perfops.batchSize=5
spark.cdm.perfops.fetchSizeInRows=1000
spark.cdm.perfops.ratelimit.origin=50000
spark.cdm.perfops.ratelimit.target=50000

# Connections
spark.cdm.connect.origin.connections.maxPerHost=8
spark.cdm.connect.target.connections.maxPerHost=8

# Then tune based on:
# - Actual throughput
# - Resource utilization
# - Cluster health
```

## Monitoring

### Spark UI

The Spark UI provides comprehensive monitoring of the migration job:

```bash
# Access Spark UI (default port)
http://spark-driver-host:4040

# Key sections to monitor:
# 1. Jobs - Overall job progress
# 2. Stages - Stage-level execution details
# 3. Storage - Memory usage
# 4. Environment - Configuration
# 5. Executors - Executor metrics and logs
# 6. SQL - Query execution plans (if applicable)
```

**Key Metrics to Watch:**
- **Task Duration**: Should be consistent across tasks
- **Shuffle Read/Write**: Indicates data movement
- **GC Time**: High GC time indicates memory pressure
- **Failed Tasks**: Should be minimal
- **Data Read/Write Rates**: Throughput indicators

### CDM Application Logs

CDM provides detailed logging during migration:

```bash
# View Spark driver logs
tail -f /var/log/spark/spark-driver.log

# Example log output:
[INFO] Starting migration job for myapp.users
[INFO] Source cluster: dse-node1:9042
[INFO] Target cluster: hcd-node1:9042
[INFO] Partition count: 200
[INFO] Batch size: 5
[INFO] Processing partition 1/200...
[INFO] Processed 50000 rows, rate: 5000 rows/sec
[INFO] Migration progress: 25% complete
```

### Validation Output

After running DiffData, CDM generates a detailed validation report:

```bash
# Validation output location
# Check Spark driver logs or configured output path

# Example validation summary:
=== Validation Summary ===
Source Records: 10,000,000
Target Records: 10,000,000
Missing Records: 0
Mismatched Records: 0
Validation Status: PASSED

# If discrepancies found:
Missing Records: 150
Mismatched Records: 25
Details written to: /path/to/validation-errors.log
```

### Monitoring Best Practices

1. **Monitor Both Clusters**: Watch CPU, memory, and disk I/O on both source and target
2. **Track Throughput**: Calculate rows/sec and adjust rate limits if needed
3. **Watch for Errors**: Check Spark UI for failed tasks
4. **Monitor Network**: Ensure network bandwidth is sufficient
5. **Check Logs Regularly**: Look for warnings or errors in CDM logs

## Best Practices

### 1. Pre-Migration Checklist

**Schema Preparation:**
```bash
# 1. Export schema from source
cqlsh dse-node1 -e "DESCRIBE KEYSPACE myapp" > schema.cql

# 2. Create schema on target (may need modifications for compatibility)
cqlsh hcd-node1 < schema.cql

# 3. Verify schema matches
cqlsh dse-node1 -e "DESCRIBE TABLE myapp.users"
cqlsh hcd-node1 -e "DESCRIBE TABLE myapp.users"
```

**Connectivity Testing:**
```bash
# Test source connectivity
cqlsh dse-node1 -u cassandra -p cassandra -e "SELECT * FROM myapp.users LIMIT 1;"

# Test target connectivity
cqlsh hcd-node1 -u cassandra -p cassandra -e "SELECT * FROM myapp.users LIMIT 1;"

# Test from Spark cluster
spark-submit --class com.datastax.cdm.job.Migrate \
  --conf spark.cdm.connect.origin.host=dse-node1 \
  --conf spark.cdm.connect.target.host=hcd-node1 \
  cassandra-data-migrator-assembly.jar \
  --properties-file test-config.properties
```

### 2. Phased Migration Approach

**Phase 1: Pilot Migration (1-5% of data)**
```properties
# Test with small subset using token ranges
spark.cdm.tokenrange.partitionFile=pilot-ranges.csv
spark.cdm.tokenrange.partitionIndex=0

# Validate results
# Tune performance parameters
# Identify any issues
```

**Phase 2: Bulk Migration**
```bash
# Run full migration with optimized settings
# Use parallel jobs for large tables
# Monitor progress continuously
```

**Phase 3: Validation and Reconciliation**
```bash
# Run DiffData to identify discrepancies
# Use autocorrect to fix issues
# Perform final validation
```

### 3. Performance Optimization Strategy

**Start Conservative:**
```properties
spark.executor.instances=5
spark.executor.cores=2
spark.executor.memory=8g
spark.cdm.perfops.numParts=50
spark.cdm.perfops.batchSize=5
spark.cdm.perfops.ratelimit.origin=10000
spark.cdm.perfops.ratelimit.target=10000
```

**Monitor and Adjust:**
- Increase parallelism if CPU utilization is low
- Increase rate limits if clusters can handle more load
- Adjust batch size based on row size
- Scale executors based on data volume

### 4. Data Integrity Practices

**Always Enable:**
```properties
# Preserve original timestamps and TTL
spark.cdm.feature.ttl.enabled=true
spark.cdm.feature.writetime.enabled=true

# Enable validation
spark.cdm.autocorrect.missing=true
spark.cdm.autocorrect.mismatch=true
```

**Validation Workflow:**
```bash
# 1. Initial migration
spark-submit --class com.datastax.cdm.job.Migrate ...

# 2. Validation pass
spark-submit --class com.datastax.cdm.job.DiffData ...

# 3. Review discrepancies
# Check validation output for missing/mismatched records

# 4. Correction pass (if needed)
spark-submit --class com.datastax.cdm.job.DiffData \
  --conf spark.cdm.autocorrect.missing=true \
  --conf spark.cdm.autocorrect.mismatch=true ...

# 5. Final validation
spark-submit --class com.datastax.cdm.job.DiffData ...
```

### 5. Error Handling and Recovery

**Configure Error Limits:**
```properties
# Maximum errors before job fails
spark.cdm.perfops.errorLimit=1000

# Continue on errors (for large migrations)
spark.cdm.perfops.continueOnError=true
```

**Recovery Strategy:**
- CDM is idempotent - safe to re-run
- Use writetime filtering for incremental re-runs
- Review error logs to identify systematic issues
- Adjust guardrails if hitting size limits

### 6. Production Migration Checklist

- [ ] Schema created and verified on target
- [ ] Connectivity tested from Spark cluster
- [ ] Pilot migration completed successfully
- [ ] Performance parameters tuned
- [ ] Monitoring in place
- [ ] TTL and writetime preservation enabled
- [ ] Validation strategy defined
- [ ] Rollback plan documented
- [ ] Team trained on monitoring and troubleshooting
- [ ] Maintenance window scheduled (if needed)

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Out of Memory Errors

**Symptoms:**
- Executor failures with `OutOfMemoryError: Java heap space`
- Tasks failing repeatedly
- High GC time in Spark UI

**Solutions:**
```properties
# 1. Increase executor memory
spark.executor.memory=32g
spark.driver.memory=16g

# 2. Reduce batch size (fewer rows per batch)
spark.cdm.perfops.batchSize=3

# 3. Increase number of partitions (smaller tasks)
spark.cdm.perfops.numParts=1000

# 4. Adjust memory fractions
spark.memory.fraction=0.8
spark.memory.storageFraction=0.3
```

**Prevention:**
- Start with conservative batch sizes for large rows
- Monitor executor memory usage in Spark UI
- Use guardrails to skip oversized rows

#### Issue 2: Slow Migration Performance

**Symptoms:**
- Low throughput (< 1000 rows/sec)
- Long task durations
- Underutilized cluster resources

**Root Causes and Solutions:**

**A. Insufficient Parallelism:**
```properties
# Increase Spark parallelism
spark.executor.instances=30
spark.executor.cores=4
spark.cdm.perfops.numParts=500
```

**B. Conservative Rate Limits:**
```properties
# Increase rate limits (if clusters can handle it)
spark.cdm.perfops.ratelimit.origin=50000
spark.cdm.perfops.ratelimit.target=50000
```

**C. Small Batch Size:**
```properties
# Increase batch size for small rows
spark.cdm.perfops.batchSize=10
spark.cdm.perfops.fetchSizeInRows=2000
```

**D. Network Bottleneck:**
- Check network bandwidth between clusters
- Ensure Spark cluster has good connectivity to both Cassandra clusters
- Consider running Spark cluster closer to data centers

#### Issue 3: Connection Timeouts

**Symptoms:**
- `NoHostAvailableException`
- `OperationTimedOutException`
- Tasks failing with connection errors

**Solutions:**
```properties
# 1. Increase connection timeouts
spark.cdm.connect.origin.socket.readTimeoutMillis=120000
spark.cdm.connect.target.socket.readTimeoutMillis=120000

# 2. Increase retry attempts
spark.cdm.connect.origin.retry.maxAttempts=10
spark.cdm.connect.target.retry.maxAttempts=10

# 3. Reduce rate limits to ease cluster load
spark.cdm.perfops.ratelimit.origin=10000
spark.cdm.perfops.ratelimit.target=10000

# 4. Increase connection pool
spark.cdm.connect.origin.connections.maxPerHost=10
spark.cdm.connect.target.connections.maxPerHost=10
```

**Verification:**
```bash
# Test connectivity from Spark cluster
cqlsh source-host -u username -p password
cqlsh target-host -u username -p password

# Check cluster health
nodetool status
```

#### Issue 4: Data Validation Failures

**Symptoms:**
- DiffData reports missing or mismatched records
- Row counts don't match between source and target

**Common Causes:**

**A. TTL/Writetime Not Preserved:**
```properties
# Solution: Enable preservation
spark.cdm.feature.ttl.enabled=true
spark.cdm.feature.writetime.enabled=true
```

**B. Ongoing Writes to Source:**
- Solution: Use writetime filtering for incremental sync
- Or: Ensure source is read-only during migration

**C. Schema Incompatibility:**
- Verify column types match
- Check for missing columns in target
- Ensure compatible data types

**D. Rows Exceeding Guardrails:**
```bash
# Check logs for skipped rows
grep "guardrail" spark-driver.log

# Adjust guardrails if needed
spark.cdm.guardrail.colSizeInKB=2048
spark.cdm.guardrail.rowSizeInKB=20480
```

**Remediation:**
```bash
# Run validation with auto-correction
spark-submit --class com.datastax.cdm.job.DiffData \
  --conf spark.cdm.autocorrect.missing=true \
  --conf spark.cdm.autocorrect.mismatch=true \
  cassandra-data-migrator-assembly.jar \
  --properties-file cdm.properties
```

#### Issue 5: Spark Job Failures

**Symptoms:**
- Job fails with exceptions
- Tasks keep retrying and failing
- Executors lost

**Diagnostic Steps:**
```bash
# 1. Check Spark driver logs
tail -f /var/log/spark/spark-driver.log

# 2. Check executor logs in Spark UI
# Navigate to Executors tab → Click executor → View logs

# 3. Check Spark application logs
yarn logs -applicationId <app-id>  # For YARN
# OR
kubectl logs <spark-driver-pod>    # For Kubernetes
```

**Common Solutions:**
```properties
# 1. Increase task retry attempts
spark.task.maxFailures=10

# 2. Increase executor heartbeat timeout
spark.executor.heartbeatInterval=30s
spark.network.timeout=300s

# 3. Enable dynamic allocation (if supported)
spark.dynamicAllocation.enabled=true
spark.dynamicAllocation.minExecutors=5
spark.dynamicAllocation.maxExecutors=50
```

### Troubleshooting Checklist

When encountering issues:

1. **Check Spark UI** (http://spark-driver:4040)
   - Look for failed tasks
   - Check executor status
   - Review error messages

2. **Review Logs**
   - Spark driver logs
   - Executor logs
   - CDM application logs

3. **Verify Configuration**
   - Connection strings correct
   - Credentials valid
   - Schema names match

4. **Test Connectivity**
   - Can Spark cluster reach both Cassandra clusters?
   - Are firewalls configured correctly?
   - Is DNS resolution working?

5. **Check Cluster Health**
   - Source cluster healthy?
   - Target cluster healthy?
   - Sufficient resources available?

6. **Monitor Resources**
   - CPU utilization
   - Memory usage
   - Network bandwidth
   - Disk I/O

## Complete Migration Example

This comprehensive example demonstrates a full CDM migration workflow with validation:

```bash
#!/bin/bash
# complete_cdm_migration.sh - Production-ready CDM migration script

set -e

# Configuration
KEYSPACE="myapp"
TABLES=("users" "orders" "products")
CDM_JAR="cassandra-data-migrator-assembly.jar"
SPARK_MASTER="spark://spark-master:7077"
LOG_DIR="./cdm-logs"

# Create log directory
mkdir -p $LOG_DIR

echo "========================================="
echo "Starting CDM Migration"
echo "Keyspace: $KEYSPACE"
echo "Tables: ${TABLES[@]}"
echo "========================================="

for TABLE in "${TABLES[@]}"; do
  echo ""
  echo "Processing table: $KEYSPACE.$TABLE"
  echo "-----------------------------------------"
  
  # Create properties file with updated configuration
  cat > cdm-${TABLE}.properties << EOF
# Spark Configuration
spark.master=$SPARK_MASTER
spark.app.name=CDM-Migration-${KEYSPACE}-${TABLE}
spark.executor.instances=10
spark.executor.cores=4
spark.executor.memory=16g
spark.driver.memory=8g

# Source Cluster Configuration
spark.cdm.connect.origin.host=dse-node1,dse-node2,dse-node3
spark.cdm.connect.origin.port=9042
spark.cdm.connect.origin.username=cassandra
spark.cdm.connect.origin.password=cassandra
spark.cdm.connect.origin.localDC=dc1

# Target Cluster Configuration
spark.cdm.connect.target.host=hcd-node1,hcd-node2,hcd-node3
spark.cdm.connect.target.port=9042
spark.cdm.connect.target.username=cassandra
spark.cdm.connect.target.password=cassandra
spark.cdm.connect.target.localDC=datacenter1

# Schema Configuration
spark.cdm.schema.origin.keyspaceTable=${KEYSPACE}.${TABLE}
spark.cdm.schema.target.keyspaceTable=${KEYSPACE}.${TABLE}

# Performance Settings
spark.cdm.perfops.numParts=200
spark.cdm.perfops.batchSize=5
spark.cdm.perfops.fetchSizeInRows=1000
spark.cdm.perfops.ratelimit.origin=20000
spark.cdm.perfops.ratelimit.target=20000

# Data Integrity
spark.cdm.feature.ttl.enabled=true
spark.cdm.feature.writetime.enabled=true

# Error Handling
spark.cdm.perfops.errorLimit=1000
EOF
  
  # Step 1: Run migration
  echo "Step 1: Migrating data..."
  spark-submit \
    --class com.datastax.cdm.job.Migrate \
    --master $SPARK_MASTER \
    --driver-memory 8g \
    --executor-memory 16g \
    $CDM_JAR \
    --properties-file cdm-${TABLE}.properties \
    2>&1 | tee $LOG_DIR/migrate-${TABLE}.log
  
  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "✓ Migration completed successfully"
  else
    echo "✗ Migration failed - check logs"
    exit 1
  fi
  
  # Step 2: Validate data
  echo ""
  echo "Step 2: Validating data..."
  spark-submit \
    --class com.datastax.cdm.job.DiffData \
    --master $SPARK_MASTER \
    --driver-memory 8g \
    --executor-memory 16g \
    $CDM_JAR \
    --properties-file cdm-${TABLE}.properties \
    2>&1 | tee $LOG_DIR/validate-${TABLE}.log
  
  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "✓ Validation completed successfully"
  else
    echo "✗ Validation failed - check logs"
    exit 1
  fi
  
  echo ""
  echo "✓ Table $KEYSPACE.$TABLE migration complete"
  echo "-----------------------------------------"
done

echo ""
echo "========================================="
echo "All tables migrated successfully!"
echo "Logs available in: $LOG_DIR"
echo "========================================="
```

### Running the Migration

```bash
# Make script executable
chmod +x complete_cdm_migration.sh

# Run migration
./complete_cdm_migration.sh

# Monitor progress
tail -f cdm-logs/migrate-users.log

# Check validation results
grep -i "validation" cdm-logs/validate-*.log
```

## Summary

Cassandra Data Migrator (CDM) is a powerful, Spark-based tool for large-scale data migration between Cassandra clusters.

### Key Strengths

**✅ Performance & Scale:**
- Leverages Apache Spark for distributed processing
- Handles multi-TB datasets efficiently
- Parallel processing across multiple workers
- Configurable rate limiting and batch sizes

**✅ Data Integrity:**
- Preserves TTL and writetime values
- Built-in validation with DiffData operation
- Auto-correction capabilities
- Guardrails for data quality

**✅ Flexibility:**
- Column mapping and transformation
- Incremental migration support
- Partition-based parallel execution
- Resumable operations

**✅ Production-Ready:**
- Comprehensive error handling
- Detailed logging and monitoring
- Integration with Spark UI
- Open source with active community

### Considerations

**⚠️ Requirements:**
- Apache Spark infrastructure needed
- Spark expertise beneficial
- Resource-intensive (CPU, memory, network)
- Not suitable for real-time synchronization

**⚠️ Operational:**
- Batch processing model (not streaming)
- Requires careful performance tuning
- Network bandwidth critical
- Monitoring and troubleshooting skills needed

### Best Use Cases

**Ideal For:**
- ✅ Large-scale migrations (100GB+, multi-TB)
- ✅ Initial bulk data load in zero-downtime migrations
- ✅ Data transformation during migration
- ✅ Complex validation requirements
- ✅ Environments with existing Spark infrastructure

**Not Ideal For:**
- ❌ Real-time data synchronization
- ❌ Small datasets (< 100GB)
- ❌ Environments without Spark
- ❌ Simple table copies (use native tools)

### Integration Strategy

CDM works best as part of a comprehensive migration strategy:

1. **Schema Migration**: Use native CQL or DSBulk
2. **Bulk Data Load**: Use CDM for initial data migration
3. **Real-Time Sync**: Use ZDM proxy for ongoing synchronization
4. **Validation**: Use CDM's DiffData for verification
5. **Cutover**: Switch applications to target cluster

### Additional Resources

- **Official Documentation**: https://docs.datastax.com/en/data-migration/cassandra-data-migrator.html
- **GitHub Repository**: https://github.com/datastax/cassandra-data-migrator
- **Community Support**: DataStax Community Forums
- **Issue Tracking**: GitHub Issues

---

**Next:** [Zero Downtime Migration (ZDM) Approach](05-zdm-approach.md)