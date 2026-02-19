# Monitoring Setup for Cassandra Migration Lab

This directory contains monitoring configuration for the Cassandra migration lab environment.

## Components

### Prometheus
- **Port**: 9090
- **Configuration**: [`prometheus.yml`](prometheus.yml)
- Scrapes metrics from:
  - ZDM Proxy (port 14001)
  - DSE cluster nodes (JMX port 7199)
  - HCD cluster nodes (JMX port 7199)

### Grafana
- **Port**: 3000
- **Default credentials**: admin/admin
- **Auto-provisioned dashboards** from [datastax/zdm-proxy-automation](https://github.com/datastax/zdm-proxy-automation/tree/main/grafana-dashboards)

## Grafana Dashboards

Three dashboards are automatically provisioned in the "ZDM Migration" folder:

### 1. ZDM Proxy Dashboard
**File**: [`grafana-dashboards/zdm-proxy-dashboard.json`](grafana-dashboards/zdm-proxy-dashboard.json)

Main dashboard for monitoring ZDM Proxy operations:
- Request rates and latencies
- Read/write routing metrics
- Error rates and types
- Connection pool statistics
- Dual write performance
- Async read performance

### 2. ZDM Go Runtime Metrics
**File**: [`grafana-dashboards/zdm-go-runtime-metrics.json`](grafana-dashboards/zdm-go-runtime-metrics.json)

Go runtime metrics for ZDM Proxy:
- Memory usage and GC statistics
- Goroutine counts
- CPU usage
- Heap allocations
- GC pause times

### 3. Node Exporter Full
**File**: [`grafana-dashboards/node-exporter-full.json`](grafana-dashboards/node-exporter-full.json)

System-level metrics (requires node-exporter):
- CPU, memory, disk usage
- Network I/O
- System load
- Disk I/O

## Accessing Grafana

1. Start the lab environment:
   ```bash
   docker-compose up -d
   ```

2. Wait for Grafana to start (check with `docker-compose ps`)

3. Open Grafana in your browser:
   ```
   http://localhost:3000
   ```

4. Login with default credentials:
   - Username: `admin`
   - Password: `admin`

5. Navigate to **Dashboards** → **ZDM Migration** folder to view the dashboards

## Dashboard Provisioning

Dashboards are automatically loaded via Grafana provisioning:
- **Provisioning config**: [`grafana-provisioning/dashboards/dashboards.yml`](grafana-provisioning/dashboards/dashboards.yml)
- **Datasource config**: [`grafana-provisioning/datasources/prometheus.yml`](grafana-provisioning/datasources/prometheus.yml)
- **Dashboard files**: [`grafana-dashboards/`](grafana-dashboards/)

Changes to dashboard JSON files will be automatically detected and reloaded by Grafana.

## Monitoring ZDM Migration

During Exercise 4 (ZDM Migration), use these dashboards to:

1. **Monitor dual writes**: Check that writes are going to both clusters
2. **Track read routing**: Verify reads are being routed correctly (Origin → Target)
3. **Identify errors**: Watch for any connection or query errors
4. **Performance analysis**: Compare latencies between Origin and Target clusters
5. **Resource usage**: Monitor ZDM Proxy memory and CPU usage

## Troubleshooting

### Dashboards not appearing
- Check Grafana logs: `docker-compose logs grafana`
- Verify volume mounts in [`docker-compose.yml`](../docker-compose.yml)
- Ensure dashboard JSON files are valid

### No data in dashboards
- Verify Prometheus is scraping ZDM Proxy: http://localhost:9090/targets
- Check ZDM Proxy metrics endpoint: http://localhost:14001/metrics
- Ensure ZDM Proxy is running: `docker-compose ps zdm-proxy`

### Prometheus connection issues
- Check datasource configuration in Grafana UI
- Verify Prometheus is accessible: http://localhost:9090

## References

- [ZDM Proxy Documentation](https://docs.datastax.com/en/astra-serverless/docs/migrate/introduction.html)
- [ZDM Proxy Automation Repository](https://github.com/datastax/zdm-proxy-automation)
- [Grafana Provisioning Documentation](https://grafana.com/docs/grafana/latest/administration/provisioning/)