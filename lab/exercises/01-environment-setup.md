# Exercise 1: Environment Setup and Validation

## Objectives

- Verify the lab environment is running (started via [Quick Start](../README.md#quick-start))
- Confirm both DSE and HCD clusters are healthy
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

### Step 1: Start and Verify the Lab

Ensure you're working from the `lab` directory as you CWD (Current Working Directory).

```bash
cd lab
docker compose up -d
```

Wait 3–5 minutes (longer on first run while the tools image builds), then confirm services are up:

```bash
docker compose ps
# Optional: watch until all show "Up"
watch -n 5 'docker compose ps'
```

**Validation Checklist:**
- [ ] All containers show status "Up"

### Step 2: Verify Cluster Health

```bash
# DSE — expect one node with status UN in datacenter datacenter1
docker exec dse-node nodetool status

# HCD — expect one node with status UN in datacenter datacenter1
docker exec hcd-node nodetool status

# CQL connectivity
docker exec dse-node cqlsh -e "SELECT cluster_name, release_version FROM system.local"
docker exec hcd-node cqlsh -e "SELECT cluster_name, release_version FROM system.local"
```

**Validation Checklist:**
- [ ] DSE node shows status "UN" in datacenter `datacenter1`
- [ ] HCD node shows status "UN" in datacenter `datacenter1`
- [ ] Both clusters respond to CQL queries

### Step 3: Create Schema on DSE

```bash
# Create schema using init script
docker exec -i dse-node cqlsh < init-scripts/01-create-schema.cql

# Verify keyspace creation
docker exec dse-node cqlsh -e "DESC KEYSPACE training;"

# Expected output shows:
# - Keyspace with NetworkTopologyStrategy
# - Tables: users, orders, products, user_activity
# - Indexes on various columns
```

**Validation Checklist:**
- [ ] Keyspace `training` created
- [ ] All 4 tables created
- [ ] Indexes created successfully

### Step 4: Create Schema on HCD

In this step we intentfuly copy the source schema to the target database. In most cases, unless you transform the data on the go, the schemas have to match.

```bash
# Export schema from DSE
docker exec dse-node cqlsh -e "DESC KEYSPACE training;" > /tmp/training_schema.cql

# Create on HCD
docker exec -i hcd-node cqlsh < /tmp/training_schema_hcd.cql

# Verify
docker exec hcd-node cqlsh -e "DESC KEYSPACE training;"
```

**Validation Checklist:**
- [ ] Keyspace `training` created on HCD
- [ ] All tables match DSE schema
- [ ] Replication uses `datacenter1` on both clusters

### Step 5: Generate and Verify Sample Data

```bash
# Generate data from the tools container (cassandra-driver is pre-installed)
docker exec tools python3 /scripts/generate_data.py dse-node

# Verify row counts on DSE
docker exec dse-node cqlsh -e "
SELECT COUNT(*) FROM training.users;
SELECT COUNT(*) FROM training.products;
SELECT COUNT(*) FROM training.orders;
SELECT COUNT(*) FROM training.user_activity;
"
```

Expected counts: 1,000 users, 500 products, 2,000 orders, 5,000 user activity records.

**Validation Checklist:**
- [ ] Data generation script completes without errors
- [ ] Row counts match expected values

### Step 6: Verify Monitoring Stack

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

### Step 7: Verify Tools Container

```bash
docker exec tools which cqlsh dsbulk
docker exec tools python3 --version
```

**Validation Checklist:**
- [ ] `cqlsh` and `dsbulk` are on PATH
- [ ] Python 3.11 is available

## Troubleshooting

### Issue: Containers won't start

```bash
# Check Docker resources
docker system df

# Check logs
docker compose logs dse-node

# Restart specific service
docker compose restart dse-node
```

### Issue: Cluster not forming

```bash
# Check network connectivity
# (Single node setup - no inter-node communication needed)

# Check Cassandra logs
docker exec dse-node tail -f /var/log/cassandra/system.log
```

### Issue: Can't connect with cqlsh

```bash
# Verify port is listening
docker exec dse-node netstat -tlnp | grep 9042

# Check if node is ready
docker exec dse-node nodetool status
```

### Issue: Data generation fails

```bash
# Check if keyspace exists
docker exec dse-node cqlsh -e "DESC KEYSPACE training;"

# Verify connectivity
docker exec tools ping dse-node

# Check Python dependencies
docker exec tools pip list | grep cassandra
```

## Success Criteria

You have successfully completed this exercise when:

- ✅ Both Cassandra nodes are running (1 DSE + 1 HCD)
- ✅ Both nodes show status as "UN" (Up/Normal)
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
docker compose down

# Remove volumes (WARNING: deletes all data)
docker compose down -v

# Restart fresh
docker compose up -d
```

## Key Takeaways

1. **Cluster Formation**: Both DSE and HCD nodes run independently
2. **Schema Compatibility**: DSE schema can be adapted for HCD with minor changes
3. **Data Generation**: Sample data helps practice migration scenarios
4. **Monitoring**: Essential for tracking migration progress
5. **Tools**: Pre-configured tools simplify migration tasks

---

**Time to Complete:** 30-45 minutes  
**Difficulty:** Beginner  
**Next Exercise:** [Native Tooling Migration](02-native-tooling.md)