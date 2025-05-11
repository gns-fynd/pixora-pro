# SSO Authentication Fix

This document explains the changes made to fix the SSO (Single Sign-On) authentication issue in the Pixora AI platform.

## Problem

Users could sign up using SSO (Google, Apple, etc.) and appear in the Supabase auth users, but they were not properly logged into the platform. This was because the token exchange between Supabase and the backend was not happening correctly.

## Solution

The following changes have been made to fix the issue:

1. **Enhanced AuthCallback Component**: Created a new dedicated component (`src/pages/auth/auth-callback.tsx`) that properly handles the token exchange with the backend after SSO authentication.

2. **Updated SSO Methods**: Modified the `signInWithGoogle` and `signInWithApple` methods in `src/services/backend-auth-service.ts` to set a flag indicating that SSO is being used.

3. **Updated Main Router**: Updated `src/main.tsx` to use the new AuthCallback component.

4. **Environment Configuration**: Created example environment files with the necessary configuration for SSO authentication.

## How to Implement the Fix

1. **Update Environment Variables**:

   Copy the `.env.local.example` file to `.env.local` and update the values:

   ```
   # Supabase Configuration
   VITE_SUPABASE_URL=your-supabase-project-url
   VITE_SUPABASE_ANON_KEY=your-supabase-anon-key

   # API Configuration
   VITE_API_URL=http://localhost:8000

   # Auth Configuration
   VITE_USE_DIRECT_SUPABASE_AUTH=false
   ```

   Make sure `VITE_USE_DIRECT_SUPABASE_AUTH` is set to `false` to enable token exchange with the backend.

2. **Update Backend Environment Variables**:

   Copy the `backend/.env.local.example` file to `backend/.env.local` and update the values:

   ```
   # Security
   SUPABASE_URL=your-supabase-project-url
   SUPABASE_KEY=your-supabase-anon-key
   SUPABASE_SERVICE_KEY=your-supabase-service-role-key
   SUPABASE_JWT_SECRET=your-supabase-jwt-secret
   ```

   The `SUPABASE_JWT_SECRET` is particularly important for token verification. You can find it in your Supabase project settings under API > JWT Settings > JWT Secret.

3. **Restart Both Frontend and Backend**:

   ```bash
   # Restart the frontend
   npm run dev

   # Restart the backend
   cd backend
   python run.py
   ```

## How It Works

1. When a user initiates SSO login (Google, Apple, etc.), a flag is set in localStorage to indicate that SSO is being used.
2. After successful authentication with Supabase, the user is redirected to the `/auth/callback` route.
3. The new AuthCallback component:
   - Checks if SSO was used
   - Gets the Supabase session
   - Exchanges the Supabase token for a backend token
   - Sets the backend token in the API client
   - Calls `checkSession()` to get the user profile
   - Redirects to the home page

4. The backend's `/auth/token` endpoint:
   - Verifies the Supabase token
   - Creates a user profile if it doesn't exist
   - Returns a backend token

## Debugging

If you encounter issues with SSO authentication, check the browser console for detailed logs. The updated code includes extensive logging to help diagnose problems:

- "Auth callback triggered"
- "URL params" and "Hash params"
- "Is SSO authentication"
- "Session data"
- "Exchanging token with backend"
- "Token exchange successful" or "Token exchange error"

## Additional Notes

- The token exchange happens in the AuthCallback component, which is a critical part of the SSO flow.
- If the token exchange fails, the component will still try to continue with the session check, as the user might still be authenticated with Supabase.
- The backend creates a user profile if it doesn't exist, which is important for SSO users who don't go through the regular sign-up process.
