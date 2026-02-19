#!/bin/bash

echo "=== Read Performance Test ==="

# Test reads through proxy (currently from DSE)
echo "Testing reads through ZDM Proxy..."
START=$(date +%s%N)
for i in {1..100}; do
  cqlsh zdm-proxy 9042 -e "SELECT * FROM training.users LIMIT 10;" > /dev/null 2>&1
done
END=$(date +%s%N)
PROXY_TIME=$(( (END - START) / 1000000 ))
echo "ZDM Proxy (DSE): ${PROXY_TIME}ms for 100 queries"

# Test direct reads from DSE
echo "Testing direct reads from DSE..."
START=$(date +%s%N)
for i in {1..100}; do
  cqlsh dse-node1 -e "SELECT * FROM training.users LIMIT 10;" > /dev/null 2>&1
done
END=$(date +%s%N)
DSE_TIME=$(( (END - START) / 1000000 ))
echo "Direct DSE: ${DSE_TIME}ms for 100 queries"

# Test direct reads from HCD
echo "Testing direct reads from HCD..."
START=$(date +%s%N)
for i in {1..100}; do
  cqlsh hcd-node1 -e "SELECT * FROM training.users LIMIT 10;" > /dev/null 2>&1
done
END=$(date +%s%N)
HCD_TIME=$(( (END - START) / 1000000 ))
echo "Direct HCD: ${HCD_TIME}ms for 100 queries"

echo ""
echo "=== Performance Summary ==="
echo "ZDM Proxy overhead: $(( PROXY_TIME - DSE_TIME ))ms"
echo "HCD vs DSE: $(( HCD_TIME - DSE_TIME ))ms difference"

# Made with Bob
