# Exercise 1: Environment Setup and Validation

## Objectives

- Start the lab environment using Docker Compose
- Verify both DSE and HCD clusters are healthy
- Create schema on both clusters
- Generate sample data
- Validate connectivity and basic operations

## Prerequisites

- Docker or Colima installed and running
- At least 8GB RAM and 4 CPU cores available
- 30GB free disk space

## Duration

30-45 minutes

## Steps

### Step 1: Start the Lab Environment

```bash
# Navigate to lab directory
cd lab

# Start all services
docker-compose up -d

# Expected output:
# Creating network "lab_cassandra-migration" ... done
# Creating dse-node1 ... done
# Creating hcd-node1 ... done
# Creating zdm-proxy ... done
# ...
```

**Wait Time:** 3-5 minutes for all services to start

### Step 2: Monitor Startup Progress

```bash
# Watch container status
watch -n 5 'docker-compose ps'

# All containers should show "Up" and "healthy" status
# Press Ctrl+C to exit watch

# Alternative: Check specific service
docker-compose ps dse-node1
docker-compose ps hcd-node1
```

### Step 3: Verify DSE Cluster

```bash
# Check DSE cluster status
docker exec dse-node1 nodetool status

# Expected output:
# Datacenter: dc1
# ===============
# Status=Up/Down
# |/ State=Normal/Leaving/Joining/Moving
# --  Address     Load       Tokens  Owns    Host ID                               Rack
# UN  172.20.0.2  X.XX KiB   256     XX.X%   xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  rack1
# UN  172.20.0.3  X.XX KiB   256     XX.X%   xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  rack1
# UN  172.20.0.4  X.XX KiB   256     XX.X%   xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  rack1
```

**Validation Checklist:**
- [ ] All 3 nodes show status "UN" (Up/Normal)
- [ ] Each node has 256 tokens
- [ ] Load is distributed across nodes

### Step 4: Verify HCD Cluster

```bash
# Check HCD cluster status
docker exec hcd-node1 nodetool status

# Expected output:
# Datacenter: datacenter1
# =======================
# Status=Up/Down
# |/ State=Normal/Leaving/Joining/Moving
# --  Address     Load       Tokens  Owns    Host ID                               Rack
# UN  172.20.0.5  X.XX KiB   256     XX.X%   xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  rack1
# UN  172.20.0.6  X.XX KiB   256     XX.X%   xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  rack1
# UN  172.20.0.7  X.XX KiB   256     XX.X%   xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  rack1
```

**Validation Checklist:**
- [ ] All 3 nodes show status "UN" (Up/Normal)
- [ ] Each node has 256 tokens
- [ ] Datacenter name is "datacenter1"

### Step 5: Test CQL Connectivity

```bash
# Connect to DSE
docker exec -it dse-node1 cqlsh

# You should see:
# Connected to DSE_Cluster at 127.0.0.1:9042.
# [cqlsh 5.0.1 | Cassandra 3.11.x | DSE 5.1.35 | CQL spec 3.4.4 | Native protocol v4]

# Test basic query
cqlsh> SELECT cluster_name, release_version FROM system.local;

# Exit
cqlsh> exit
```

```bash
# Connect to HCD
docker exec -it hcd-node1 cqlsh

# You should see:
# Connected to HCD_Cluster at 127.0.0.1:9042.
# [cqlsh 6.x.x | Cassandra 4.1.x | CQL spec 3.4.5 | Native protocol v5]

# Test basic query
cqlsh> SELECT cluster_name, release_version FROM system.local;

# Exit
cqlsh> exit
```

**Validation Checklist:**
- [ ] Can connect to DSE cluster
- [ ] Can connect to HCD cluster
- [ ] Both clusters respond to queries

### Step 6: Create Schema on DSE

```bash
# Create schema using init script
docker exec -i dse-node1 cqlsh < init-scripts/01-create-schema.cql

# Verify keyspace creation
docker exec dse-node1 cqlsh -e "DESC KEYSPACE training;"

# Expected output shows:
# - Keyspace with NetworkTopologyStrategy
# - Tables: users, orders, products, user_activity
# - Indexes on various columns
```

**Validation Checklist:**
- [ ] Keyspace `training` created
- [ ] All 4 tables created
- [ ] Indexes created successfully

### Step 7: Create Schema on HCD

```bash
# Export schema from DSE
docker exec dse-node1 cqlsh -e "DESC KEYSPACE training;" > /tmp/training_schema.cql

# Modify for HCD (change datacenter name)
sed 's/dc1/datacenter1/g' /tmp/training_schema.cql > /tmp/training_schema_hcd.cql

# Create on HCD
docker exec -i hcd-node1 cqlsh < /tmp/training_schema_hcd.cql

# Verify
docker exec hcd-node1 cqlsh -e "DESC KEYSPACE training;"
```

**Validation Checklist:**
- [ ] Keyspace `training` created on HCD
- [ ] All tables match DSE schema
- [ ] Replication factor adjusted for HCD datacenter

### Step 8: Generate Sample Data

