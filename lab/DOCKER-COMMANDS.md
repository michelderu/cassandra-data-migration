# Docker Command Reference for Lab Environment

## Quick Reference

This guide provides Docker-specific commands for working with the lab environment. All commands assume you're in the `lab/` directory.

## Table of Contents

1. [Container Management](#container-management)
2. [Cluster Operations](#cluster-operations)
3. [Data Operations](#data-operations)
4. [Monitoring](#monitoring)
5. [Troubleshooting](#troubleshooting)
6. [Network Operations](#network-operations)

## Container Management

### Starting and Stopping

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d dse-node1

# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v

# Restart specific service
docker-compose restart dse-node1

# Stop specific service
docker-compose stop hcd-node1

# Start stopped service
docker-compose start hcd-node1
```

### Viewing Status

```bash
# View all containers
docker-compose ps

# View specific service
docker-compose ps dse-node1

# View logs
docker-compose logs -f dse-node1

# View logs for all services
docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100 dse-node1
```

### Accessing Containers

```bash
# Access DSE node shell
docker exec -it dse-node1 bash

# Access HCD node shell
docker exec -it hcd-node1 bash

# Access migration tools container
docker exec -it migration-tools bash

# Access as root user
docker exec -u root -it dse-node1 bash

# Run single command
docker exec dse-node1 nodetool status
```

## Cluster Operations

### DSE Cluster

```bash
# Check cluster status
docker exec dse-node1 nodetool status

# Get cluster info
docker exec dse-node1 nodetool info

# Check ring
docker exec dse-node1 nodetool ring

# Describe cluster
docker exec dse-node1 nodetool describecluster

# Check gossip info
docker exec dse-node1 nodetool gossipinfo

# Thread pool stats
docker exec dse-node1 nodetool tpstats

# Compaction stats
docker exec dse-node1 nodetool compactionstats

# Table stats
docker exec dse-node1 nodetool tablestats training

# Proxy histograms
docker exec dse-node1 nodetool proxyhistograms
```

### HCD Cluster

```bash
# Check cluster status
docker exec hcd-node1 nodetool status

# Get cluster info
docker exec hcd-node1 nodetool info

# Check ring
docker exec hcd-node1 nodetool ring

# Describe cluster
docker exec hcd-node1 nodetool describecluster

# Thread pool stats
docker exec hcd-node1 nodetool tpstats

# Compaction stats
docker exec hcd-node1 nodetool compactionstats

# Table stats
docker exec hcd-node1 nodetool tablestats training

# Repair keyspace
docker exec hcd-node1 nodetool repair training
```

### CQL Access

```bash
# Connect to DSE via cqlsh
docker exec -it dse-node1 cqlsh

# Connect to HCD via cqlsh
docker exec -it hcd-node1 cqlsh

# Connect through ZDM Proxy
docker exec -it migration-tools cqlsh zdm-proxy 9042

# Execute single query on DSE
docker exec dse-node1 cqlsh -e "SELECT COUNT(*) FROM training.users;"

# Execute single query on HCD
docker exec hcd-node1 cqlsh -e "SELECT COUNT(*) FROM training.users;"

# Execute CQL file
docker exec -i dse-node1 cqlsh < init-scripts/01-create-schema.cql

# From host machine (if cqlsh installed)
cqlsh localhost 9042  # DSE
cqlsh localhost 9043  # HCD
cqlsh localhost 9044  # ZDM Proxy
```

## Data Operations

### Snapshots

```bash
# Create snapshot on DSE
docker exec dse-node1 nodetool snapshot training -t my_snapshot

# List snapshots
docker exec dse-node1 nodetool listsnapshots

# Clear specific snapshot
docker exec dse-node1 nodetool clearsnapshot -t my_snapshot training

# Clear all snapshots
docker exec dse-node1 nodetool clearsnapshot --all
```

### Data Export/Import

```bash
# Export data using COPY (from within container)
docker exec -it migration-tools bash -c "
cqlsh dse-node1 -e \"
COPY training.users TO '/exports/users.csv' WITH HEADER = true;
\"
"

# Import data using COPY
docker exec -it migration-tools bash -c "
cqlsh hcd-node1 -e \"
COPY training.users FROM '/exports/users.csv' WITH HEADER = true;
\"
"

# Copy files between host and container
docker cp dse-node1:/tmp/data.csv ./data.csv
docker cp ./data.csv migration-tools:/exports/
```

### DSBulk Operations

```bash
# Export with DSBulk
docker exec -it migration-tools bash -c "
dsbulk unload \
  -h dse-node1 \
  -k training \
  -t users \
  -url /exports/users
"

# Import with DSBulk
docker exec -it migration-tools bash -c "
dsbulk load \
  -h hcd-node1 \
  -k training \
  -t users \
  -url /exports/users
"
```

## Monitoring

### Prometheus

```bash
# Check Prometheus health
curl http://localhost:9090/-/healthy

# Query Prometheus API
curl 'http://localhost:9090/api/v1/query?query=up'

# Check targets
curl http://localhost:9090/api/v1/targets | jq

# Reload configuration
curl -X POST http://localhost:9090/-/reload
```

### Grafana

```bash
# Check Grafana health
curl http://localhost:3000/api/health

# Access Grafana UI
open http://localhost:3000
# Login: admin / admin

# List datasources
curl -u admin:admin http://localhost:3000/api/datasources
```

### ZDM Proxy Metrics

```bash
# Get all metrics
curl http://localhost:14001/metrics

# Filter specific metrics
curl http://localhost:14001/metrics | grep zdm_proxy_requests

# Get request count
curl http://localhost:14001/metrics | grep "zdm_proxy_requests_total"

# Get error count
curl http://localhost:14001/metrics | grep "zdm_proxy_errors_total"
```

### Container Resource Usage

```bash
# View resource usage for all containers
docker stats

# View specific container
docker stats dse-node1

# One-time snapshot
docker stats --no-stream

# Format output
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

## Troubleshooting

### Logs

```bash
# View container logs
docker logs dse-node1

# Follow logs
docker logs -f dse-node1

# Last 100 lines
docker logs --tail=100 dse-node1

# Logs since timestamp
docker logs --since 2024-01-01T00:00:00 dse-node1

# View Cassandra system log
docker exec dse-node1 tail -f /var/log/cassandra/system.log

# Search for errors
docker exec dse-node1 grep ERROR /var/log/cassandra/system.log
```

### Container Inspection

```bash
# Inspect container
docker inspect dse-node1

# Get IP address
docker inspect dse-node1 | jq '.[0].NetworkSettings.Networks'

# Get environment variables
docker inspect dse-node1 | jq '.[0].Config.Env'

# Get mounts
docker inspect dse-node1 | jq '.[0].Mounts'
```

### Health Checks

```bash
# Check container health
docker inspect dse-node1 | jq '.[0].State.Health'

# View health check logs
docker inspect dse-node1 | jq '.[0].State.Health.Log'
```

### Resource Issues

```bash
# Check disk usage
docker system df

# Clean up unused resources
docker system prune

# Remove unused volumes
docker volume prune

# Remove unused images
docker image prune -a

# Check Colima resources (if using Colima)
colima status
```

### Network Issues

```bash
# List networks
docker network ls

# Inspect network
docker network inspect lab_cassandra-migration

# Test connectivity between containers
docker exec dse-node1 ping hcd-node1
docker exec dse-node1 ping -c 3 hcd-node1

# Check if port is listening
docker exec dse-node1 netstat -tlnp | grep 9042

# Test port connectivity
docker exec migration-tools telnet dse-node1 9042
```

### Restart Strategies

```bash
# Restart single node
docker-compose restart dse-node1

# Restart cluster (DSE)
docker-compose restart dse-node1 dse-node2 dse-node3

# Restart cluster (HCD)
docker-compose restart hcd-node1 hcd-node2 hcd-node3

# Restart all services
docker-compose restart

# Force recreate container
docker-compose up -d --force-recreate dse-node1
```

## Network Operations

### Network Information

```bash
# List all networks
docker network ls

# Inspect migration network
docker network inspect lab_cassandra-migration

# View connected containers
docker network inspect lab_cassandra-migration | jq '.[0].Containers'
```

### Port Mappings

```bash
# View port mappings
docker-compose ps

# Check specific port
docker port dse-node1 9042

# List all ports for container
docker port dse-node1
```

### DNS Resolution

```bash
# Test DNS resolution
docker exec migration-tools nslookup dse-node1
docker exec migration-tools nslookup hcd-node1

# Test with ping
docker exec migration-tools ping -c 3 dse-node1
```

## Volume Management

### Volume Operations

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect lab_dse-node1-data

# Remove specific volume (WARNING: deletes data)
docker volume rm lab_dse-node1-data

# Remove all unused volumes
docker volume prune
```

### Backup Volumes

```bash
# Backup volume to tar
docker run --rm \
  -v lab_dse-node1-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/dse-node1-backup.tar.gz /data

# Restore volume from tar
docker run --rm \
  -v lab_dse-node1-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/dse-node1-backup.tar.gz -C /
```

## Useful Aliases

Add these to your `~/.bashrc` or `~/.zshrc`:

```bash
# Container access
alias dse1='docker exec -it dse-node1 bash'
alias hcd1='docker exec -it hcd-node1 bash'
alias tools='docker exec -it migration-tools bash'

# CQL access
alias cqldse='docker exec -it dse-node1 cqlsh'
alias cqlhcd='docker exec -it hcd-node1 cqlsh'
alias cqlzdm='docker exec -it migration-tools cqlsh zdm-proxy 9042'

# Cluster status
alias dse-status='docker exec dse-node1 nodetool status'
alias hcd-status='docker exec hcd-node1 nodetool status'

# Logs
alias dse-logs='docker logs -f dse-node1'
alias hcd-logs='docker logs -f hcd-node1'
alias zdm-logs='docker logs -f zdm-proxy'

# Lab management
alias lab-up='cd ~/projects/cassandra-data-migration/lab && docker-compose up -d'
alias lab-down='cd ~/projects/cassandra-data-migration/lab && docker-compose down'
alias lab-status='cd ~/projects/cassandra-data-migration/lab && docker-compose ps'
```

## Common Workflows

### Complete Lab Reset

```bash
# Stop everything
docker-compose down -v

# Clean up Docker
docker system prune -a --volumes

# Restart lab
docker-compose up -d

# Wait for clusters to form
sleep 60

# Verify
docker-compose ps
docker exec dse-node1 nodetool status
docker exec hcd-node1 nodetool status
```

### Quick Health Check

```bash
# Check all services
docker-compose ps

# Check DSE cluster
docker exec dse-node1 nodetool status | grep UN

# Check HCD cluster
docker exec hcd-node1 nodetool status | grep UN

# Check data
docker exec dse-node1 cqlsh -e "SELECT COUNT(*) FROM training.users;"
docker exec hcd-node1 cqlsh -e "SELECT COUNT(*) FROM training.users;"
```

### Performance Check

```bash
# Resource usage
docker stats --no-stream

# Cluster performance
docker exec dse-node1 nodetool tpstats
docker exec hcd-node1 nodetool tpstats

# Compaction status
docker exec dse-node1 nodetool compactionstats
docker exec hcd-node1 nodetool compactionstats
```

## Tips and Best Practices

### Resource Management

1. **Monitor resources**: Use `docker stats` regularly
2. **Clean up**: Run `docker system prune` periodically
3. **Limit containers**: Start only needed services
4. **Adjust limits**: Modify `mem_limit` and `cpus` in docker-compose.yml

### Debugging

1. **Check logs first**: Always start with `docker logs`
2. **Use verbose mode**: Add `-v` or `--verbose` to commands
3. **Test connectivity**: Use `ping` and `telnet` between containers
4. **Inspect containers**: Use `docker inspect` for detailed info

### Data Safety

1. **Backup before changes**: Create snapshots before risky operations
2. **Use volumes**: Data in volumes persists across container restarts
3. **Export important data**: Use DSBulk or COPY to export data
4. **Test in dev first**: Always test in lab before production

### Performance

1. **Use SSD**: Ensure Docker uses SSD storage
2. **Allocate resources**: Give Docker enough CPU and memory
3. **Monitor compaction**: Watch for compaction lag
4. **Tune heap**: Adjust MAX_HEAP_SIZE if needed

## Colima-Specific Commands

If using Colima instead of Docker Desktop:

```bash
# Start Colima
colima start --cpu 4 --memory 8 --disk 50

# Check status
colima status

# Stop Colima
colima stop

# Restart with more resources
colima stop
colima start --cpu 6 --memory 12 --disk 60

# SSH into Colima VM
colima ssh

# Delete Colima (WARNING: deletes all data)
colima delete

# List Colima instances
colima list
```

## Getting Help

### Documentation

- Docker Compose: `docker-compose --help`
- Docker: `docker --help`
- Nodetool: `docker exec dse-node1 nodetool help`
- CQLsh: `docker exec dse-node1 cqlsh --help`
- DSBulk: `docker exec migration-tools dsbulk --help`

### Useful Resources

- Lab README: `lab/README.md`
- Exercises: `lab/exercises/`
- Troubleshooting: `docs/08-troubleshooting.md`
- Main README: `README.md`

---

**Quick Start:**
```bash
cd lab
docker-compose up -d
docker-compose ps
docker exec dse-node1 nodetool status
docker exec hcd-node1 nodetool status
```

**Quick Stop:**
```bash
cd lab
docker-compose down
```

**Emergency Reset:**
```bash
cd lab
docker-compose down -v
docker system prune -a --volumes
docker-compose up -d