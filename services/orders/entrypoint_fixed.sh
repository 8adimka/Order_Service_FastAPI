#!/bin/bash
set -e

echo "Waiting for database..."
sleep 5

echo "Creating database tables..."
python3 -c "
import psycopg2
import os
import sys

db_url = os.environ.get('POSTGRES_ORDERS_URL', 'postgresql://postgres:postgres@postgres_orders:5432/ordersdb')

try:
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()
    
    cursor.execute('''
        DO \$\$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_status') THEN
                CREATE TYPE order_status AS ENUM ('PENDING', 'PAID', 'SHIPPED', 'CANCELED');
            END IF;
        END
        \$\$;
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id INTEGER NOT NULL,
            items JSONB NOT NULL,
            total_price FLOAT NOT NULL,
            status order_status NOT NULL DEFAULT 'PENDING',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS ix_orders_user_id ON orders(user_id)
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alembic_version (
            version_num VARCHAR(50) PRIMARY KEY
        )
    ''')
    
    cursor.execute('''
        INSERT INTO alembic_version (version_num) 
        VALUES ('0001_create_orders_fixed')
        ON CONFLICT (version_num) DO NOTHING
    ''')
    
    cursor.close()
    conn.close()
    print('Database tables created')
    
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
"

echo "Starting FastAPI..."
cd /app
exec uvicorn app.main:app --host 0.0.0.0 --port 8000