```bash
# Access data generator container
docker exec -it data-generator bash

# Install cassandra-driver if not already installed
pip install cassandra-driver

# Run data generator
cd /scripts
python3 generate_data.py dse-node1

# Expected output:
# Connecting to dse-node1:9042...
# Connected successfully!
# Generating 1000 users...
#   Generated 100 users...
#   Generated 200 users...
#   ...
# ✓ Generated 1000 users
# Generating 500 products...
# ✓ Generated 500 products
# Generating 2000 orders...
# ✓ Generated 2000 orders
# Generating 5000 user activity records...
# ✓ Generated 5000 user activity records
#
# ==================================================
# Data Generation Complete!
# ==================================================
# users                : 1,000 rows
# products             : 500 rows
# orders               : 2,000 rows
# user_activity        : 5,000 rows
# ==================================================

# Exit container
exit
```

**Validation Checklist:**
- [ ] 1,000 users generated
- [ ] 500 products generated
- [ ] 2,000 orders generated
- [ ] 5,000 user activity records generated

### Step 9: Verify Data on DSE

```bash
# Check row counts
docker exec dse-node1 cqlsh -e "
SELECT COUNT(*) FROM training.users;
SELECT COUNT(*) FROM training.products;
SELECT COUNT(*) FROM training.orders;
SELECT COUNT(*) FROM training.user_activity;
"

# Sample some data
docker exec dse-node1 cqlsh -e "
SELECT * FROM training.users LIMIT 5;
"

# Test queries
docker exec dse-node1 cqlsh -e "
SELECT username, email, status FROM training.users WHERE status = 'active' LIMIT 10 ALLOW FILTERING;
"
```

**Validation Checklist:**
- [ ] Row counts match expected values
- [ ] Sample data looks correct
- [ ] Queries execute successfully

### Step 10: Verify Monitoring Stack

```bash
# Check Prometheus
curl http://localhost:9090/-/healthy

# Expected: Prometheus is Healthy.

# Check Grafana
curl http://localhost:3000/api/health

# Expected: {"commit":"...","database":"ok","version":"..."}

# Access Grafana UI
# Open browser: http://localhost:3000
# Login: admin / admin
```

**Validation Checklist:**
- [ ] Prometheus is accessible
- [ ] Grafana is accessible
- [ ] Can login to Grafana

### Step 11: Verify Tools Container

```bash
# Access tools container
docker exec -it migration-tools bash

# Verify tools are available
which cqlsh
which dsbulk
python3 --version

# Test connectivity to DSE
cqlsh dse-node1 -e "SELECT cluster_name FROM system.local;"

# Test connectivity to HCD
cqlsh hcd-node1 -e "SELECT cluster_name FROM system.local;"

# Exit
exit
```

**Validation Checklist:**
- [ ] Tools container is accessible
- [ ] All tools are installed
- [ ] Can connect to both clusters

## Verification Commands

Run these commands to verify everything is working:

```bash
# 1. All containers running
docker-compose ps | grep "Up"

# 2. DSE cluster healthy
docker exec dse-node1 nodetool status | grep "UN" | wc -l
# Should output: 3

# 3. HCD cluster healthy
docker exec hcd-node1 nodetool status | grep "UN" | wc -l
# Should output: 3

# 4. Data exists on DSE
docker exec dse-node1 cqlsh -e "SELECT COUNT(*) FROM training.users;" | grep -oP '\d+'
# Should output: 1000

# 5. Schema exists on HCD
docker exec hcd-node1 cqlsh -e "DESC KEYSPACE training;" | grep "CREATE TABLE"
# Should show 4 tables
```

## Troubleshooting

### Issue: Containers won't start

```bash
# Check Docker resources
docker system df

# Check logs
docker-compose logs dse-node1

# Restart specific service
docker-compose restart dse-node1
```

### Issue: Cluster not forming

```bash
# Check network connectivity
docker exec dse-node1 ping dse-node2

# Check Cassandra logs
docker exec dse-node1 tail -f /var/log/cassandra/system.log
```

### Issue: Can't connect with cqlsh

```bash
# Verify port is listening
docker exec dse-node1 netstat -tlnp | grep 9042

# Check if node is ready
docker exec dse-node1 nodetool status
```

### Issue: Data generation fails

```bash
# Check if keyspace exists
docker exec dse-node1 cqlsh -e "DESC KEYSPACE training;"

# Verify connectivity
docker exec data-generator ping dse-node1

# Check Python dependencies
docker exec data-generator pip list | grep cassandra
```

## Success Criteria

You have successfully completed this exercise when:

- ✅ All 6 Cassandra nodes are running (3 DSE + 3 HCD)
- ✅ Both clusters show all nodes as "UN" (Up/Normal)
- ✅ Schema exists on both DSE and HCD clusters
- ✅ Sample data generated on DSE cluster
- ✅ Monitoring stack is accessible
- ✅ Tools container can connect to both clusters

## Next Steps

Proceed to [Exercise 2: Native Tooling Migration](02-native-tooling.md) to learn about using native Cassandra tools for data migration.

## Clean Up (Optional)

If you need to reset the environment:

```bash
# Stop all containers
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Restart fresh
docker-compose up -d
```

## Key Takeaways

1. **Cluster Formation**: Both DSE and HCD clusters form independently
2. **Schema Compatibility**: DSE schema can be adapted for HCD with minor changes
3. **Data Generation**: Sample data helps practice migration scenarios
4. **Monitoring**: Essential for tracking migration progress
5. **Tools**: Pre-configured tools simplify migration tasks

---

**Time to Complete:** 30-45 minutes  
**Difficulty:** Beginner  
**Next Exercise:** [Native Tooling Migration](02-native-tooling.md)