# Database Migrations

This directory contains database migrations for the Pixora AI application. Migrations are used to make changes to the database schema or data in a controlled and repeatable way.

## Migration Files

Migration files are SQL scripts that are applied to the database in order. They are named with a timestamp prefix to ensure they are applied in the correct order.

For example:
- `20250421_001_fix_user_trigger.sql` - Fixes the user trigger function to handle missing metadata

## Applying Migrations

To apply a migration, use the `apply_migration.py` script:

```bash
# Make sure you have the required dependencies
pip install httpx python-dotenv

# Set the Supabase credentials in your .env file
# SUPABASE_URL=your-supabase-url
# SUPABASE_KEY=your-supabase-key

# Apply a migration
python apply_migration.py 20250421_001_fix_user_trigger.sql
```

## Creating New Migrations

To create a new migration:

1. Create a new SQL file in this directory with a name following the pattern `YYYYMMDD_NNN_description.sql`
2. Write your SQL statements in the file
3. Apply the migration using the `apply_migration.py` script

## Best Practices

- Always include comments in your migration files explaining what they do
- Make migrations idempotent when possible (they can be run multiple times without causing errors)
- Include both "up" and "down" migrations when possible (to apply and revert changes)
- Test migrations in a development environment before applying them to production
