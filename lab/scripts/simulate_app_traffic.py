#!/usr/bin/env python3
"""
Application Traffic Simulator for ZDM Migration

This script simulates realistic application traffic through the ZDM Proxy,
mixing read and write operations to test the dual-write and dual-read
functionality during migration.

Usage:
    python3 simulate_app_traffic.py [--duration SECONDS] [--delay SECONDS]

Options:
    --duration SECONDS  How long to run the simulation (default: 30)
    --delay SECONDS     Delay between operations (default: 0.5)
"""

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import uuid
import random
import time
import argparse
from datetime import datetime

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Simulate application traffic through ZDM Proxy'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=30,
        help='Duration to run simulation in seconds (default: 30)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='Delay between operations in seconds (default: 0.5)'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='zdm-proxy',
        help='Host to connect to (default: zdm-proxy)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=9042,
        help='Port to connect to (default: 9042)'
    )
    parser.add_argument(
        '--keyspace',
        type=str,
        default='training',
        help='Keyspace to use (default: training)'
    )
    parser.add_argument(
        '--read-ratio',
        type=float,
        default=0.75,
        help='Ratio of read operations (default: 0.75 = 75%% reads, 25%% writes)'
    )
    return parser.parse_args()

def create_session(host, port, keyspace):
    """Create a Cassandra session."""
    print(f"Connecting to {host}:{port}...")
    cluster = Cluster([host], port=port)
    session = cluster.connect(keyspace)
    print(f"Connected to keyspace '{keyspace}'")
    return cluster, session

def perform_read(session, iteration):
    """Perform a read operation."""
    try:
        # Mix of different read patterns
        read_type = random.choice(['limit', 'filter', 'specific'])
        
        if read_type == 'limit':
            result = session.execute("SELECT * FROM users LIMIT 10")
            count = len(list(result))
            print(f"[{iteration}] Read (LIMIT): Retrieved {count} users")
            
        elif read_type == 'filter':
            result = session.execute(
                "SELECT username, email FROM users WHERE status = 'active' LIMIT 5 ALLOW FILTERING"
            )
            count = len(list(result))
            print(f"[{iteration}] Read (FILTER): Retrieved {count} active users")
            
        else:  # specific
            result = session.execute("SELECT COUNT(*) FROM users")
            count = result.one()[0]
            print(f"[{iteration}] Read (COUNT): Total users = {count}")
            
        return True
    except Exception as e:
        print(f"[{iteration}] Read ERROR: {e}")
        return False

def perform_write(session, iteration):
    """Perform a write operation."""
    try:
        # Mix of different write patterns
        write_type = random.choice(['insert', 'update'])
        
        if write_type == 'insert':
            user_id = uuid.uuid4()
            username = f'app_user_{iteration}_{random.randint(1000, 9999)}'
            email = f'app_{iteration}@test.com'
            
            session.execute("""
                INSERT INTO users (user_id, username, email, status, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, username, email, 'active', datetime.now()))
            
            print(f"[{iteration}] Write (INSERT): Created user {username}")
            
        else:  # update
            # Get a random user to update
            result = session.execute("SELECT user_id FROM users LIMIT 1")
            row = result.one()
            if row:
                session.execute("""
                    UPDATE users SET status = %s WHERE user_id = %s
                """, ('active', row.user_id))
                print(f"[{iteration}] Write (UPDATE): Updated user status")
            else:
                print(f"[{iteration}] Write (UPDATE): No users to update")
                
        return True
    except Exception as e:
        print(f"[{iteration}] Write ERROR: {e}")
        return False

def run_simulation(args):
    """Run the traffic simulation."""
    cluster, session = create_session(args.host, args.port, args.keyspace)
    
    print()
    print("=" * 60)
    print("Simulating application traffic through ZDM Proxy")
    print("=" * 60)
    print(f"Duration: {args.duration} seconds")
    print(f"Delay between operations: {args.delay} seconds")
    print(f"Read ratio: {args.read_ratio:.0%}")
    print(f"Write ratio: {1-args.read_ratio:.0%}")
    print()
    print("Press Ctrl+C to stop early")
    print("=" * 60)
    print()
    
    iteration = 0
    read_count = 0
    write_count = 0
    read_errors = 0
    write_errors = 0
    start_time = time.time()
    
    try:
        while time.time() - start_time < args.duration:
            iteration += 1
            
            # Determine operation based on read ratio
            if random.random() < args.read_ratio:
                # Perform read
                if perform_read(session, iteration):
                    read_count += 1
                else:
                    read_errors += 1
            else:
                # Perform write
                if perform_write(session, iteration):
                    write_count += 1
                else:
                    write_errors += 1
            
            time.sleep(args.delay)
            
    except KeyboardInterrupt:
        print("\n\nStopping simulation (interrupted by user)...")
    
    elapsed = time.time() - start_time
    
    # Print summary
    print()
    print("=" * 60)
    print("Simulation Summary")
    print("=" * 60)
    print(f"Duration: {elapsed:.1f} seconds")
    print(f"Total operations: {iteration}")
    print(f"Operations/second: {iteration/elapsed:.2f}")
    print()
    print(f"Reads: {read_count} ({read_count/iteration*100:.1f}%)")
    print(f"Writes: {write_count} ({write_count/iteration*100:.1f}%)")
    print()
    if read_errors > 0 or write_errors > 0:
        print(f"Read errors: {read_errors}")
        print(f"Write errors: {write_errors}")
        print(f"Success rate: {(read_count+write_count)/iteration*100:.1f}%")
    else:
        print("✅ All operations completed successfully!")
    print("=" * 60)
    
    cluster.shutdown()

def main():
    """Main entry point."""
    args = parse_args()
    
    try:
        run_simulation(args)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())

# Made with Bob
