#!/bin/bash
# Adapt CQL from DSE DESC KEYSPACE / DESC TABLE for HCD (Cassandra 4.x).
# Strips table options that DSE 6.x emits but HCD does not accept.
#
# Usage:
#   docker exec dse-node cqlsh -e "DESC KEYSPACE training;" | ./adapt_dse_schema_for_hcd.sh > training_schema_hcd.cql
#   docker exec -i hcd-node cqlsh < training_schema_hcd.cql

set -euo pipefail

sed -E \
  -e '/dclocal_read_repair_chance/d' \
  -e '/[[:space:]]AND[[:space:]]+read_repair_chance[[:space:]]*=/d' \
  -e '/^[[:space:]]+read_repair_chance[[:space:]]*=/d'
