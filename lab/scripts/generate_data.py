#!/usr/bin/env python3
"""
Data generator for migration lab exercises.
Generates sample data for training keyspace.
"""

import uuid
import random
from datetime import datetime, timedelta, date
from decimal import Decimal
from cassandra.cluster import Cluster
import sys

# Sample data
FIRST_NAMES = ['John', 'Jane', 'Michael', 'Sarah', 'David', 'Emily', 'Robert', 'Lisa', 'James', 'Mary']
LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
STATUSES = ['active', 'inactive', 'pending', 'suspended']
CATEGORIES = ['Electronics', 'Clothing', 'Books', 'Home', 'Sports', 'Toys', 'Food', 'Beauty']
ACTIVITY_TYPES = ['login', 'logout', 'purchase', 'view_product', 'add_to_cart', 'remove_from_cart']

def connect_to_cluster(host='dse-node1', port=9042):
    """Connect to Cassandra cluster"""
    print(f"Connecting to {host}:{port}...")
    cluster = Cluster([host], port=port)
    session = cluster.connect('training')
    print("Connected successfully!")
    return cluster, session

def generate_users(session, count=1000):
    """Generate sample users"""
    print(f"Generating {count} users...")
    
    insert_stmt = session.prepare("""
        INSERT INTO users (user_id, username, email, first_name, last_name, 
                          created_at, updated_at, status, preferences)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)
    
    user_ids = []
    for i in range(count):
        user_id = uuid.uuid4()
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        username = f"{first_name.lower()}.{last_name.lower()}{i}"
        email = f"{username}@example.com"
        created_at = datetime.now() - timedelta(days=random.randint(1, 365))
        updated_at = created_at + timedelta(days=random.randint(0, 30))
        status = random.choice(STATUSES)
        preferences = {
            'theme': random.choice(['light', 'dark']),
            'language': random.choice(['en', 'es', 'fr']),
            'notifications': random.choice(['enabled', 'disabled'])
        }
        
        session.execute(insert_stmt, (
            user_id, username, email, first_name, last_name,
            created_at, updated_at, status, preferences
        ))
        
        user_ids.append(user_id)
        
        if (i + 1) % 100 == 0:
            print(f"  Generated {i + 1} users...")
    
    print(f"✓ Generated {count} users")
    return user_ids

def generate_products(session, count=500):
    """Generate sample products"""
    print(f"Generating {count} products...")
    
    insert_stmt = session.prepare("""
        INSERT INTO products (product_id, name, description, price, 
                             category, stock_quantity, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """)
    
    product_ids = []
    for i in range(count):
        product_id = uuid.uuid4()
        category = random.choice(CATEGORIES)
        name = f"{category} Product {i}"
        description = f"Description for {name}"
        price = Decimal(str(round(random.uniform(10.0, 1000.0), 2)))
        stock_quantity = random.randint(0, 1000)
        created_at = datetime.now() - timedelta(days=random.randint(1, 180))
        
        session.execute(insert_stmt, (
            product_id, name, description, price,
            category, stock_quantity, created_at
        ))
        
        product_ids.append(product_id)
        
        if (i + 1) % 100 == 0:
            print(f"  Generated {i + 1} products...")
    
    print(f"✓ Generated {count} products")
    return product_ids

def generate_orders(session, user_ids, product_ids, count=2000):
    """Generate sample orders"""
    print(f"Generating {count} orders...")
    
    insert_stmt = session.prepare("""
        INSERT INTO orders (order_id, user_id, order_date, total_amount, 
                           status, items, shipping_address)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """)
    
    for i in range(count):
        order_id = uuid.uuid4()
        user_id = random.choice(user_ids)
        order_date = datetime.now() - timedelta(days=random.randint(1, 90))
        num_items = random.randint(1, 5)
        items = [str(random.choice(product_ids)) for _ in range(num_items)]
        total_amount = Decimal(str(round(random.uniform(20.0, 500.0), 2)))
        status = random.choice(['pending', 'processing', 'shipped', 'delivered', 'cancelled'])
        shipping_address = f"{random.randint(1, 9999)} Main St, City, State {random.randint(10000, 99999)}"
        
        session.execute(insert_stmt, (
            order_id, user_id, order_date, total_amount,
            status, items, shipping_address
        ))
        
        if (i + 1) % 100 == 0:
            print(f"  Generated {i + 1} orders...")
    
    print(f"✓ Generated {count} orders")

def generate_user_activity(session, user_ids, count=5000):
    """Generate sample user activity"""
    print(f"Generating {count} user activity records...")
    
    insert_stmt = session.prepare("""
        INSERT INTO user_activity (user_id, activity_date, activity_time, 
                                   activity_type, details)
        VALUES (?, ?, ?, ?, ?)
    """)
    
    for i in range(count):
        user_id = random.choice(user_ids)
        activity_time = datetime.now() - timedelta(days=random.randint(0, 30), 
                                                   hours=random.randint(0, 23),
                                                   minutes=random.randint(0, 59))
        activity_date = activity_time.date()
        activity_type = random.choice(ACTIVITY_TYPES)
        details = f"User performed {activity_type} action"
        
        session.execute(insert_stmt, (
            user_id, activity_date, activity_time,
            activity_type, details
        ))
        
        if (i + 1) % 500 == 0:
            print(f"  Generated {i + 1} activity records...")
    
    print(f"✓ Generated {count} user activity records")

def print_statistics(session):
    """Print data statistics"""
    print("\n" + "="*50)
    print("Data Generation Complete!")
    print("="*50)
    
    tables = ['users', 'products', 'orders', 'user_activity']
    for table in tables:
        try:
            result = session.execute(f"SELECT COUNT(*) FROM {table}")
            count = result.one()[0]
            print(f"{table:20} : {count:,} rows")
        except Exception as e:
            print(f"{table:20} : Error - {e}")
    
    print("="*50)

def main():
    """Main function"""
    # Parse arguments
    host = sys.argv[1] if len(sys.argv) > 1 else 'dse-node1'
    
    # Connect to cluster
    cluster, session = connect_to_cluster(host)
    
    try:
        # Generate data
        user_ids = generate_users(session, count=1000)
        product_ids = generate_products(session, count=500)
        generate_orders(session, user_ids, product_ids, count=2000)
        generate_user_activity(session, user_ids, count=5000)
        
        # Print statistics
        print_statistics(session)
        
    finally:
        cluster.shutdown()
        print("\nConnection closed.")

if __name__ == '__main__':
    main()

# Made with Bob
