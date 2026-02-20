# Cassandra Data Migrator (CDM) Approach

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Migration Strategies](#migration-strategies)
6. [Advanced Features](#advanced-features)
7. [Performance Tuning](#performance-tuning)
8. [Monitoring](#monitoring)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

## Overview

Cassandra Data Migrator (CDM) is an Apache Spark-based tool designed for large-scale data migration between Cassandra clusters. It's particularly effective for bulk data migration and can be combined with other tools for zero-downtime scenarios.

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

```mermaid
graph TD
    subgraph Source[Source Cluster]
        SN1[Node 1]
        SN2[Node 2]
        SN3[Node 3]
    end
    
    subgraph Spark[Spark Processing & Transformation]
        Process[- Read from source<br/>- Transform optional<br/>- Validate<br/>- Write to target]
    end
    
    subgraph Target[Target HCD Cluster]
        TN1[Node 1]
        TN2[Node 2]
        TN3[Node 3]
    end
    
    SN1 -->|Read Data| Process
    SN2 -->|Read Data| Process
    SN3 -->|Read Data| Process
    
    Process -->|Write Data| TN1
    Process -->|Write Data| TN2
    Process -->|Write Data| TN3
    
    style Source fill:#fff4e6
    style Spark fill:#e3f2fd
    style Target fill:#e8f5e9
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

#### 3. Source Cluster
- Provides data to migrate
- Supports: Apache Cassandra 3.11/4.0/4.1 or DSE 5.1/6.8/6.9
- Remains operational during migration
- No modifications required

#### 4. Target Cluster (HCD)
- Receives migrated data
- Schema must exist before migration
- Can be operational during migration

## Installation

### Prerequisites

```bash
# Required software
- Apache Spark 3.x
- Java 11 or higher
- Scala 2.12
- Network connectivity to both clusters

# Recommended resources
- 4+ CPU cores per worker
- 16+ GB RAM per worker
- Fast network connection
```

### Method 1: Pre-built JAR

```bash
# Download CDM JAR
wget https://github-registry-files.githubusercontent.com/538937619/ffa9af80-ea71-11f0-87fb-f5d6da70f424?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAVCODYLSA53PQK4ZA%2F20260219%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260219T143142Z&X-Amz-Expires=300&X-Amz-Signature=829b98c4fa80e124ecbf1c973186ed920db83e6050e9747c334f22c45833d124&X-Amz-SignedHeaders=host&response-content-disposition=filename%3Dcassandra-data-migrator-5.7.2.jar&response-content-type=application%2Foctet-stream
# Verify download
ls -lh cassandra-data-migrator-4.0.0.jar
```

### Method 2: Build from Source

```bash
# Clone repository
git clone https://github.com/datastax/cassandra-data-migrator.git
cd cassandra-data-migrator

# Build with Maven
mvn clean package -DskipTests

# JAR location
ls -lh target/cassandra-data-migrator-*.jar
```

### Method 3: Docker

```bash
# Pull Docker image
docker pull datastax/cassandra-data-migrator:4.0.0

# Run migration
docker run -v $(pwd)/config:/config \
  datastax/cassandra-data-migrator:4.0.0 \
  --conf /config/cdm.properties
```

## Configuration

### Basic Configuration

```properties
# cdm.properties

# Spark configuration
spark.master=local[*]
spark.app.name=CDM-Migration

# Source cluster (Cassandra or DSE)
spark.origin.host=dse-node1,dse-node2,dse-node3
spark.origin.port=9042
spark.origin.username=cassandra
spark.origin.password=cassandra
spark.origin.keyspace=myapp
spark.origin.table=users

# Target cluster (HCD)
spark.target.host=hcd-node1,hcd-node2,hcd-node3
spark.target.port=9042
spark.target.username=cassandra
spark.target.password=cassandra
spark.target.keyspace=myapp
spark.target.table=users

# Migration settings
spark.cdm.schema.origin.column.names.to.target=*
spark.cdm.perfops.numParts=100
spark.cdm.perfops.batchSize=5
```

### Advanced Configuration

```properties
# cdm-advanced.properties

# Spark configuration
spark.master=spark://spark-master:7077
spark.app.name=CDM-Production-Migration
spark.executor.instances=10
spark.executor.cores=4
spark.executor.memory=16g
spark.driver.memory=8g

# Source cluster (Cassandra or DSE)
spark.origin.host=dse-node1,dse-node2,dse-node3
spark.origin.port=9042
spark.origin.username=cassandra
spark.origin.password=cassandra
spark.origin.keyspace=myapp
spark.origin.table=users
spark.origin.connection.localDC=dc1
spark.origin.connection.consistency=LOCAL_QUORUM

# Target cluster (HCD)
spark.target.host=hcd-node1,hcd-node2,hcd-node3
spark.target.port=9042
spark.target.username=cassandra
spark.target.password=cassandra
spark.target.keyspace=myapp
spark.target.table=users
spark.target.connection.localDC=datacenter1
spark.target.connection.consistency=LOCAL_QUORUM

# Performance tuning
spark.cdm.perfops.numParts=200
spark.cdm.perfops.batchSize=10
spark.cdm.perfops.fetchSizeInRows=1000
spark.cdm.perfops.ratelimit.origin=10000
spark.cdm.perfops.ratelimit.target=10000

# Data validation
spark.cdm.autocorrect.missing=true
spark.cdm.autocorrect.mismatch=true

# Error handling
spark.cdm.perfops.errorLimit=1000

# Filtering
spark.cdm.filter.cassandra.partition.min=0
spark.cdm.filter.cassandra.partition.max=100
```

### SSL Configuration

```properties
# cdm-ssl.properties

# Source SSL
spark.origin.connection.ssl.enabled=true
spark.origin.connection.ssl.truststore.path=/path/to/origin-truststore.jks
spark.origin.connection.ssl.truststore.password=truststore_password
spark.origin.connection.ssl.keystore.path=/path/to/origin-keystore.jks
spark.origin.connection.ssl.keystore.password=keystore_password

# Target SSL
spark.target.connection.ssl.enabled=true
spark.target.connection.ssl.truststore.path=/path/to/target-truststore.jks
spark.target.connection.ssl.truststore.password=truststore_password
spark.target.connection.ssl.keystore.path=/path/to/target-keystore.jks
spark.target.connection.ssl.keystore.password=keystore_password
```

## Migration Strategies

### Strategy 1: Full Table Migration

```bash
# Basic full table migration
spark-submit \
  --class com.datastax.cdm.job.Migrate \
  --master spark://spark-master:7077 \
  --conf spark.executor.instances=10 \
  cassandra-data-migrator-4.0.0.jar \
  --properties-file cdm.properties
```

### Strategy 2: Partition Range Migration

```properties
# Migrate specific partition range
spark.cdm.filter.cassandra.partition.min=0
spark.cdm.filter.cassandra.partition.max=25

# Run multiple jobs in parallel for different ranges
# Job 1: 0-25
# Job 2: 26-50
# Job 3: 51-75
# Job 4: 76-100
```

```bash
# Run parallel migrations
for range in "0-25" "26-50" "51-75" "76-100"; do
  MIN=$(echo $range | cut -d'-' -f1)
  MAX=$(echo $range | cut -d'-' -f2)
  
  spark-submit \
    --class com.datastax.cdm.job.Migrate \
    --master spark://spark-master:7077 \
    --conf spark.cdm.filter.cassandra.partition.min=$MIN \
    --conf spark.cdm.filter.cassandra.partition.max=$MAX \
    cassandra-data-migrator-4.0.0.jar \
    --properties-file cdm.properties &
done
wait
```

### Strategy 3: Incremental Migration

```properties
# First run: Full migration
spark.cdm.feature.writetime.enabled=false

# Subsequent runs: Only new/updated data
spark.cdm.feature.writetime.enabled=true
spark.cdm.feature.writetime.filter.min=1708099200000000  # Timestamp in microseconds
```

### Strategy 4: Column Subset Migration

```properties
# Migrate only specific columns
spark.cdm.schema.origin.column.names.to.target=user_id,username,email,created_at

# Exclude columns
spark.cdm.schema.origin.column.names.to.exclude=internal_field,deprecated_column
```

### Strategy 5: Data Transformation

```properties
# Enable transformation
spark.cdm.transform.custom.class=com.example.MyTransformer

# Custom transformer implementation
# Implement: com.datastax.cdm.feature.Transformer interface
```

## Advanced Features

### 1. Data Validation

```properties
# Enable validation
spark.cdm.autocorrect.missing=true
spark.cdm.autocorrect.mismatch=true

# Validation modes:
# - missing: Detect and copy missing rows
# - mismatch: Detect and fix data mismatches
```

```bash
# Run validation-only job
spark-submit \
  --class com.datastax.cdm.job.DiffData \
  --master spark://spark-master:7077 \
  cassandra-data-migrator-4.0.0.jar \
  --properties-file cdm.properties
```

### 2. Guardrails

```properties
# Set guardrails to prevent issues
spark.cdm.guardrail.colSizeInKB=1024
spark.cdm.guardrail.rowSizeInKB=10240

# Rows exceeding guardrails are logged but not migrated
```

### 3. TTL and Writetime Preservation

```properties
# Preserve TTL
spark.cdm.feature.ttl.enabled=true

# Preserve writetime
spark.cdm.feature.writetime.enabled=true

# Both are critical for accurate migration
```

### 4. Counter Table Support

```properties
# Enable counter table migration
spark.cdm.feature.counter.enabled=true

# Counter tables require special handling
```

### 5. Large Field Handling

```properties
# Handle large fields (blobs, text)
spark.cdm.feature.largefield.enabled=true
spark.cdm.feature.largefield.sizeInKB=1024
```

## Performance Tuning

### 1. Parallelism

```properties
# Increase parallelism
spark.cdm.perfops.numParts=500  # More partitions = more parallelism

# Spark executor configuration
spark.executor.instances=20
spark.executor.cores=4
spark.executor.memory=16g
```

### 2. Batch Size

```properties
# Optimize batch size
spark.cdm.perfops.batchSize=10  # Rows per batch
spark.cdm.perfops.fetchSizeInRows=1000  # Fetch size from source
```

### 3. Rate Limiting

```properties
# Prevent overwhelming clusters
spark.cdm.perfops.ratelimit.origin=20000  # Reads per second
spark.cdm.perfops.ratelimit.target=20000  # Writes per second
```

### 4. Connection Pooling

```properties
# Optimize connections
spark.origin.connection.connections_per_executor_max=8
spark.target.connection.connections_per_executor_max=8
```

### 5. Memory Management

```bash
# Increase driver and executor memory
spark-submit \
  --driver-memory 16g \
  --executor-memory 32g \
  --conf spark.memory.fraction=0.8 \
  --conf spark.memory.storageFraction=0.3 \
  cassandra-data-migrator-4.0.0.jar \
  --properties-file cdm.properties
```

## Monitoring

### Spark UI

```bash
# Access Spark UI
http://spark-master:4040

# Key metrics:
# - Active jobs
# - Completed stages
# - Task duration
# - Executor metrics
# - Storage memory
```

### CDM Metrics

```bash
# CDM logs show progress
# Example output:
[INFO] Migration progress: 1000000 rows processed
[INFO] Read rate: 50000 rows/sec
[INFO] Write rate: 45000 rows/sec
[INFO] Errors: 0
[INFO] Estimated completion: 2 hours
```

### Custom Monitoring Script

```bash
#!/bin/bash
# monitor_cdm.sh

SPARK_MASTER="spark://spark-master:7077"
APP_NAME="CDM-Migration"

while true; do
  # Get application status
  STATUS=$(curl -s http://spark-master:8080/json/ | \
    jq -r ".activeapps[] | select(.name==\"$APP_NAME\") | .state")
  
  if [ "$STATUS" == "RUNNING" ]; then
    echo "$(date): Migration in progress"
    
    # Get executor metrics
    curl -s http://spark-master:4040/api/v1/applications/$APP_ID/executors | \
      jq '.[] | {id, totalCores, memoryUsed, diskUsed}'
  else
    echo "$(date): Migration completed or not running"
    break
  fi
  
  sleep 60
done
```

### Validation Report

```bash
# After migration, check validation report
cat cdm-validation-report.txt

# Example report:
Total rows in source: 10000000
Total rows in target: 10000000
Missing rows: 0
Mismatched rows: 0
Migration status: SUCCESS
```

## Best Practices

### 1. Pre-Migration Preparation

```bash
# 1. Create schema on target
cqlsh hcd-node1 < schema.cql

# 2. Verify connectivity
cqlsh dse-node1 -e "SELECT * FROM myapp.users LIMIT 1;"
cqlsh hcd-node1 -e "SELECT * FROM myapp.users LIMIT 1;"

# 3. Test with small dataset
# Use partition range filter for testing
```

### 2. Staged Migration

```bash
# Stage 1: Migrate 10% of data
spark.cdm.filter.cassandra.partition.min=0
spark.cdm.filter.cassandra.partition.max=10

# Stage 2: Validate and tune
# Run validation job
# Adjust performance settings

# Stage 3: Migrate remaining data
spark.cdm.filter.cassandra.partition.min=11
spark.cdm.filter.cassandra.partition.max=100
```

### 3. Resource Allocation

```properties
# For 1TB dataset:
spark.executor.instances=20
spark.executor.cores=4
spark.executor.memory=16g
spark.cdm.perfops.numParts=500

# Adjust based on:
# - Dataset size
# - Available resources
# - Network bandwidth
# - Cluster capacity
```

### 4. Error Handling

```properties
# Set error limits
spark.cdm.perfops.errorLimit=1000

# Log errors for review
spark.cdm.perfops.errorLog.enabled=true
spark.cdm.perfops.errorLog.path=/var/log/cdm/errors.log
```

### 5. Validation Strategy

```bash
# 1. Run migration
spark-submit ... Migrate ...

# 2. Run validation
spark-submit ... DiffData ...

# 3. Fix discrepancies
spark-submit ... Migrate ... (with autocorrect enabled)

# 4. Final validation
spark-submit ... DiffData ...
```

## Troubleshooting

### Issue 1: Out of Memory

```bash
# Symptoms
# - Executor failures
# - "OutOfMemoryError: Java heap space"

# Solutions
# 1. Increase executor memory
spark.executor.memory=32g

# 2. Reduce batch size
spark.cdm.perfops.batchSize=5

# 3. Increase number of partitions
spark.cdm.perfops.numParts=1000
```

### Issue 2: Slow Migration

```bash
# Symptoms
# - Long migration time

# Solutions
# 1. Increase parallelism
spark.executor.instances=30
spark.cdm.perfops.numParts=500

# 2. Optimize batch size
spark.cdm.perfops.batchSize=10

# 3. Check network bandwidth
# 4. Verify cluster health
```

### Issue 3: Connection Timeouts

```bash
# Symptoms
# - "Connection timeout"
# - "NoHostAvailableException"

# Solutions
# 1. Increase timeout
spark.origin.connection.timeout=30000
spark.target.connection.timeout=30000

# 2. Check network connectivity
# 3. Verify cluster health
# 4. Reduce rate limits
```

### Issue 4: Data Mismatches

```bash
# Symptoms
# - Validation reports mismatches
# - Different row counts

# Solutions
# 1. Enable autocorrect
spark.cdm.autocorrect.missing=true
spark.cdm.autocorrect.mismatch=true

# 2. Check TTL/writetime preservation
spark.cdm.feature.ttl.enabled=true
spark.cdm.feature.writetime.enabled=true

# 3. Verify schema compatibility
# 4. Check for ongoing writes to source
```

### Issue 5: Spark Job Failures

```bash
# Symptoms
# - Job fails with errors
# - Tasks keep retrying

# Solutions
# 1. Check Spark logs
tail -f /var/log/spark/spark-worker.log

# 2. Verify configuration
# 3. Check resource availability
# 4. Review error messages in Spark UI
```

## Complete Migration Example

```bash
#!/bin/bash
# complete_cdm_migration.sh

set -e

KEYSPACE="myapp"
TABLES=("users" "orders" "products")
CDM_JAR="cassandra-data-migrator-4.0.0.jar"
SPARK_MASTER="spark://spark-master:7077"

echo "Starting CDM migration"

for TABLE in "${TABLES[@]}"; do
  echo "Migrating table: $TABLE"
  
  # Create properties file
  cat > cdm-${TABLE}.properties << EOF
spark.master=$SPARK_MASTER
spark.app.name=CDM-${TABLE}
spark.executor.instances=10
spark.executor.cores=4
spark.executor.memory=16g

spark.origin.host=dse-node1,dse-node2,dse-node3
spark.origin.port=9042
spark.origin.username=cassandra
spark.origin.password=cassandra
spark.origin.keyspace=$KEYSPACE
spark.origin.table=$TABLE

spark.target.host=hcd-node1,hcd-node2,hcd-node3
spark.target.port=9042
spark.target.username=cassandra
spark.target.password=cassandra
spark.target.keyspace=$KEYSPACE
spark.target.table=$TABLE

spark.cdm.perfops.numParts=200
spark.cdm.perfops.batchSize=10
spark.cdm.feature.ttl.enabled=true
spark.cdm.feature.writetime.enabled=true
EOF
  
  # Run migration
  spark-submit \
    --class com.datastax.cdm.job.Migrate \
    --master $SPARK_MASTER \
    $CDM_JAR \
    --properties-file cdm-${TABLE}.properties
  
  # Validate
  echo "Validating table: $TABLE"
  spark-submit \
    --class com.datastax.cdm.job.DiffData \
    --master $SPARK_MASTER \
    $CDM_JAR \
    --properties-file cdm-${TABLE}.properties
  
  echo "Table $TABLE migration complete"
done

echo "All tables migrated successfully"
```

## Summary

CDM provides powerful capabilities for large-scale data migration:

**Advantages:**
- ✅ High performance with Spark
- ✅ Parallel processing
- ✅ Built-in validation
- ✅ Data transformation support
- ✅ Resumable migrations
- ✅ Open source

**Considerations:**
- Requires Spark infrastructure
- Not real-time (batch processing)
- Learning curve for Spark
- Resource intensive

**Best For:**
- Large datasets (multi-TB)
- Initial bulk data load
- Complex transformations
- Environments with Spark

**Combine With:**
- ZDM for real-time sync after bulk load
- Native tools for schema migration
- Custom validation scripts

---

**Next:** [Tool Comparison and Decision Matrix](06-comparison-matrix.md)