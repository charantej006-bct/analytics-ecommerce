import os
import sys
import duckdb

# Resolve absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "saas_warehouse.duckdb")
RAW_DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "raw_data"))

def load_raw_tables():
    print(f"[1/4] Connecting to DuckDB at: {DB_PATH}")
    conn = duckdb.connect(DB_PATH)
    
    print("[2/4] Ensuring 'raw' schema exists...")
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw;")
    
    tables = [
        "customers",
        "plans",
        "subscriptions",
        "subscription_events",
        "payments"
    ]
    
    print(f"[3/4] Searching for CSVs in: {RAW_DATA_DIR}")
    for table in tables:
        csv_file = os.path.join(RAW_DATA_DIR, f"{table}.csv")
        # Normalize slashes for DuckDB SQL compatibility on Windows
        sql_csv_path = csv_file.replace("\\", "/")
        
        if os.path.exists(csv_file):
            conn.execute(f"""
                CREATE OR REPLACE TABLE raw.{table} AS 
                SELECT * FROM read_csv_auto('{sql_csv_path}', all_varchar=true);
            """)
            count = conn.execute(f"SELECT COUNT(*) FROM raw.{table}").fetchone()[0]
            print(f"  -> Loaded raw.{table}: {count:,} rows")
        else:
            print(f"  -> [WARNING] Skipping raw.{table}: file not found at {csv_file}")
            
    conn.close()
    print("[4/4] Ingestion complete.")

if __name__ == "__main__":
    load_raw_tables()