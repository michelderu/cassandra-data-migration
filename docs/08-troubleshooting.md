# Troubleshooting Guide

## Table of Contents
1. [Common Issues](#common-issues)
2. [Cluster Issues](#cluster-issues)
3. [Migration Tool Issues](#migration-tool-issues)
4. [Performance Issues](#performance-issues)
5. [Data Consistency Issues](#data-consistency-issues)
6. [Network Issues](#network-issues)
7. [Lab Environment Issues](#lab-environment-issues)
8. [Diagnostic Commands](#diagnostic-commands)

## Common Issues

### Issue: Connection Timeout

**Symptoms:**
```
OperationTimedOut: errors={'127.0.0.1': 'Client request timeout'}
Connection refused
```

**Possible Causes:**
- Cluster not fully started
- Network connectivity issues
- Firewall blocking ports
- Node overloaded

**Solutions:**

```bash
# 1. Check if node is up
nodetool status

# 2. Verify port is listening
netstat -tlnp | grep 9042

# 3. Test connectivity
telnet <node-ip> 9042

# 4. Check node logs
tail -f /var/log/cassandra/system.log

# 5. Increase timeout in application
# For Python driver:
cluster = Cluster(
    contact_points=['node1'],
    connect_timeout=30,
    control_connection_timeout=30
)
```

### Issue: Authentication Failed

**Symptoms:**
```
AuthenticationFailed: Remote end requires authentication
Provided username cassandra and/or password are incorrect
```

**Solutions:**

```bash
# 1. Verify credentials
cqlsh -u cassandra -p cassandra

# 2. Check authentication configuration
# In cassandra.yaml:
grep authenticator /etc/cassandra/cassandra.yaml

# 3. Reset password if needed
cqlsh -u cassandra -p cassandra
ALTER ROLE cassandra WITH PASSWORD = 'new_password';

# 4. For DSE, check dse.yaml
grep authentication_options /etc/dse/dse.yaml
```

### Issue: Schema Mismatch

**Symptoms:**
```
InvalidRequest: Keyspace 'myapp' does not exist
Table 'users' does not exist
Column 'new_field' not found
```

**Solutions:**

```bash
# 1. Verify keyspace exists
cqlsh -e "DESC KEYSPACE myapp;"

# 2. Compare schemas
cqlsh dse-node1 -e "DESC KEYSPACE myapp;" > dse_schema.cql
cqlsh hcd-node1 -e "DESC KEYSPACE myapp;" > hcd_schema.cql
diff dse_schema.cql hcd_schema.cql

# 3. Create missing schema
cqlsh hcd-node1 < schema.cql

# 4. Verify table structure
cqlsh -e "DESC TABLE myapp.users;"
```

## Cluster Issues

### Issue: Node Won't Join Cluster

**Symptoms:**
```
Node shows as DN (Down/Normal) in nodetool status
Logs show: "Unable to gossip with any seeds"
```

**Solutions:**

```bash
# 1. Check seed configuration
grep seeds /etc/cassandra/cassandra.yaml

# 2. Verify network connectivity to seeds
ping <seed-node>
telnet <seed-node> 7000

# 3. Check if ports are open
netstat -tlnp | grep -E '7000|7001|9042'

# 4. Review logs for specific errors
grep ERROR /var/log/cassandra/system.log

# 5. Clear data and rejoin (CAUTION: data loss)
nodetool drain
rm -rf /var/lib/cassandra/data/*
rm -rf /var/lib/cassandra/commitlog/*
rm -rf /var/lib/cassandra/saved_caches/*
# Restart Cassandra
```

### Issue: Split Brain / Multiple Clusters

**Symptoms:**
```
nodetool status shows different cluster names
Nodes can't see each other
Data inconsistency
```

**Solutions:**

```bash
# 1. Check cluster name on all nodes
nodetool describecluster

# 2. Verify cluster_name in cassandra.yaml matches
grep cluster_name /etc/cassandra/cassandra.yaml

# 3. Check network partitioning
# From each node, ping all other nodes

# 4. If cluster names differ, fix and restart
# Edit cassandra.yaml
cluster_name: 'Correct_Cluster_Name'
# Restart node

# 5. Force cluster reformation (LAST RESORT)
# Stop all nodes
# Clear system tables
# Restart with correct configuration
```

### Issue: High Compaction Lag

**Symptoms:**
```
nodetool compactionstats shows many pending compactions
Disk usage growing
Read performance degrading
```

**Solutions:**

```bash
# 1. Check compaction status
nodetool compactionstats

# 2. Check pending compactions
nodetool tpstats | grep CompactionExecutor

# 3. Increase compaction throughput temporarily
nodetool setcompactionthroughput 128

# 4. Add more compaction threads
# In cassandra.yaml:
concurrent_compactors: 4

# 5. Trigger manual compaction (off-peak hours)
nodetool compact keyspace table

# 6. Monitor progress
watch -n 5 'nodetool compactionstats'
```

## Migration Tool Issues

### Issue: SSTableLoader Fails

**Symptoms:**
```
Error: Cannot find schema for keyspace
Connection refused
Streaming failed
```

**Solutions:**

```bash
# 1. Verify schema exists on target
cqlsh hcd-node1 -e "DESC KEYSPACE myapp;"

# 2. Check connectivity
telnet hcd-node1 9042

# 3. Verify SSTable format compatibility
# Check SSTable version
ls -la /path/to/sstables/

# 4. Use correct options
sstableloader \
  -d hcd-node1,hcd-node2,hcd-node3 \
  -u cassandra \
  -pw cassandra \
  --throttle 50 \
  /path/to/sstables/

# 5. Check target cluster capacity
nodetool status
df -h /var/lib/cassandra
```

### Issue: DSBulk Export/Import Fails

**Symptoms:**
```
Error: Connection timeout
Out of memory
Invalid data format
```

**Solutions:**

```bash
# 1. Increase timeout
dsbulk unload \
  -h dse-node1 \
  -k myapp \
  -t users \
  -url /export \
  --driver.advanced.connection.init-query-timeout "30 seconds"

# 2. Reduce batch size for memory issues
dsbulk load \
  --executor.maxPerSecond 1000 \
  --connector.csv.maxConcurrentFiles 2

# 3. Check data format
head -n 5 /export/data.csv

# 4. Validate CSV structure
dsbulk load --dryRun true

# 5. Check logs
tail -f /var/log/dsbulk/operation.log
```

### Issue: ZDM Proxy Not Working

**Symptoms:**
```
Proxy won't start
Applications can't connect through proxy
Dual-write not working
```

**Solutions:**

```bash
# 1. Check proxy logs
docker logs zdm-proxy

# 2. Verify configuration
cat zdm-config.yml

# 3. Test connectivity to both clusters
telnet dse-node1 9042
telnet hcd-node1 9042

# 4. Check proxy port
netstat -tlnp | grep 9044

# 5. Verify proxy metrics
curl http://localhost:14001/metrics

# 6. Restart proxy with verbose logging
# In config:
log_level: "DEBUG"
```

### Issue: CDM Job Fails

**Symptoms:**
```
Spark job fails
Out of memory errors
Task failures
```

**Solutions:**

```bash
# 1. Check Spark logs
tail -f /var/log/spark/spark-worker.log

# 2. Increase executor memory
spark-submit \
  --executor-memory 16g \
  --driver-memory 8g \
  cassandra-data-migrator.jar

# 3. Reduce batch size
# In cdm.properties:
spark.cdm.perfops.batchSize=5

# 4. Increase partitions
spark.cdm.perfops.numParts=500

# 5. Check Spark UI for details
# http://spark-master:4040
```

## Performance Issues

### Issue: Slow Reads

**Symptoms:**
```
High read latency
Timeouts on SELECT queries
Application slowness
```

**Solutions:**

```bash
# 1. Check read latency
nodetool tablestats myapp.users | grep "Read Latency"

# 2. Check for pending compactions
nodetool compactionstats

# 3. Verify consistency level
# Use LOCAL_QUORUM instead of ALL

# 4. Check if repair is needed
nodetool repair myapp

# 5. Monitor thread pools
nodetool tpstats

# 6. Check for large partitions
nodetool tablehistograms myapp users

# 7. Add more nodes if needed
# Or increase read_request_timeout_in_ms
```

### Issue: Slow Writes

**Symptoms:**
```
High write latency
Write timeouts
Commitlog growing
```

**Solutions:**

```bash
# 1. Check write latency
nodetool tablestats myapp.users | grep "Write Latency"

# 2. Check commitlog
ls -lh /var/lib/cassandra/commitlog/

# 3. Verify disk I/O
iostat -x 1 10

# 4. Check memtable flush
nodetool tpstats | grep MemtableFlushWriter

# 5. Tune commitlog
# In cassandra.yaml:
commitlog_sync: periodic
commitlog_sync_period_in_ms: 10000

# 6. Check for disk space
df -h /var/lib/cassandra
```

### Issue: High CPU Usage

**Symptoms:**
```
CPU at 100%
System unresponsive
Queries timing out
```

**Solutions:**

```bash
# 1. Check CPU usage
top -bn1 | grep cassandra

# 2. Check for expensive queries
# Enable query logging
# In cassandra.yaml:
slow_query_log_timeout_in_ms: 500

# 3. Check compaction activity
nodetool compactionstats

# 4. Reduce compaction throughput
nodetool setcompactionthroughput 32

# 5. Check for repair running
nodetool compactionstats | grep Repair

# 6. Review query patterns
# Look for ALLOW FILTERING queries
```

## Data Consistency Issues

### Issue: Row Count Mismatch

**Symptoms:**
```
Different row counts between clusters
Missing data on target
Extra data on target
```

**Solutions:**

```bash
# 1. Compare counts
cqlsh dse-node1 -e "SELECT COUNT(*) FROM myapp.users;"
cqlsh hcd-node1 -e "SELECT COUNT(*) FROM myapp.users;"

# 2. Check for ongoing writes
# Stop writes temporarily

# 3. Run repair on both clusters
nodetool repair myapp

# 4. Sample data comparison
cqlsh dse-node1 -e "SELECT * FROM myapp.users LIMIT 100;" > dse_sample.txt
cqlsh hcd-node1 -e "SELECT * FROM myapp.users LIMIT 100;" > hcd_sample.txt
diff dse_sample.txt hcd_sample.txt

# 5. Use validation tool
python3 validate_consistency.py

# 6. Re-migrate missing data
# Identify missing partition ranges
# Re-run migration for those ranges
```

### Issue: Data Corruption

**Symptoms:**
```
Null values where data should exist
Garbled text
Incorrect data types
```

**Solutions:**

```bash
# 1. Check for encoding issues
# Verify UTF-8 encoding

# 2. Validate data types
cqlsh -e "DESC TABLE myapp.users;"

# 3. Check for TTL expiration
cqlsh -e "SELECT TTL(column) FROM myapp.users LIMIT 10;"

# 4. Run scrub on affected tables
nodetool scrub myapp users

# 5. Restore from backup if needed
# Use snapshot or backup

# 6. Re-migrate affected data
# With proper encoding and type handling
```

## Network Issues

### Issue: Network Latency

**Symptoms:**
```
High inter-node latency
Slow replication
Timeout errors
```

**Solutions:**

```bash
# 1. Measure latency between nodes
ping -c 10 <node-ip>

# 2. Check network bandwidth
iperf3 -s  # On one node
iperf3 -c <node-ip>  # On another

# 3. Check for packet loss
mtr <node-ip>

# 4. Verify network configuration
ifconfig
route -n

# 5. Check for network congestion
netstat -s | grep retransmit

# 6. Adjust timeouts if needed
# In cassandra.yaml:
read_request_timeout_in_ms: 10000
write_request_timeout_in_ms: 5000
```

### Issue: Firewall Blocking

**Symptoms:**
```
Connection refused
Nodes can't communicate
Clients can't connect
```

**Solutions:**

```bash
# 1. Check if ports are open
telnet <node-ip> 9042
telnet <node-ip> 7000

# 2. List firewall rules
iptables -L -n

# 3. Open required ports
# CQL: 9042
# Inter-node: 7000, 7001
# JMX: 7199

# For iptables:
iptables -A INPUT -p tcp --dport 9042 -j ACCEPT
iptables -A INPUT -p tcp --dport 7000 -j ACCEPT

# For firewalld:
firewall-cmd --permanent --add-port=9042/tcp
firewall-cmd --reload

# 4. Check security groups (cloud)
# Ensure proper ingress/egress rules
```

## Lab Environment Issues

### Issue: Docker Containers Won't Start

**Symptoms:**
```
Container exits immediately
Health check failing
Port conflicts
```

**Solutions:**

```bash
# 1. Check container logs
docker logs dse-node1

# 2. Check resource usage
docker stats

# 3. Check for port conflicts
netstat -tlnp | grep 9042

# 4. Increase Docker resources
# Docker Desktop: Settings > Resources
# Colima: colima start --cpu 6 --memory 12

# 5. Clean up and restart
docker-compose down -v
docker system prune -a
docker-compose up -d

# 6. Check disk space
df -h
docker system df
```

### Issue: Colima Issues

**Symptoms:**
```
Colima won't start
Insufficient resources
Network issues
```

**Solutions:**

```bash
# 1. Check Colima status
colima status

# 2. Restart with more resources
colima stop
colima start --cpu 6 --memory 12 --disk 60

# 3. Check Colima logs
colima logs

# 4. Reset Colima (CAUTION: deletes all data)
colima delete
colima start --cpu 6 --memory 12 --disk 60

# 5. Check network
colima ssh
ping google.com
```

## Diagnostic Commands

### Cluster Health

```bash
# Overall cluster status
nodetool status

# Cluster information
nodetool describecluster

# Ring information
nodetool ring

# Node information
nodetool info

# Check gossip
nodetool gossipinfo
```

### Performance Metrics

```bash
# Thread pool stats
nodetool tpstats

# Table statistics
nodetool tablestats keyspace.table

# Compaction stats
nodetool compactionstats

# Histogram data
nodetool tablehistograms keyspace table

# Proxyhistograms
nodetool proxyhistograms
```

### Data Validation

```bash
# Row count
cqlsh -e "SELECT COUNT(*) FROM keyspace.table;"

# Sample data
cqlsh -e "SELECT * FROM keyspace.table LIMIT 10;"

# Check for tombstones
nodetool tablestats keyspace.table | grep Tombstone

# SSTable count
nodetool tablestats keyspace.table | grep "SSTable count"
```

### System Resources

```bash
# CPU usage
top -bn1 | head -20

# Memory usage
free -h

# Disk usage
df -h
du -sh /var/lib/cassandra/*

# Disk I/O
iostat -x 1 5

# Network usage
iftop -i eth0
```

### Logs

```bash
# Cassandra system log
tail -f /var/log/cassandra/system.log

# Search for errors
grep ERROR /var/log/cassandra/system.log

# Search for warnings
grep WARN /var/log/cassandra/system.log

# GC logs
tail -f /var/log/cassandra/gc.log

# Debug log
tail -f /var/log/cassandra/debug.log
```

## Getting Help

### Information to Collect

When seeking help, collect:

1. **Version Information**
```bash
nodetool version
cqlsh --version
```

2. **Cluster Status**
```bash
nodetool status
nodetool describecluster
```

3. **Error Messages**
```bash
grep ERROR /var/log/cassandra/system.log | tail -50
```

4. **Configuration**
```bash
cat /etc/cassandra/cassandra.yaml
```

5. **System Resources**
```bash
free -h
df -h
top -bn1 | head -20
```

### Resources

- **Documentation**: Review docs in [`../docs/`](../docs/)
- **Exercises**: Check exercise guides in [`exercises/`](.)
- **Community**: DataStax Community Forums
- **GitHub**: Check tool repositories for known issues

## Summary

**Key Troubleshooting Steps:**

1. **Check Logs** - Always start with logs
2. **Verify Connectivity** - Test network and ports
3. **Check Resources** - CPU, memory, disk
4. **Validate Configuration** - Review settings
5. **Test Incrementally** - Isolate the problem
6. **Monitor Metrics** - Use nodetool and monitoring tools
7. **Document Issues** - Keep track of problems and solutions

**Prevention:**

- Regular monitoring
- Proper capacity planning
- Thorough testing before production
- Maintain backups
- Document configurations
- Keep systems updated

---

**Related Documents:**
- [Migration Overview](01-migration-overview.md)
- [Challenges and Risks](07-challenges-risks.md)
- [Lab Environment Setup](../lab/README.md)