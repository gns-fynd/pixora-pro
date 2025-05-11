#!/bin/bash
# Script to apply the fix for the user trigger function

# Change to the migrations directory
cd "$(dirname "$0")/migrations"

# Install required dependencies
pip install httpx python-dotenv

# Apply the migration
python apply_migration.py 20250421_001_fix_user_trigger.sql

echo "Migration applied successfully. Please try the SSO authentication again."
