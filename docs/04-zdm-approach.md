# Zero Downtime Migration (ZDM) Proxy Approach

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [How ZDM Works](#how-zdm-works)
4. [Installation and Setup](#installation-and-setup)
5. [Configuration](#configuration)
6. [Migration Phases](#migration-phases)
7. [Monitoring and Validation](#monitoring-and-validation)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Overview

The Zero Downtime Migration (ZDM) proxy is a purpose-built solution for migrating from DSE/Cassandra to HCD with zero downtime. It acts as a transparent proxy between applications and database clusters, enabling gradual migration without application changes.

### Key Features

✅ **True Zero Downtime**: Applications remain operational throughout migration  
✅ **No Application Changes**: Transparent proxy layer  
✅ **Dual-Write Capability**: Writes to both clusters simultaneously  
✅ **Read Routing**: Intelligent read request routing  
✅ **Built-in Validation**: Automatic data consistency checks  
✅ **Gradual Migration**: Phase-based approach with rollback capability  
✅ **Monitoring**: Comprehensive metrics and logging

### When to Use ZDM

**Ideal For:**
- Production environments requiring zero downtime
- Applications that cannot be modified
- Large-scale migrations (multi-TB datasets)
- Complex multi-datacenter topologies
- Strict SLA requirements

**Not Ideal For:**
- Development/test environments (simpler tools suffice)
- Applications with very low latency requirements (proxy adds overhead)
- Scenarios where application changes are acceptable

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │  App 1   │  │  App 2   │  │  App 3   │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
└───────┼─────────────┼─────────────┼────────────────────┘
        │             │             │
        └─────────────┴─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │      ZDM Proxy Layer      │
        │  ┌─────────────────────┐  │
        │  │   Proxy Instance    │  │
        │  │  - Request Router   │  │
        │  │  - Dual Writer      │  │
        │  │  - Validator        │  │
        │  └─────────────────────┘  │
        └─────────────┬─────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
┌───────────────┐           ┌───────────────┐
│  Origin DSE   │           │  Target HCD   │
│   Cluster     │           │   Cluster     │
│               │           │               │
│ ┌───┐ ┌───┐  │           │ ┌───┐ ┌───┐  │
│ │ N │ │ N │  │           │ │ N │ │ N │  │
│ └───┘ └───┘  │           │ └───┘ └───┘  │
└───────────────┘           └───────────────┘
```

### Component Details

#### 1. ZDM Proxy
- **Request Router**: Directs reads to appropriate cluster
- **Dual Writer**: Writes to both clusters simultaneously
- **Consistency Checker**: Validates data consistency
- **Metrics Collector**: Gathers performance metrics

#### 2. Origin Cluster (DSE 5.1)
- Source cluster with existing data
- Continues serving traffic during migration
- Gradually phased out

#### 3. Target Cluster (HCD)
- Destination cluster
- Receives dual-writes during migration
- Eventually becomes primary cluster

## How ZDM Works

### Phase 1: Dual-Write Mode

```
Application Write Request
         │
         ▼
    ZDM Proxy
         │
    ┌────┴────┐
    ▼         ▼
  Origin    Target
   (DSE)    (HCD)
    │         │
    └────┬────┘
         │
    Response to
    Application
```

**Behavior:**
- All writes go to both clusters
- Reads come from Origin (DSE)
- Asynchronous writes to Target
- Origin response returned to application

### Phase 2: Read Routing

```
Application Read Request
         │
         ▼
    ZDM Proxy
    (Decision)
         │
    ┌────┴────┐
    ▼         ▼
  Origin    Target
  (Primary) (Secondary)
    │         │
    └────┬────┘
         │
    Response to
    Application
```

**Behavior:**
- Configurable read routing percentage
- Gradual shift from Origin to Target
- Fallback to Origin on Target errors
- Performance comparison

### Phase 3: Target Primary

```
Application Request
         │
         ▼
    ZDM Proxy
         │
         ▼
      Target
      (HCD)
    (Primary)
         │
         ▼
    Response to
    Application
```

**Behavior:**
- All traffic to Target (HCD)
- Origin cluster can be decommissioned
- Migration complete

## Installation and Setup

### Prerequisites

```bash
# System requirements
- Java 11 or higher
- Network connectivity to both clusters
- Sufficient CPU and memory (4 cores, 8GB RAM minimum)
- Docker (optional, for containerized deployment)
```

### Installation Methods

#### Method 1: Binary Installation

```bash
# Download ZDM Proxy
wget https://github.com/datastax/zdm-proxy/releases/download/v2.1.0/zdm-proxy-2.1.0.tar.gz

# Extract
tar -xzf zdm-proxy-2.1.0.tar.gz
cd zdm-proxy-2.1.0

# Verify Java
java -version
# openjdk version "11.0.x"

# Run proxy
./bin/zdm-proxy --config config.yml
```

#### Method 2: Docker Installation

```bash
# Pull Docker image
docker pull datastax/zdm-proxy:2.1.0

# Run container
docker run -d \
  --name zdm-proxy \
  -p 9042:9042 \
  -p 14001:14001 \
  -v $(pwd)/config.yml:/config.yml \
  datastax/zdm-proxy:2.1.0 \
  --config /config.yml
```

#### Method 3: Kubernetes Deployment

```yaml
# zdm-proxy-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zdm-proxy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: zdm-proxy
  template:
    metadata:
      labels:
        app: zdm-proxy
    spec:
      containers:
      - name: zdm-proxy
        image: datastax/zdm-proxy:2.1.0
        ports:
        - containerPort: 9042
          name: cql
        - containerPort: 14001
          name: metrics
        volumeMounts:
        - name: config
          mountPath: /config.yml
          subPath: config.yml
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
      volumes:
      - name: config
        configMap:
          name: zdm-proxy-config
---
apiVersion: v1
kind: Service
metadata:
  name: zdm-proxy
spec:
  selector:
    app: zdm-proxy
  ports:
  - port: 9042
    targetPort: 9042
    name: cql
  - port: 14001
    targetPort: 14001
    name: metrics
  type: LoadBalancer
```

## Configuration

### Basic Configuration

```yaml
# config.yml
origin_contact_points: "dse-node1,dse-node2,dse-node3"
origin_port: 9042
origin_username: "cassandra"
origin_password: "cassandra"

target_contact_points: "hcd-node1,hcd-node2,hcd-node3"
target_port: 9042
target_username: "cassandra"
target_password: "cassandra"

proxy_listen_port: 9042
proxy_listen_address: "0.0.0.0"

# Metrics endpoint
metrics_enabled: true
metrics_port: 14001
```

### Advanced Configuration

```yaml
# config.yml - Production settings
origin_contact_points: "dse-node1,dse-node2,dse-node3"
origin_port: 9042
origin_username: "cassandra"
origin_password: "cassandra"
origin_local_datacenter: "dc1"
origin_connection_timeout_ms: 5000
origin_request_timeout_ms: 12000

target_contact_points: "hcd-node1,hcd-node2,hcd-node3"
target_port: 9042
target_username: "cassandra"
target_password: "cassandra"
target_local_datacenter: "datacenter1"
target_connection_timeout_ms: 5000
target_request_timeout_ms: 12000

proxy_listen_port: 9042
proxy_listen_address: "0.0.0.0"
proxy_max_client_connections: 1000
proxy_max_stream_ids: 2048

# Read routing configuration
read_mode: "PRIMARY_ONLY"  # Options: PRIMARY_ONLY, DUAL, TARGET_ONLY
primary_cluster: "ORIGIN"  # Options: ORIGIN, TARGET

# Write configuration
async_handshake_timeout_ms: 4000
forward_client_credentials_to_origin: false
forward_client_credentials_to_target: false

# Metrics and monitoring
metrics_enabled: true
metrics_port: 14001
metrics_prefix: "zdm"

# Logging
log_level: "INFO"  # Options: TRACE, DEBUG, INFO, WARN, ERROR
```

### SSL/TLS Configuration

```yaml
# config.yml - With SSL
origin_contact_points: "dse-node1,dse-node2,dse-node3"
origin_port: 9042
origin_username: "cassandra"
origin_password: "cassandra"
origin_ssl_enabled: true
origin_ssl_truststore_path: "/path/to/origin-truststore.jks"
origin_ssl_truststore_password: "truststore_password"

target_contact_points: "hcd-node1,hcd-node2,hcd-node3"
target_port: 9042
target_username: "cassandra"
target_password: "cassandra"
target_ssl_enabled: true
target_ssl_truststore_path: "/path/to/target-truststore.jks"
target_ssl_truststore_password: "truststore_password"

# Client-facing SSL
proxy_ssl_enabled: true
proxy_ssl_keystore_path: "/path/to/proxy-keystore.jks"
proxy_ssl_keystore_password: "keystore_password"
```

## Migration Phases

### Phase 0: Preparation

```bash
# 1. Set up HCD cluster
# 2. Create schema on HCD
cqlsh hcd-node1 < schema.cql

# 3. Initial data load (optional)
# Use sstableloader or dsbulk for bulk data
dsbulk load -h hcd-node1 -k myapp -t users -url /export/users

# 4. Deploy ZDM proxy
docker run -d --name zdm-proxy \
  -p 9042:9042 \
  -v $(pwd)/config.yml:/config.yml \
  datastax/zdm-proxy:2.1.0 --config /config.yml

# 5. Verify proxy connectivity
cqlsh zdm-proxy-host 9042 -u cassandra -p cassandra
```

### Phase 1: Enable Dual-Write

```yaml
# config.yml - Phase 1
read_mode: "PRIMARY_ONLY"
primary_cluster: "ORIGIN"
```

```bash
# Update application connection strings
# FROM: dse-node1,dse-node2,dse-node3
# TO:   zdm-proxy-host

# Restart applications gradually
# Monitor for errors
```

**Validation:**
```bash
# Check write counts on both clusters
cqlsh dse-node1 -e "SELECT COUNT(*) FROM myapp.users;"
cqlsh hcd-node1 -e "SELECT COUNT(*) FROM myapp.users;"

# Monitor ZDM metrics
curl http://zdm-proxy-host:14001/metrics | grep write
```

### Phase 2: Gradual Read Migration

```yaml
# config.yml - Phase 2a (10% reads to target)
read_mode: "DUAL"
primary_cluster: "ORIGIN"
read_routing_percentage: 10  # 10% to target, 90% to origin
```

```bash
# Restart proxy with new config
docker restart zdm-proxy

# Monitor performance
# Compare latency between clusters
# Check error rates
```

```yaml
# config.yml - Phase 2b (50% reads to target)
read_mode: "DUAL"
primary_cluster: "ORIGIN"
read_routing_percentage: 50
```

```yaml
# config.yml - Phase 2c (100% reads to target)
read_mode: "PRIMARY_ONLY"
primary_cluster: "TARGET"
```

### Phase 3: Target as Primary

```yaml
# config.yml - Phase 3
read_mode: "PRIMARY_ONLY"
primary_cluster: "TARGET"
```

```bash
# All traffic now goes to HCD
# Monitor for 24-48 hours
# Verify stability and performance
```

### Phase 4: Decommission Origin

```bash
# 1. Stop dual-writes (optional)
# Update config to only write to target

# 2. Remove ZDM proxy (optional)
# Update applications to connect directly to HCD

# 3. Backup origin cluster
nodetool snapshot -t final_backup

# 4. Decommission origin nodes
nodetool decommission

# 5. Archive data
# Keep backups for rollback period
```

## Monitoring and Validation

### Metrics Endpoint

```bash
# Access metrics
curl http://zdm-proxy-host:14001/metrics

# Key metrics to monitor:
# - zdm_proxy_requests_total
# - zdm_proxy_requests_duration_seconds
# - zdm_proxy_errors_total
# - zdm_proxy_origin_requests_total
# - zdm_proxy_target_requests_total
```

### Prometheus Integration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'zdm-proxy'
    static_configs:
      - targets: ['zdm-proxy-host:14001']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "ZDM Proxy Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(zdm_proxy_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(zdm_proxy_errors_total[5m])"
          }
        ]
      },
      {
        "title": "Latency (p99)",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, zdm_proxy_requests_duration_seconds_bucket)"
          }
        ]
      }
    ]
  }
}
```

### Data Consistency Validation

```bash
# validation_script.sh
#!/bin/bash

KEYSPACE="myapp"
TABLE="users"
SAMPLE_SIZE=1000

# Get random sample from origin
ORIGIN_SAMPLE=$(cqlsh dse-node1 -e "
  SELECT user_id, username, email 
  FROM $KEYSPACE.$TABLE 
  LIMIT $SAMPLE_SIZE
" | tail -n +4)

# Check same records on target
while IFS= read -r line; do
  USER_ID=$(echo $line | awk '{print $1}')
  
  ORIGIN_DATA=$(cqlsh dse-node1 -e "
    SELECT * FROM $KEYSPACE.$TABLE WHERE user_id = $USER_ID
  ")
  
  TARGET_DATA=$(cqlsh hcd-node1 -e "
    SELECT * FROM $KEYSPACE.$TABLE WHERE user_id = $USER_ID
  ")
  
  if [ "$ORIGIN_DATA" != "$TARGET_DATA" ]; then
    echo "Mismatch for user_id: $USER_ID"
  fi
done <<< "$ORIGIN_SAMPLE"

echo "Validation complete"
```

### Automated Validation Tool

```python
# validate_consistency.py
from cassandra.cluster import Cluster
import random

def validate_consistency(keyspace, table, sample_size=1000):
    # Connect to both clusters
    origin_cluster = Cluster(['dse-node1'])
    target_cluster = Cluster(['hcd-node1'])
    
    origin_session = origin_cluster.connect(keyspace)
    target_session = target_cluster.connect(keyspace)
    
    # Get sample from origin
    rows = origin_session.execute(f"SELECT * FROM {table} LIMIT {sample_size}")
    
    mismatches = 0
    for row in rows:
        # Build WHERE clause from primary key
        pk_columns = get_primary_key_columns(keyspace, table)
        where_clause = " AND ".join([f"{col} = %s" for col in pk_columns])
        pk_values = [getattr(row, col) for col in pk_columns]
        
        # Query target
        target_row = target_session.execute(
            f"SELECT * FROM {table} WHERE {where_clause}",
            pk_values
        ).one()
        
        # Compare
        if not rows_equal(row, target_row):
            mismatches += 1
            print(f"Mismatch: {pk_values}")
    
    print(f"Validation complete: {mismatches} mismatches out of {sample_size}")
    
    origin_cluster.shutdown()
    target_cluster.shutdown()

if __name__ == "__main__":
    validate_consistency("myapp", "users", 1000)
```

## Best Practices

### 1. Gradual Rollout

```bash
# Start with non-critical applications
# Monitor for issues
# Gradually add more applications
# Keep rollback plan ready
```

### 2. Performance Testing

```bash
# Baseline performance on origin
cassandra-stress write n=1000000 -node dse-node1

# Test through proxy
cassandra-stress write n=1000000 -node zdm-proxy-host

# Compare results
# Acceptable overhead: 5-10%
```

### 3. Capacity Planning

```yaml
# ZDM Proxy resources per 1000 req/sec:
CPU: 1 core
Memory: 2 GB
Network: 100 Mbps

# Scale horizontally for higher throughput
# Deploy multiple proxy instances
# Use load balancer
```

### 4. High Availability

```bash
# Deploy multiple proxy instances
# Use load balancer (HAProxy, Nginx)
# Configure health checks
# Implement automatic failover
```

### 5. Monitoring Checklist

- [ ] Request rate (reads/writes per second)
- [ ] Error rate (< 0.1% acceptable)
- [ ] Latency (p50, p95, p99)
- [ ] Connection count
- [ ] Memory usage
- [ ] CPU usage
- [ ] Network throughput
- [ ] Data consistency validation

## Troubleshooting

### Issue 1: High Latency

```bash
# Symptoms
# - Increased response times
# - Application timeouts

# Diagnosis
curl http://zdm-proxy-host:14001/metrics | grep duration

# Solutions
# 1. Increase proxy resources
# 2. Tune connection pools
# 3. Check network latency
# 4. Optimize queries
```

### Issue 2: Connection Errors

```bash
# Symptoms
# - "Connection refused"
# - "Too many connections"

# Diagnosis
netstat -an | grep 9042 | wc -l

# Solutions
# 1. Increase max_client_connections
# 2. Check firewall rules
# 3. Verify cluster health
# 4. Scale proxy instances
```

### Issue 3: Data Inconsistency

```bash
# Symptoms
# - Different row counts
# - Missing data on target

# Diagnosis
# Run consistency validation script

# Solutions
# 1. Check dual-write configuration
# 2. Verify replication settings
# 3. Run repair on target
# 4. Re-sync affected data
```

### Issue 4: Memory Issues

```bash
# Symptoms
# - OutOfMemoryError
# - Proxy crashes

# Diagnosis
docker stats zdm-proxy

# Solutions
# 1. Increase container memory
# 2. Tune JVM heap size
# 3. Reduce max_stream_ids
# 4. Check for memory leaks
```

## Summary

ZDM Proxy provides a robust solution for zero-downtime migration:

**Advantages:**
- ✅ True zero downtime
- ✅ No application changes required
- ✅ Built-in validation
- ✅ Gradual migration with rollback
- ✅ Production-ready

**Considerations:**
- Additional infrastructure required
- Proxy adds latency overhead (5-10%)
- Requires monitoring and management
- Learning curve for operations team

**Best For:**
- Production environments
- Large-scale migrations
- Strict SLA requirements
- Applications that cannot be modified

---

**Next:** [Cassandra Data Migrator (CDM) Approach](05-cdm-approach.md)