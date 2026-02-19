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
docker-compose up -d dse-node

# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v

# Restart specific service
docker-compose restart dse-node

# Stop specific service
docker-compose stop hcd-node

# Start stopped service
docker-compose start hcd-node
```

### Viewing Status

```bash
# View all containers
docker-compose ps

# View specific service
docker-compose ps dse-node

# View logs
docker-compose logs -f dse-node

# View logs for all services
docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100 dse-node
```

### Accessing Containers

```bash
# Access DSE node shell
docker exec -it dse-node bash

# Access HCD node shell
docker exec -it hcd-node bash

# Access migration tools container
docker exec -it migration-tools bash

# Access as root user
docker exec -u root -it dse-node bash

# Run single command
docker exec dse-node nodetool status
```

## Cluster Operations

### DSE Cluster

```bash
# Check cluster status
docker exec dse-node nodetool status

# Get cluster info
docker exec dse-node nodetool info

# Check ring
docker exec dse-node nodetool ring

# Describe cluster
docker exec dse-node nodetool describecluster

# Check gossip info
docker exec dse-node nodetool gossipinfo

# Thread pool stats
docker exec dse-node nodetool tpstats

# Compaction stats
docker exec dse-node nodetool compactionstats

# Table stats
docker exec dse-node nodetool tablestats training

# Proxy histograms
docker exec dse-node nodetool proxyhistograms
```

### HCD Cluster

```bash
# Check cluster status
docker exec hcd-node nodetool status

# Get cluster info
docker exec hcd-node nodetool info

# Check ring
docker exec hcd-node nodetool ring

# Describe cluster
docker exec hcd-node nodetool describecluster

# Thread pool stats
docker exec hcd-node nodetool tpstats

# Compaction stats
docker exec hcd-node nodetool compactionstats

# Table stats
docker exec hcd-node nodetool tablestats training

# Repair keyspace
docker exec hcd-node nodetool repair training
```

### CQL Access

```bash
# Connect to DSE via cqlsh
docker exec -it dse-node cqlsh

# Connect to HCD via cqlsh
docker exec -it hcd-node cqlsh

# Connect through ZDM Proxy
docker exec -it migration-tools cqlsh zdm-proxy 9042

# Execute single query on DSE
docker exec dse-node cqlsh -e "SELECT COUNT(*) FROM training.users;"

# Execute single query on HCD
docker exec hcd-node cqlsh -e "SELECT COUNT(*) FROM training.users;"

# Execute CQL file
docker exec -i dse-node cqlsh < init-scripts/01-create-schema.cql

# From host machine (if cqlsh installed)
cqlsh localhost 9042  # DSE
cqlsh localhost 9043  # HCD
cqlsh localhost 9044  # ZDM Proxy
```

## Data Operations

### Snapshots

```bash
# Create snapshot on DSE
docker exec dse-node nodetool snapshot training -t my_snapshot

# List snapshots
docker exec dse-node nodetool listsnapshots

# Clear specific snapshot
docker exec dse-node nodetool clearsnapshot -t my_snapshot training

# Clear all snapshots
docker exec dse-node nodetool clearsnapshot --all
```

### Data Export/Import

```bash
# Export data using COPY (from within container)
docker exec -it migration-tools bash -c "
cqlsh dse-node -e \"
COPY training.users TO '/exports/users.csv' WITH HEADER = true;
\"
"

# Import data using COPY
docker exec -it migration-tools bash -c "
cqlsh hcd-node -e \"
COPY training.users FROM '/exports/users.csv' WITH HEADER = true;
\"
"

# Copy files between host and container
docker cp dse-node:/tmp/data.csv ./data.csv
docker cp ./data.csv migration-tools:/exports/
```

### DSBulk Operations

```bash
# Export with DSBulk
docker exec -it migration-tools bash -c "
dsbulk unload \
  -h dse-node \
  -k training \
  -t users \
  -url /exports/users
"

# Import with DSBulk
docker exec -it migration-tools bash -c "
dsbulk load \
  -h hcd-node \
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
docker stats dse-node

# One-time snapshot
docker stats --no-stream

# Format output
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

