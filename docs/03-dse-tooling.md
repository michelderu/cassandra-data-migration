# DSE-Specific Tooling for Migration

## Table of Contents
1. [Overview](#overview)
2. [DSE Bulk Loader](#dse-bulk-loader)
3. [DSE OpsCenter](#dse-opscenter)
4. [DSE Backup Service](#dse-backup-service)
5. [DSE Specific Considerations](#dse-specific-considerations)
6. [Migration Strategies](#migration-strategies)

## Overview

DataStax Enterprise 5.1 includes proprietary tools designed for data management and migration. While these tools are optimized for DSE-to-DSE migrations, understanding their capabilities helps in planning DSE-to-HCD migrations.

### Key DSE Tools

| Tool | Purpose | HCD Compatible | Use in Migration |
|------|---------|----------------|------------------|
| DSE Bulk Loader | High-performance data loading | ⚠️ Partial | Export only |
| OpsCenter | Cluster management & backup | ❌ No | Backup/monitoring |
| DSE Backup Service | Automated backups | ❌ No | Pre-migration backup |
| DSE Analytics | Spark integration | ❌ No | Data transformation |

## DSE Bulk Loader

### Overview

DSE Bulk Loader (dsbulk) is a high-performance tool for loading and unloading data from DSE clusters. It's significantly faster than the native COPY command.

### Installation

```bash
# Download DSE Bulk Loader
wget https://downloads.datastax.com/dsbulk/dsbulk-1.10.0.tar.gz

# Extract
tar -xzf dsbulk-1.10.0.tar.gz

# Add to PATH
export PATH=$PATH:$PWD/dsbulk-1.10.0/bin

# Verify installation
dsbulk --version
# DataStax Bulk Loader v1.10.0
```

### Unloading Data (Export)

#### Basic Export

```bash
# Export entire table to CSV
dsbulk unload \
  -h dse-node1 \
  -k myapp \
  -t users \
  -url /export/users

# Output: Creates CSV files in /export/users/
```

#### Export with Options

```bash
# Export with custom settings
dsbulk unload \
  -h dse-node1 \
  -k myapp \
  -t users \
  -url /export/users \
  --connector.csv.delimiter '|' \
  --connector.csv.header true \
  --connector.csv.maxConcurrentFiles 4 \
  --executor.maxPerSecond 10000 \
  --driver.query.consistency LOCAL_QUORUM
```

#### Export to JSON

```bash
# Export as JSON
dsbulk unload \
  -h dse-node1 \
  -k myapp \
  -t users \
  -url /export/users \
  --connector.name json \
  --connector.json.prettyPrint true
```

#### Selective Export

```bash
# Export specific columns
dsbulk unload \
  -h dse-node1 \
  -k myapp \
  -t users \
  -url /export/users \
  --schema.query "SELECT user_id, username, email FROM myapp.users"

# Export with WHERE clause
dsbulk unload \
  -h dse-node1 \
  -k myapp \
  -t users \
  -url /export/users \
  --schema.query "SELECT * FROM myapp.users WHERE status = 'active' ALLOW FILTERING"
```

### Loading Data (Import)

#### Basic Import to HCD

```bash
# Import CSV to HCD cluster
dsbulk load \
  -h hcd-node1 \
  -k myapp \
  -t users \
  -url /export/users \
  --connector.csv.header true
```

#### Import with Performance Tuning

```bash
# High-performance import
dsbulk load \
  -h hcd-node1,hcd-node2,hcd-node3 \
  -k myapp \
  -t users \
  -url /export/users \
  --connector.csv.header true \
  --connector.csv.maxConcurrentFiles 8 \
  --executor.maxPerSecond 50000 \
  --executor.maxInFlight 2048 \
  --batch.mode PARTITION_KEY \
  --driver.query.consistency LOCAL_QUORUM
```

#### Import from JSON

```bash
# Import JSON files
dsbulk load \
  -h hcd-node1 \
  -k myapp \
  -t users \
  -url /export/users \
  --connector.name json
```

### Configuration File Approach

Create a configuration file for reusable settings:

```bash
# Create dsbulk.conf
cat > dsbulk.conf << 'EOF'
dsbulk {
  connector {
    name = csv
    csv {
      header = true
      delimiter = ","
      maxConcurrentFiles = 8
    }
  }
  
  executor {
    maxPerSecond = 50000
    maxInFlight = 2048
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
}
EOF

# Use configuration file
dsbulk unload -f dsbulk.conf -h dse-node1 -k myapp -t users -url /export/users
dsbulk load -f dsbulk.conf -h hcd-node1 -k myapp -t users -url /export/users
```

### Advanced Features

#### Monitoring Progress

```bash
# Enable detailed logging
dsbulk unload \
  -h dse-node1 \
  -k myapp \
  -t users \
  -url /export/users \
  --log.directory /var/log/dsbulk \
  --log.maxQueryStringLength 1000 \
  --log.verbosity 2

# Monitor log file
tail -f /var/log/dsbulk/operation.log
```

#### Error Handling

```bash
# Configure error handling
dsbulk load \
  -h hcd-node1 \
  -k myapp \
  -t users \
  -url /export/users \
  --log.directory /var/log/dsbulk \
  --executor.maxErrors 100 \
  --executor.maxErrorRatio 0.01
```

#### Dry Run

```bash
# Test without actually loading data
dsbulk load \
  -h hcd-node1 \
  -k myapp \
  -t users \
  -url /export/users \
  --dryRun true
```

### Performance Optimization

#### Parallel Processing

```bash
# Split large dataset into chunks
split -l 1000000 /export/users/data.csv /export/users/chunk_

# Load chunks in parallel
for chunk in /export/users/chunk_*; do
  dsbulk load \
    -h hcd-node1 \
    -k myapp \
    -t users \
    -url $chunk \
    --connector.csv.header false &
done
wait
```

#### Compression

```bash
# Export with compression
dsbulk unload \
  -h dse-node1 \
  -k myapp \
  -t users \
  -url /export/users \
  --connector.csv.compression gzip

# Import compressed files
dsbulk load \
  -h hcd-node1 \
  -k myapp \
  -t users \
  -url /export/users \
  --connector.csv.compression gzip
```

### Complete Migration Script

```bash
#!/bin/bash
# migrate_with_dsbulk.sh

set -e

KEYSPACE="myapp"
TABLES=("users" "orders" "products")
DSE_HOST="dse-node1"
HCD_HOST="hcd-node1,hcd-node2,hcd-node3"
EXPORT_DIR="/export"
LOG_DIR="/var/log/dsbulk"

echo "Starting DSE to HCD migration using dsbulk"

# Create directories
mkdir -p $EXPORT_DIR $LOG_DIR

# Export schema
echo "Exporting schema..."
cqlsh $DSE_HOST -e "DESC KEYSPACE $KEYSPACE" > $EXPORT_DIR/schema.cql

# Create keyspace on HCD
echo "Creating keyspace on HCD..."
cqlsh $(echo $HCD_HOST | cut -d',' -f1) < $EXPORT_DIR/schema.cql

# Migrate each table
for TABLE in "${TABLES[@]}"; do
  echo "Migrating table: $TABLE"
  
  # Export from DSE
  echo "  Exporting from DSE..."
  dsbulk unload \
    -h $DSE_HOST \
    -k $KEYSPACE \
    -t $TABLE \
    -url $EXPORT_DIR/$TABLE \
    --connector.csv.header true \
    --connector.csv.maxConcurrentFiles 8 \
    --executor.maxPerSecond 50000 \
    --log.directory $LOG_DIR/unload_$TABLE
  
  # Get row count from DSE
  DSE_COUNT=$(cqlsh $DSE_HOST -e "SELECT COUNT(*) FROM $KEYSPACE.$TABLE;" | grep -oP '\d+')
  echo "  DSE row count: $DSE_COUNT"
  
  # Import to HCD
  echo "  Importing to HCD..."
  dsbulk load \
    -h $HCD_HOST \
    -k $KEYSPACE \
    -t $TABLE \
    -url $EXPORT_DIR/$TABLE \
    --connector.csv.header true \
    --connector.csv.maxConcurrentFiles 8 \
    --executor.maxPerSecond 50000 \
    --executor.maxInFlight 2048 \
    --batch.mode PARTITION_KEY \
    --log.directory $LOG_DIR/load_$TABLE
  
  # Verify row count on HCD
  HCD_COUNT=$(cqlsh $(echo $HCD_HOST | cut -d',' -f1) -e "SELECT COUNT(*) FROM $KEYSPACE.$TABLE;" | grep -oP '\d+')
  echo "  HCD row count: $HCD_COUNT"
  
  # Compare counts
  if [ "$DSE_COUNT" -eq "$HCD_COUNT" ]; then
    echo "  ✅ Table $TABLE migrated successfully"
  else
    echo "  ❌ Row count mismatch for table $TABLE"
    exit 1
  fi
done

echo "Migration completed successfully!"
```

### Advantages

✅ **High Performance**: Much faster than native COPY command  
✅ **Parallel Processing**: Automatic parallelization  
✅ **Error Handling**: Robust error recovery  
✅ **Flexible Formats**: CSV, JSON support  
✅ **Monitoring**: Detailed logging and progress tracking  
✅ **HCD Compatible**: Works with HCD clusters

### Limitations

❌ **Point-in-Time**: Snapshot-based, doesn't capture ongoing writes  
❌ **Requires Staging**: Need disk space for export files  
❌ **Not Real-Time**: Batch processing only  
❌ **DSE License**: May require DSE license for some features

## DSE OpsCenter

### Overview

OpsCenter is DSE's centralized management and monitoring platform. While it cannot directly migrate to HCD, it's valuable for pre-migration tasks.

### Pre-Migration Use Cases

#### 1. Cluster Health Assessment

```bash
# Access OpsCenter
http://opscenter-host:8888

# Key metrics to review:
- Cluster health status
- Node performance
- Disk usage
- Compaction statistics
- Repair status
```

#### 2. Backup Before Migration

```bash
# Create backup via OpsCenter UI:
1. Navigate to Backup Service
2. Create new backup location
3. Configure backup schedule
4. Execute immediate backup
5. Verify backup completion
```

#### 3. Performance Baseline

```bash
# Capture performance metrics:
- Read/write latency
- Throughput (ops/sec)
- CPU and memory usage
- Disk I/O patterns
- Network traffic

# Export metrics for comparison with HCD
```

### OpsCenter Backup Service

#### Configuration

```yaml
# /etc/opscenter/clusters/<cluster-name>.conf
[backup_service]
enabled = True
backup_staging_directory = /var/lib/cassandra/backups
backup_location = s3://my-bucket/backups
```

#### Creating Backups

```bash
# Via OpsCenter API
curl -X POST http://opscenter-host:8888/backup \
  -H "Content-Type: application/json" \
  -d '{
    "backup_type": "full",
    "keyspaces": ["myapp"],
    "location": "s3://my-bucket/backups/migration"
  }'
```

#### Restoring Backups

```bash
# Restore to DSE (for rollback scenarios)
curl -X POST http://opscenter-host:8888/restore \
  -H "Content-Type: application/json" \
  -d '{
    "backup_id": "backup-20260216",
    "keyspaces": ["myapp"]
  }'
```

### Advantages

✅ **Centralized Management**: Single pane of glass  
✅ **Automated Backups**: Scheduled backup capability  
✅ **Monitoring**: Real-time cluster monitoring  
✅ **Historical Data**: Performance trends

### Limitations

❌ **DSE Only**: Cannot manage HCD clusters  
❌ **No Direct Migration**: Not a migration tool  
❌ **License Required**: Requires DSE license  
❌ **Complex Setup**: Additional infrastructure needed

## DSE Backup Service

### Overview

DSE's built-in backup service provides automated, point-in-time backups.

### Configuration

```yaml
# dse.yaml
backup_service_enabled: true
backup_staging_directory: /var/lib/cassandra/backups

# Backup locations
backup_locations:
  - type: local
    path: /backup/cassandra
  - type: s3
    bucket: my-backup-bucket
    region: us-east-1
```

### Creating Backups

```bash
# Full backup
dsetool backup create \
  --keyspace myapp \
  --type full \
  --location /backup/cassandra

# Incremental backup
dsetool backup create \
  --keyspace myapp \
  --type incremental \
  --location /backup/cassandra
```

### Listing Backups

```bash
# List available backups
dsetool backup list \
  --location /backup/cassandra

# Output:
# Backup ID: backup-20260216-120000
# Type: full
# Keyspace: myapp
# Size: 10.5 GB
# Status: completed
```

### Restoring Backups

```bash
# Restore backup
dsetool backup restore \
  --backup-id backup-20260216-120000 \
  --keyspace myapp \
  --location /backup/cassandra
```

## DSE Specific Considerations

### 1. DSE Search (Solr)

DSE Search indexes are **not compatible** with HCD. Migration strategy:

```bash
# Option 1: Rebuild indexes on HCD using external Solr
# Option 2: Use Elasticsearch or other search solution
# Option 3: Implement application-level search

# Export search schema
dsetool create_core myapp.users schema=schema.xml

# Migrate to external search platform
```

### 2. DSE Analytics (Spark)

DSE Analytics integration is **not available** in HCD:

```bash
# Option 1: Use standalone Spark cluster
# Option 2: Use Spark with Cassandra connector
# Option 3: Alternative analytics platform (Presto, Trino)

# Export Spark job configurations
# Modify to use Cassandra connector
```

### 3. DSE Graph

DSE Graph is **not included** in HCD:

```bash
# Option 1: Migrate to JanusGraph
# Option 2: Use Neo4j or other graph database
# Option 3: Implement graph logic in application

# Export graph data
dse gremlin-console
gremlin> graph = DseGraph.traversal()
gremlin> graph.V().toList()
```

### 4. DSE Authentication

DSE authentication must be reconfigured for HCD:

```yaml
# DSE authentication (dse.yaml)
authentication_options:
  enabled: true
  default_scheme: internal
  scheme_permissions: true

# HCD authentication (cassandra.yaml)
authenticator: PasswordAuthenticator
authorizer: CassandraAuthorizer
```

#### Migration Steps

```bash
# 1. Export DSE users and roles
cqlsh -e "SELECT * FROM dse_security.role_members;" > roles.csv
cqlsh -e "SELECT * FROM dse_security.role_permissions;" > permissions.csv

# 2. Create users on HCD
cqlsh hcd-node1 -e "CREATE ROLE myuser WITH PASSWORD = 'password' AND LOGIN = true;"

# 3. Grant permissions
cqlsh hcd-node1 -e "GRANT ALL ON KEYSPACE myapp TO myuser;"
```

### 5. System Tables

DSE system tables differ from standard Cassandra:

```sql
-- DSE-specific system tables (not in HCD)
dse_system
dse_security
dse_leases
dse_perf
solr_admin

-- Migration: Export relevant data before migration
-- Most system tables don't need migration
```

## Migration Strategies

### Strategy 1: DSBulk + Validation

```bash
# 1. Export with dsbulk
dsbulk unload -h dse-node1 -k myapp -t users -url /export/users

# 2. Load to HCD
dsbulk load -h hcd-node1 -k myapp -t users -url /export/users

# 3. Validate
./validate_migration.sh myapp users
```

### Strategy 2: OpsCenter Backup + Manual Restore

```bash
# 1. Create backup via OpsCenter
# 2. Download backup files
# 3. Convert to HCD format (if needed)
# 4. Use sstableloader to load
```

### Strategy 3: Hybrid Approach

```bash
# 1. Use OpsCenter for monitoring and backup
# 2. Use dsbulk for data export/import
# 3. Use ZDM for zero-downtime cutover
# 4. Validate with custom scripts
```

## Best Practices

### 1. Pre-Migration Backup

```bash
# Always backup before migration
dsetool backup create \
  --keyspace myapp \
  --type full \
  --location s3://backup-bucket/pre-migration
```

### 2. Test with Subset

```bash
# Test migration with small dataset first
dsbulk unload \
  -h dse-node1 \
  -k myapp \
  -t users \
  -url /export/test \
  --schema.query "SELECT * FROM myapp.users LIMIT 10000"
```

### 3. Monitor Performance

```bash
# Monitor during migration
watch -n 5 'nodetool tpstats'
watch -n 5 'nodetool compactionstats'
```

### 4. Validate Thoroughly

```bash
# Compare row counts
# Compare sample data
# Test application queries
# Verify performance
```

## Summary

DSE-specific tooling provides powerful capabilities for data management:

- **DSBulk**: Recommended for high-performance data export/import
- **OpsCenter**: Valuable for pre-migration assessment and backup
- **DSE Backup Service**: Essential for creating safety backups
- **DSE Features**: Require separate migration strategies (Search, Analytics, Graph)

For DSE to HCD migration, DSBulk is the most practical DSE tool, while OpsCenter and Backup Service support pre-migration preparation.

---

**Next:** [Zero Downtime Migration (ZDM) Approach](04-zdm-approach.md)