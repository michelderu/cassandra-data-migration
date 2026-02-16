# Native Tooling for Data Migration

## Table of Contents
1. [Overview](#overview)
2. [SSTableLoader](#sstableloader)
3. [Nodetool Snapshot and Restore](#nodetool-snapshot-and-restore)
4. [COPY Command](#copy-command)
5. [CQL COPY TO/FROM](#cql-copy-tofrom)
6. [Backup and Restore](#backup-and-restore)
7. [Best Practices](#best-practices)

## Overview

Native Cassandra/DSE tooling provides built-in capabilities for data migration. While these tools weren't specifically designed for zero-downtime migrations, they can be combined strategically to achieve minimal downtime scenarios.

### Tool Comparison Quick Reference

| Tool | Use Case | Downtime | Complexity | Performance |
|------|----------|----------|------------|-------------|
| SSTableLoader | Bulk data load | Low | Medium | High |
| Nodetool Snapshot | Backup/restore | High | Low | High |
| COPY Command | Small datasets | Medium | Low | Low |
| CQL COPY | Development/test | Medium | Low | Low |

## SSTableLoader

### Overview

[`sstableloader`](https://cassandra.apache.org/doc/latest/tools/sstable/sstableloader.html) is a bulk loading tool that streams SSTables to a live cluster. It's one of the most efficient native tools for large-scale data migration.

### How It Works

```
┌─────────────────┐
│  Source DSE     │
│  SSTables       │
└────────┬────────┘
         │
         │ 1. Export SSTables
         ▼
┌─────────────────┐
│  File System    │
│  (Staging)      │
└────────┬────────┘
         │
         │ 2. Stream via sstableloader
         ▼
┌─────────────────┐
│  Target HCD     │
│  Cluster        │
└─────────────────┘
```

### Prerequisites

- Access to DSE SSTables (filesystem level)
- Network connectivity to target HCD cluster
- Sufficient disk space for staging
- Schema must exist on target cluster

### Step-by-Step Process

#### 1. Create Schema on Target

```cql
-- On HCD cluster
CREATE KEYSPACE IF NOT EXISTS myapp
WITH replication = {
  'class': 'NetworkTopologyStrategy',
  'datacenter1': 3
};

CREATE TABLE myapp.users (
  user_id uuid PRIMARY KEY,
  username text,
  email text,
  created_at timestamp
);
```

#### 2. Take Snapshot on Source DSE

```bash
# On DSE node
nodetool snapshot myapp -t migration_snapshot

# Snapshot location
# /var/lib/cassandra/data/myapp/users-<uuid>/snapshots/migration_snapshot/
```

#### 3. Copy SSTables to Staging Area

```bash
# Create staging directory
mkdir -p /staging/myapp/users

# Copy SSTables from snapshot
cp /var/lib/cassandra/data/myapp/users-*/snapshots/migration_snapshot/* \
   /staging/myapp/users/

# Verify files
ls -lh /staging/myapp/users/
# Should see: *-Data.db, *-Index.db, *-Statistics.db, etc.
```

#### 4. Run SSTableLoader

```bash
# Basic usage
sstableloader \
  -d hcd-node1,hcd-node2,hcd-node3 \
  /staging/myapp/users

# With options for production
sstableloader \
  -d hcd-node1,hcd-node2,hcd-node3 \
  --username cassandra \
  --password cassandra \
  --ssl-storage-port 7001 \
  --throttle 16 \
  --connections-per-host 4 \
  /staging/myapp/users
```

#### 5. Monitor Progress

```bash
# SSTableLoader output shows progress
Established 3 connections
Streaming session ID: 12345678-1234-1234-1234-123456789012
progress: [hcd-node1 1/3 (33%)] [hcd-node2 1/3 (33%)] [hcd-node3 1/3 (33%)]
progress: [hcd-node1 2/3 (66%)] [hcd-node2 2/3 (66%)] [hcd-node3 2/3 (66%)]
progress: [hcd-node1 3/3 (100%)] [hcd-node2 3/3 (100%)] [hcd-node3 3/3 (100%)]
```

### SSTableLoader Options

```bash
# Connection options
-d, --nodes <host1,host2,...>    # Target cluster nodes
-p, --port <port>                # Native transport port (default: 9042)
--ssl-storage-port <port>        # SSL storage port (default: 7001)

# Authentication
-u, --username <username>        # Username for authentication
-pw, --password <password>       # Password for authentication
--ssl-truststore <path>          # SSL truststore path
--ssl-truststore-password <pwd>  # SSL truststore password

# Performance tuning
-t, --throttle <mbits>           # Throttle speed in Mbits (default: unlimited)
-cph, --connections-per-host <n> # Connections per host (default: 1)
-i, --ignore <list>              # Comma-separated list of nodes to ignore

# Other options
-v, --verbose                    # Verbose output
--no-progress                    # Disable progress reporting
```

### Performance Tuning

#### Throttling

```bash
# Limit to 50 Mbits/sec to avoid overwhelming network
sstableloader -d hcd-node1 --throttle 50 /staging/myapp/users
```

#### Parallel Connections

```bash
# Increase connections for faster loading
sstableloader -d hcd-node1 --connections-per-host 8 /staging/myapp/users
```

#### Batch Processing

```bash
# Process multiple tables in parallel
for table in users orders products; do
  sstableloader -d hcd-node1 /staging/myapp/$table &
done
wait
```

### Advantages

✅ **High Performance**: Direct SSTable streaming is very efficient  
✅ **No Application Changes**: Works at storage layer  
✅ **Bulk Loading**: Handles large datasets well  
✅ **Parallel Processing**: Can load multiple tables simultaneously  
✅ **Network Efficient**: Compressed streaming

### Limitations

❌ **Requires Filesystem Access**: Need access to DSE data directories  
❌ **Schema Must Exist**: Target schema must be created first  
❌ **Point-in-Time**: Snapshot is static, doesn't capture ongoing writes  
❌ **Format Compatibility**: May need SSTable format conversion  
❌ **No Incremental Updates**: Full table load only

### Zero-Downtime Strategy with SSTableLoader

```
Phase 1: Initial Bulk Load
├─ Take snapshot of DSE
├─ Load to HCD via sstableloader
└─ Validate data

Phase 2: Incremental Sync
├─ Use CDM or dual-write for new data
├─ Catch up on changes since snapshot
└─ Validate consistency

Phase 3: Cutover
├─ Enable proxy or switch application
├─ Monitor both clusters
└─ Decommission DSE
```

## Nodetool Snapshot and Restore

### Overview

[`nodetool snapshot`](https://cassandra.apache.org/doc/latest/tools/nodetool/snapshot.html) creates hard links to SSTables, providing a consistent point-in-time backup.

### Creating Snapshots

```bash
# Snapshot entire cluster
nodetool snapshot

# Snapshot specific keyspace
nodetool snapshot myapp

# Snapshot with custom tag
nodetool snapshot -t migration_20260216 myapp

# Snapshot specific table
nodetool snapshot -kt myapp.users
```

### Listing Snapshots

```bash
# List all snapshots
nodetool listsnapshots

# Output example:
Snapshot Details:
Snapshot name  Keyspace   Column Family  True size  Size on disk
migration_20260216  myapp  users  1.5 GB  1.5 GB
```

### Clearing Snapshots

```bash
# Clear specific snapshot
nodetool clearsnapshot -t migration_20260216

# Clear all snapshots for keyspace
nodetool clearsnapshot myapp

# Clear all snapshots
nodetool clearsnapshot --all
```

### Restore Process

```bash
# 1. Stop Cassandra/DSE
sudo systemctl stop cassandra

# 2. Clear existing data
rm -rf /var/lib/cassandra/data/myapp/users-*/

# 3. Copy snapshot data
cp -r /var/lib/cassandra/data/myapp/users-*/snapshots/migration_20260216/* \
      /var/lib/cassandra/data/myapp/users-*/

# 4. Change ownership
chown -R cassandra:cassandra /var/lib/cassandra/data/myapp/

# 5. Start Cassandra
sudo systemctl start cassandra

# 6. Run repair
nodetool repair myapp
```

### Advantages

✅ **Fast Snapshot Creation**: Hard links are instant  
✅ **Consistent Backup**: Point-in-time consistency  
✅ **Built-in Tool**: No additional software needed  
✅ **Space Efficient**: Hard links don't duplicate data

### Limitations

❌ **Requires Downtime**: Restore requires cluster stop  
❌ **Manual Process**: No automation built-in  
❌ **Same Version**: Best for same Cassandra version  
❌ **Local Only**: Snapshots are node-local

## COPY Command

### Overview

The [`COPY`](https://cassandra.apache.org/doc/latest/tools/cqlsh.html#copy-to) command in cqlsh exports/imports data in CSV format.

### Export Data (COPY TO)

```cql
-- Basic export
COPY myapp.users TO '/tmp/users.csv';

-- With options
COPY myapp.users (user_id, username, email) 
TO '/tmp/users.csv'
WITH HEADER = true
AND DELIMITER = '|'
AND MAXREQUESTS = 10
AND PAGESIZE = 100;

-- Export with WHERE clause (limited support)
COPY myapp.users (user_id, username) 
TO '/tmp/active_users.csv'
WHERE status = 'active' ALLOW FILTERING;
```

### Import Data (COPY FROM)

```cql
-- Basic import
COPY myapp.users FROM '/tmp/users.csv';

-- With options
COPY myapp.users (user_id, username, email)
FROM '/tmp/users.csv'
WITH HEADER = true
AND DELIMITER = '|'
AND CHUNKSIZE = 1000
AND INGESTRATE = 100000;
```

### COPY Options

```cql
-- Performance options
MAXREQUESTS = 10        -- Concurrent requests (default: 6)
PAGESIZE = 100          -- Rows per page (default: 1000)
CHUNKSIZE = 1000        -- Rows per chunk (default: 1000)
INGESTRATE = 100000     -- Max rows/sec (default: 100000)

-- Format options
HEADER = true           -- Include/expect header row
DELIMITER = ','         -- Field delimiter (default: ,)
QUOTE = '"'             -- Quote character (default: ")
ESCAPE = '\'            -- Escape character (default: \)
NULL = 'NULL'           -- NULL representation

-- Other options
MAXATTEMPTS = 5         -- Retry attempts (default: 5)
REPORTFREQUENCY = 0.25  -- Progress report interval
DECIMALSEP = '.'        -- Decimal separator
THOUSANDSSEP = ','      -- Thousands separator
DATETIMEFORMAT = 'yyyy-MM-dd HH:mm:ss'
```

### Example: Full Table Migration

```bash
#!/bin/bash
# migrate_table.sh

KEYSPACE="myapp"
TABLE="users"
DSE_HOST="dse-node1"
HCD_HOST="hcd-node1"

# Export from DSE
cqlsh $DSE_HOST -e "
COPY $KEYSPACE.$TABLE TO '/tmp/${TABLE}.csv'
WITH HEADER = true
AND MAXREQUESTS = 10
AND PAGESIZE = 1000;
"

# Import to HCD
cqlsh $HCD_HOST -e "
COPY $KEYSPACE.$TABLE FROM '/tmp/${TABLE}.csv'
WITH HEADER = true
AND CHUNKSIZE = 1000
AND INGESTRATE = 100000;
"

# Verify count
DSE_COUNT=$(cqlsh $DSE_HOST -e "SELECT COUNT(*) FROM $KEYSPACE.$TABLE;" | grep -oP '\d+')
HCD_COUNT=$(cqlsh $HCD_HOST -e "SELECT COUNT(*) FROM $KEYSPACE.$TABLE;" | grep -oP '\d+')

echo "DSE count: $DSE_COUNT"
echo "HCD count: $HCD_COUNT"

if [ "$DSE_COUNT" -eq "$HCD_COUNT" ]; then
  echo "✅ Migration successful"
else
  echo "❌ Count mismatch"
fi
```

### Advantages

✅ **Simple to Use**: Easy command-line interface  
✅ **Human Readable**: CSV format is easy to inspect  
✅ **Portable**: Works across versions  
✅ **Selective Export**: Can export specific columns

### Limitations

❌ **Slow Performance**: Not suitable for large datasets  
❌ **Memory Intensive**: Loads data into memory  
❌ **No Compression**: CSV files can be large  
❌ **Limited Data Types**: Some types may not export correctly  
❌ **Single Threaded**: No parallel processing

## CQL COPY TO/FROM

### Programmatic Approach

```python
# Python example using cassandra-driver
from cassandra.cluster import Cluster
import csv

# Connect to DSE
dse_cluster = Cluster(['dse-node1'])
dse_session = dse_cluster.connect('myapp')

# Connect to HCD
hcd_cluster = Cluster(['hcd-node1'])
hcd_session = hcd_cluster.connect('myapp')

# Export from DSE
rows = dse_session.execute("SELECT * FROM users")

# Import to HCD
insert_stmt = hcd_session.prepare(
    "INSERT INTO users (user_id, username, email, created_at) VALUES (?, ?, ?, ?)"
)

batch_size = 100
batch = []

for row in rows:
    batch.append((row.user_id, row.username, row.email, row.created_at))
    
    if len(batch) >= batch_size:
        for item in batch:
            hcd_session.execute(insert_stmt, item)
        batch = []
        print(f"Processed {len(batch)} rows")

# Process remaining
for item in batch:
    hcd_session.execute(insert_stmt, item)

print("Migration complete")
```

## Backup and Restore

### Full Backup Strategy

```bash
#!/bin/bash
# full_backup.sh

KEYSPACE="myapp"
BACKUP_DIR="/backup/$(date +%Y%m%d)"
SNAPSHOT_TAG="backup_$(date +%Y%m%d_%H%M%S)"

# Create snapshot
nodetool snapshot -t $SNAPSHOT_TAG $KEYSPACE

# Find snapshot directories
SNAPSHOT_DIRS=$(find /var/lib/cassandra/data/$KEYSPACE/*/snapshots/$SNAPSHOT_TAG -type d)

# Copy to backup location
mkdir -p $BACKUP_DIR
for dir in $SNAPSHOT_DIRS; do
    table=$(echo $dir | awk -F'/' '{print $(NF-2)}')
    mkdir -p $BACKUP_DIR/$table
    cp -r $dir/* $BACKUP_DIR/$table/
done

# Export schema
cqlsh -e "DESC KEYSPACE $KEYSPACE" > $BACKUP_DIR/schema.cql

# Clear snapshot
nodetool clearsnapshot -t $SNAPSHOT_TAG

echo "Backup completed: $BACKUP_DIR"
```

### Incremental Backup

```bash
# Enable incremental backups
nodetool enablebackup

# Backup location
# /var/lib/cassandra/data/<keyspace>/<table>/backups/

# Disable when done
nodetool disablebackup
```

## Best Practices

### 1. Always Test First

```bash
# Test on small dataset
COPY myapp.users (user_id, username) 
TO '/tmp/test.csv'
WITH MAXREQUESTS = 1 AND PAGESIZE = 10;
```

### 2. Monitor Resource Usage

```bash
# Monitor during migration
watch -n 5 'nodetool tpstats | grep -A 5 "Pool Name"'
watch -n 5 'nodetool compactionstats'
```

### 3. Validate Data

```bash
# Compare counts
cqlsh dse-node1 -e "SELECT COUNT(*) FROM myapp.users;"
cqlsh hcd-node1 -e "SELECT COUNT(*) FROM myapp.users;"

# Sample data comparison
cqlsh dse-node1 -e "SELECT * FROM myapp.users LIMIT 10;"
cqlsh hcd-node1 -e "SELECT * FROM myapp.users LIMIT 10;"
```

### 4. Use Compression

```bash
# Compress CSV exports
COPY myapp.users TO STDOUT | gzip > /tmp/users.csv.gz

# Decompress for import
gunzip -c /tmp/users.csv.gz | cqlsh hcd-node1 -e "COPY myapp.users FROM STDIN"
```

### 5. Parallel Processing

```bash
# Split large tables by token range
for range in $(nodetool ring | awk '{print $8}' | sort -u); do
  sstableloader -d hcd-node1 --token-range $range /staging/myapp/users &
done
wait
```

## Troubleshooting

### SSTableLoader Issues

```bash
# Error: "Cannot find schema for keyspace"
# Solution: Create schema on target first
cqlsh hcd-node1 < schema.cql

# Error: "Connection refused"
# Solution: Check network connectivity
telnet hcd-node1 9042

# Error: "Authentication failed"
# Solution: Provide credentials
sstableloader -u cassandra -pw cassandra -d hcd-node1 /staging/myapp/users
```

### COPY Command Issues

```bash
# Error: "Timeout"
# Solution: Increase timeout
cqlsh --request-timeout=300 hcd-node1

# Error: "Out of memory"
# Solution: Reduce page size
COPY myapp.users TO '/tmp/users.csv' WITH PAGESIZE = 100;

# Error: "Invalid data"
# Solution: Check data types and format
```

## Summary

Native tooling provides foundational capabilities for data migration:

- **SSTableLoader**: Best for bulk data loading, high performance
- **Nodetool Snapshot**: Essential for backups, requires downtime for restore
- **COPY Command**: Simple but slow, good for small datasets
- **Combination Approach**: Use multiple tools for complete migration strategy

For zero-downtime migrations, native tools are typically combined with other approaches like ZDM or CDM.

---

**Next:** [DSE-Specific Tooling](03-dse-tooling.md)