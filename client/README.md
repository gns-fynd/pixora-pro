# Pixora AI - Frontend

This is the frontend part of the Pixora AI application, built with React, TypeScript, and Vite.

## Development

To start the development server:

```bash
npm install
npm run dev
```

## Building for Production

To build for production:

```bash
npm run build:prod
```

This will create a production build in the `dist` directory.

## Deployment

The frontend is configured to be deployed to Vercel. The deployment configuration is in the root `vercel.json` file.

### Environment Variables

The following environment variables are used:

- `VITE_SUPABASE_URL`: The URL of your Supabase instance
- `VITE_SUPABASE_ANON_KEY`: The anonymous key for your Supabase instance
- `VITE_API_URL`: The URL of the backend API (defaults to `https://pixora-ai-backend.onrender.com/api/v1` in production)
- `VITE_USE_DIRECT_SUPABASE_AUTH`: Whether to use direct Supabase authentication (defaults to `false`)

## Project Structure

- `src/components`: Reusable UI components
- `src/context`: React context providers
- `src/hooks`: Custom React hooks
- `src/interfaces`: TypeScript interfaces
- `src/pages`: Application pages
- `src/services`: API services
- `src/store`: State management (Zustand)
- `src/utils`: Utility functions
