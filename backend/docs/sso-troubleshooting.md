# SSO Authentication Troubleshooting

This document provides guidance on troubleshooting SSO authentication issues with the Pixora AI application.

## Common Issues

### "Database error saving new user" Error

If you encounter the error "Database error saving new user" when trying to authenticate with Google or other SSO providers, it's likely due to one of the following issues:

1. **Missing or invalid metadata from the OAuth provider**
   - The OAuth provider (e.g., Google) might not be providing all the required metadata that the trigger function expects
   - The trigger function might not be handling missing metadata properly

2. **Row Level Security (RLS) policies**
   - RLS policies might be preventing the insertion of new user records

3. **Database constraints**
   - There might be constraints in the database that are being violated when creating a new user

## Solution

We've created a migration that fixes the most common issues:

1. **Improved trigger function**
   - The migration updates the `handle_new_user` trigger function to handle missing metadata
   - It adds better error handling to log errors in the Supabase logs
   - It ensures the user creation process continues even if there's an error creating the profile

2. **Optional RLS disabling**
   - The migration includes a commented-out line to disable RLS on the profiles table
   - This can be uncommented if RLS is determined to be the issue

## Applying the Fix

To apply the fix:

1. Make sure you have the Supabase credentials in your `.env` file:
   ```
   SUPABASE_URL=your-supabase-url
   SUPABASE_KEY=your-supabase-anon-key
   ```

2. Run the fix script:
   ```bash
   cd backend/db
   ./apply_fix.sh
   ```

3. Try the SSO authentication again

## Debugging

If the issue persists after applying the fix:

1. Check the Supabase logs for any errors
2. Try uncommenting the line in the migration file that disables RLS on the profiles table
3. Check if there are any unique constraints being violated (e.g., duplicate email)

## Additional Resources

- [Supabase Authentication Documentation](https://supabase.com/docs/guides/auth)
- [Supabase Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)
- [Supabase Triggers](https://supabase.com/docs/guides/database/triggers)
