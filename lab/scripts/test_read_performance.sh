#!/bin/bash
# Test read performance across DSE, HCD, and ZDM Proxy

set -e

echo "=========================================="
echo "Read Performance Test"
echo "=========================================="
echo ""

# Test parameters
KEYSPACE="training"
TABLE="users"
ITERATIONS=100

# Function to test read performance
test_read_performance() {
    local HOST=$1
    local PORT=$2
    local NAME=$3
    
    echo "Testing $NAME ($HOST:$PORT)..."
    
    START_TIME=$(date +%s%N)
    
    for i in $(seq 1 $ITERATIONS); do
        cqlsh $HOST $PORT -e "SELECT * FROM ${KEYSPACE}.${TABLE} WHERE user_id = uuid() LIMIT 1;" > /dev/null 2>&1 || true
    done
    
    END_TIME=$(date +%s%N)
    DURATION=$((($END_TIME - $START_TIME) / 1000000))
    AVG_LATENCY=$(($DURATION / $ITERATIONS))
    
    echo "  Total time: ${DURATION}ms"
    echo "  Average latency: ${AVG_LATENCY}ms"
    echo "  Throughput: $(($ITERATIONS * 1000 / $DURATION)) req/s"
    echo ""
}

# Test DSE cluster
test_read_performance "dse-node" 9042 "DSE Cluster"

# Test HCD cluster
test_read_performance "hcd-node" 9042 "HCD Cluster"

# Test ZDM Proxy
test_read_performance "zdm-proxy" 9042 "ZDM Proxy"

echo "=========================================="
echo "Performance test complete"
echo "=========================================="

# Made with Bob
