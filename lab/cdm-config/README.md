# CDM Configuration Files

This directory contains configuration files for Cassandra Data Migrator (CDM).

## Available Configurations

### Recommended: Consolidated Configuration
- **cdm.properties** - Consolidated configuration for all tables (recommended)
  - Contains common settings for source/target clusters
  - Use with `--conf` parameters to specify tables
  - Supports all four tables: users, products, orders, user_activity

## Usage

These configuration files are automatically mounted into the `spark-cdm` container at `/app/config/`.
The CDM JAR is located at `/assets/cassandra-data-migrator-5.6.3.jar` in the container.

### Recommended Approach: Using Consolidated Config

To run a migration with the consolidated config:

```bash
docker exec spark-cdm spark-submit \
  --class com.datastax.cdm.job.Migrate \
  --master 'local[*]' \
  --driver-memory 2g \
  --executor-memory 2g \
  --properties-file /app/config/cdm.properties \
  --conf spark.cdm.schema.origin.keyspaceTable=training.users \
  --conf spark.cdm.schema.target.keyspaceTable=training.users \
  /assets/cassandra-data-migrator-5.6.3.jar
```

To run validation with the consolidated config:

```bash
docker exec spark-cdm spark-submit \
  --class com.datastax.cdm.job.DiffData \
  --master 'local[*]' \
  --driver-memory 2g \
  --executor-memory 2g \
  --properties-file /app/config/cdm.properties \
  --conf spark.cdm.schema.origin.keyspaceTable=training.users \
  --conf spark.cdm.schema.target.keyspaceTable=training.users \
  /assets/cassandra-data-migrator-5.6.3.jar
```

## Configuration Parameters

All configurations use the updated CDM property format:

### Connection Settings
- `spark.cdm.connect.origin.*` - Source cluster connection (DSE)
  - `host`, `port`, `username`, `password`, `localDC`
- `spark.cdm.connect.target.*` - Target cluster connection (HCD)
  - `host`, `port`, `username`, `password`, `localDC`

### Schema Settings
- `spark.cdm.schema.origin.keyspaceTable` - Source table (e.g., `training.users`)
- `spark.cdm.schema.target.keyspaceTable` - Target table (e.g., `training.users`)

### Performance Tuning
- `spark.cdm.perfops.numParts` - Number of partitions for parallelism (default: 4)
- `spark.cdm.perfops.batchSize` - Batch size for writes (default: 5)
- `spark.cdm.perfops.fetchSizeInRows` - Fetch size for reads (default: 1000)
- `spark.cdm.perfops.ratelimit.origin` - Rate limit for source reads
- `spark.cdm.perfops.ratelimit.target` - Rate limit for target writes
- `spark.cdm.perfops.errorLimit` - Maximum errors before stopping (default: 100)

### Feature Flags
- `spark.cdm.feature.ttl.enabled` - Preserve TTL values (default: true)
- `spark.cdm.feature.writetime.enabled` - Preserve writetime values (default: true)

## Supported Tables

The configuration supports all four tables in the training keyspace:
- `training.users` - User accounts (10,000 rows)
- `training.products` - Product catalog (1,000 rows)
- `training.orders` - Order history (2,000 rows)
- `training.user_activity` - User activity logs (5,000 rows)

## Validation

After migration, validate data consistency using:

1. **Quick validation** with Python script:
   ```bash
   docker exec migration-tools python3 /scripts/validate_migration.py
   ```

2. **Detailed validation** with CDM DiffData:
   ```bash
   docker exec spark-cdm spark-submit \
     --class com.datastax.cdm.job.DiffData \
     --master 'local[*]' \
     --properties-file /app/config/cdm.properties \
     --conf spark.cdm.schema.origin.keyspaceTable=training.users \
     --conf spark.cdm.schema.target.keyspaceTable=training.users \
     /assets/cassandra-data-migrator-5.6.3.jar
   ```

## Customization

You can modify [`cdm.properties`](cdm.properties) or create new configuration files for different migration scenarios. The consolidated approach is recommended for consistency and maintainability.

## Additional Resources

- See [Exercise 04](../exercises/04-cdm-migration.md) for detailed usage instructions
- [CDM Official Documentation](https://docs.datastax.com/en/data-migration/cassandra-data-migrator.html)
- [CDM GitHub Repository](https://github.com/datastax/cassandra-data-migrator)