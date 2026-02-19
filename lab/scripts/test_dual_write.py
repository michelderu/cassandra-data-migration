from cassandra.cluster import Cluster
import uuid
from datetime import datetime

# Connect through ZDM Proxy
cluster = Cluster(['zdm-proxy'], port=9042)
session = cluster.connect('training')

# Prepare statement
insert_stmt = session.prepare("""
    INSERT INTO users (user_id, username, email, status, created_at)
    VALUES (?, ?, ?, ?, ?)
""")

print("Inserting 100 test users through ZDM Proxy...")

for i in range(100):
    session.execute(insert_stmt, (
        uuid.uuid4(),
        f'zdm_bulk_user_{i}',
        f'zdm_bulk_{i}@test.com',
        'active',
        datetime.now()
    ))
    
    if (i + 1) % 10 == 0:
        print(f"  Inserted {i + 1} users...")

print("✓ Bulk insert complete")

cluster.shutdown()

# Made with Bob
