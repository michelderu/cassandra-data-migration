-- Create training keyspace and tables for migration lab

-- Create keyspace with NetworkTopologyStrategy
CREATE KEYSPACE IF NOT EXISTS training
WITH replication = {
  'class': 'NetworkTopologyStrategy',
  'dc1': 1
};

-- Users table
CREATE TABLE IF NOT EXISTS training.users (
  user_id uuid PRIMARY KEY,
  username text,
  email text,
  first_name text,
  last_name text,
  created_at timestamp,
  updated_at timestamp,
  status text,
  preferences map<text, text>
);

-- Orders table
CREATE TABLE IF NOT EXISTS training.orders (
  order_id uuid PRIMARY KEY,
  user_id uuid,
  order_date timestamp,
  total_amount decimal,
  status text,
  items list<text>,
  shipping_address text
);

-- Products table
CREATE TABLE IF NOT EXISTS training.products (
  product_id uuid PRIMARY KEY,
  name text,
  description text,
  price decimal,
  category text,
  stock_quantity int,
  created_at timestamp
);

-- User activity table (for time-series data)
CREATE TABLE IF NOT EXISTS training.user_activity (
  user_id uuid,
  activity_date date,
  activity_time timestamp,
  activity_type text,
  details text,
  PRIMARY KEY ((user_id, activity_date), activity_time)
) WITH CLUSTERING ORDER BY (activity_time DESC);

-- Create secondary indexes
CREATE INDEX IF NOT EXISTS users_email_idx ON training.users (email);
CREATE INDEX IF NOT EXISTS users_status_idx ON training.users (status);
CREATE INDEX IF NOT EXISTS orders_user_idx ON training.orders (user_id);
CREATE INDEX IF NOT EXISTS products_category_idx ON training.products (category);
