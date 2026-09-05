"""
Applies the 20260907_token_usage_traceability.sql migration to PostgreSQL.
"""
import os
import sys

# Ensure server root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.dbConnection import get_connection

def apply_migration():
    migration_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "supabase", "migrations", "20260907_token_usage_traceability.sql"
    )
    
    print(f"Reading migration file: {migration_path}")
    with open(migration_path, "r") as f:
        sql = f.read()
        
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print("Successfully applied migration 20260907_token_usage_traceability.sql!")

if __name__ == "__main__":
    apply_migration()
