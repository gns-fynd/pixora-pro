"""
Script to apply a migration to the Supabase database
"""
import os
import sys
import argparse
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def apply_migration(migration_file: str):
    """
    Apply a migration to the Supabase database
    
    Args:
        migration_file: Path to the migration file
    """
    # Get Supabase credentials from environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set")
        sys.exit(1)
    
    # Read the migration file
    try:
        with open(migration_file, "r") as f:
            sql = f.read()
    except Exception as e:
        print(f"Error reading migration file: {e}")
        sys.exit(1)
    
    # Apply the migration
    print(f"Applying migration: {migration_file}")
    
    try:
        # Use the Supabase REST API to execute the SQL
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "params=single-object",
        }
        
        response = httpx.post(
            f"{supabase_url}/rest/v1/rpc/exec_sql",
            headers=headers,
            json={"query": sql},
            timeout=30.0,
        )
        
        if response.status_code != 200:
            print(f"Error applying migration: {response.text}")
            sys.exit(1)
        
        print("Migration applied successfully")
    except Exception as e:
        print(f"Error applying migration: {e}")
        sys.exit(1)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Apply a migration to the Supabase database")
    parser.add_argument("migration_file", help="Path to the migration file")
    args = parser.parse_args()
    
    apply_migration(args.migration_file)

if __name__ == "__main__":
    main()
