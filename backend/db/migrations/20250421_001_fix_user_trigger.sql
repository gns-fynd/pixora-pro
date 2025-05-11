-- Migration to fix the handle_new_user trigger function
-- This makes the function more robust by handling missing metadata and adding error logging

-- Drop the existing trigger first
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Replace the function with a more robust version
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (id, email, username, full_name, credits)
    VALUES (
        NEW.id,
        COALESCE(NEW.email, ''),
        COALESCE(NEW.raw_user_meta_data->>'username', split_part(COALESCE(NEW.email, ''), '@', 1)),
        COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name', ''),
        10
    );
    RETURN NEW;
EXCEPTION
    WHEN others THEN
        -- Log the error (this will appear in Supabase logs)
        RAISE LOG 'Error in handle_new_user trigger: %', SQLERRM;
        -- Still return NEW to allow the user creation to proceed
        RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Re-create the trigger
CREATE TRIGGER on_auth_user_created
AFTER INSERT ON auth.users
FOR EACH ROW
EXECUTE FUNCTION handle_new_user();

-- Temporarily disable RLS on profiles table to test if that's the issue
-- Comment this out after testing if it fixes the issue
-- ALTER TABLE profiles DISABLE ROW LEVEL SECURITY;

-- Add a comment explaining what this migration does
COMMENT ON FUNCTION handle_new_user() IS 'Handles new user creation by adding a profile record. More robust version that handles missing metadata and logs errors.';
