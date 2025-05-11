import { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import useAuthStore from '@/store/use-auth-store';

interface ProtectedRouteProps {
  children: ReactNode;
}

/**
 * A component that protects routes that require authentication.
 * If the user is not authenticated, they will be redirected to the login page.
 */
export const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const { isAuthenticated, isLoading } = useAuthStore();
  const location = useLocation();
  
  // We don't need to check the session here since it's already checked in the Root component
  // We also don't need to set up auth state change listeners here, as they're handled in the auth service

  // Show a loading indicator while checking authentication
  if (isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-gradient-to-br from-background to-background/80 dark:from-background dark:to-background/90">
        <div className="space-y-4 text-center">
          <div className="h-12 w-12 rounded-full border-4 border-primary border-t-transparent animate-spin mx-auto"></div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  // If the user is not authenticated, redirect to the login page
  if (!isAuthenticated) {
    console.log('User not authenticated, redirecting to login');
    return <Navigate to="/auth" state={{ from: location }} replace />;
  }

  // If the user is authenticated, render the protected content
  console.log('User authenticated, rendering protected content');
  return <>{children}</>;
};