## Troubleshooting

### Logs

```bash
# View container logs
docker logs dse-node

# Follow logs
docker logs -f dse-node

# Last 100 lines
docker logs --tail=100 dse-node

# Logs since timestamp
docker logs --since 2024-01-01T00:00:00 dse-node

# View Cassandra system log
docker exec dse-node tail -f /var/log/cassandra/system.log

# Search for errors
docker exec dse-node grep ERROR /var/log/cassandra/system.log
```

### Container Inspection

```bash
# Inspect container
docker inspect dse-node

# Get IP address
docker inspect dse-node | jq '.[0].NetworkSettings.Networks'

# Get environment variables
docker inspect dse-node | jq '.[0].Config.Env'

# Get mounts
docker inspect dse-node | jq '.[0].Mounts'
```

### Health Checks

```bash
# Check container health
docker inspect dse-node | jq '.[0].State.Health'

# View health check logs
docker inspect dse-node | jq '.[0].State.Health.Log'
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
docker exec dse-node ping hcd-node
docker exec dse-node ping -c 3 hcd-node

# Check if port is listening
docker exec dse-node netstat -tlnp | grep 9042

# Test port connectivity
docker exec migration-tools telnet dse-node 9042
```

### Restart Strategies

```bash
# Restart single node
docker-compose restart dse-node

# Restart cluster (DSE)
docker-compose restart dse-node dse-node dse-node

# Restart cluster (HCD)
docker-compose restart hcd-node hcd-node hcd-node

# Restart all services
docker-compose restart

# Force recreate container
docker-compose up -d --force-recreate dse-node
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
docker port dse-node 9042

# List all ports for container
docker port dse-node
```

### DNS Resolution

```bash
# Test DNS resolution
docker exec migration-tools nslookup dse-node
docker exec migration-tools nslookup hcd-node

# Test with ping
docker exec migration-tools ping -c 3 dse-node
```

## Volume Management

### Volume Operations

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect lab_dse-node-data

# Remove specific volume (WARNING: deletes data)
docker volume rm lab_dse-node-data

# Remove all unused volumes
docker volume prune
```

### Backup Volumes

```bash
# Backup volume to tar
docker run --rm \
  -v lab_dse-node-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/dse-node-backup.tar.gz /data

# Restore volume from tar
docker run --rm \
  -v lab_dse-node-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/dse-node-backup.tar.gz -C /
```

## Useful Aliases

Add these to your `~/.bashrc` or `~/.zshrc`:

```bash
# Container access
alias dse1='docker exec -it dse-node bash'
alias hcd1='docker exec -it hcd-node bash'
alias tools='docker exec -it migration-tools bash'

# CQL access
alias cqldse='docker exec -it dse-node cqlsh'
alias cqlhcd='docker exec -it hcd-node cqlsh'
alias cqlzdm='docker exec -it migration-tools cqlsh zdm-proxy 9042'

# Cluster status
alias dse-status='docker exec dse-node nodetool status'
alias hcd-status='docker exec hcd-node nodetool status'

# Logs
alias dse-logs='docker logs -f dse-node'
alias hcd-logs='docker logs -f hcd-node'
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
docker exec dse-node nodetool status
docker exec hcd-node nodetool status
```

### Quick Health Check

```bash
# Check all services
docker-compose ps

# Check DSE cluster
docker exec dse-node nodetool status | grep UN

# Check HCD cluster
docker exec hcd-node nodetool status | grep UN

# Check data
docker exec dse-node cqlsh -e "SELECT COUNT(*) FROM training.users;"
docker exec hcd-node cqlsh -e "SELECT COUNT(*) FROM training.users;"
```

### Performance Check

```bash
# Resource usage
docker stats --no-stream

# Cluster performance
docker exec dse-node nodetool tpstats
docker exec hcd-node nodetool tpstats

# Compaction status
docker exec dse-node nodetool compactionstats
docker exec hcd-node nodetool compactionstats
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
- Nodetool: `docker exec dse-node nodetool help`
- CQLsh: `docker exec dse-node cqlsh --help`
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
docker exec dse-node nodetool status
docker exec hcd-node nodetool status
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