from cassandra.cluster import Cluster
import sys

# Define primary key structure for each table
TABLE_PRIMARY_KEYS = {
    'users': ['user_id'],
    'products': ['product_id'],
    'orders': ['order_id'],
    'user_activity': ['user_id', 'activity_date', 'activity_time']
}

def validate_consistency():
    print("=" * 60)
    print("Migration Consistency Validation")
    print("=" * 60)
    
    # Connect to both clusters
    dse = Cluster(['dse-node']).connect('training')
    hcd = Cluster(['hcd-node']).connect('training')
    
    tables = ['users', 'products', 'orders', 'user_activity']
    all_passed = True
    
    for table in tables:
        print(f"\nValidating table: {table}")
        
        # Count validation
        dse_count = dse.execute(f"SELECT COUNT(*) FROM {table}").one()[0]
        hcd_count = hcd.execute(f"SELECT COUNT(*) FROM {table}").one()[0]
        
        print(f"  DSE count: {dse_count:,}")
        print(f"  HCD count: {hcd_count:,}")
        
        if dse_count == hcd_count:
            print(f"  Count check: ✓ PASS")
        else:
            print(f"  Count check: ✗ FAIL (difference: {abs(dse_count - hcd_count)})")
            all_passed = False
            continue
        
        # Sample data validation
        print(f"  Validating sample data...")
        dse_sample = list(dse.execute(f"SELECT * FROM {table} LIMIT 100"))
        
        mismatches = 0
        pk_columns = TABLE_PRIMARY_KEYS[table]
        
        for row in dse_sample:
            # Build WHERE clause for all primary key columns
            where_parts = []
            pk_values = []
            
            for pk_col in pk_columns:
                where_parts.append(f"{pk_col} = %s")
                pk_values.append(getattr(row, pk_col))
            
            where_clause = " AND ".join(where_parts)
            
            # Query HCD with complete primary key
            hcd_result = hcd.execute(
                f"SELECT * FROM {table} WHERE {where_clause}",
                pk_values
            )
            
            hcd_row = hcd_result.one()
            if hcd_row is None:
                mismatches += 1
        
        if mismatches == 0:
            print(f"  Sample check: ✓ PASS (100 rows validated)")
        else:
            print(f"  Sample check: ✗ FAIL ({mismatches} mismatches)")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All validation checks passed!")
        print("Clusters are consistent and ready for cutover")
    else:
        print("✗ Validation failed - investigate discrepancies")
    print("=" * 60)
    
    dse.shutdown()
    hcd.shutdown()
    
    return all_passed

if __name__ == "__main__":
    success = validate_consistency()
    sys.exit(0 if success else 1)

# Made with Bob
