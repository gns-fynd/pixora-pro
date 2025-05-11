import { ReactNode, useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import useAuthStore from '@/store/use-auth-store';
import { apiClient } from '@/services/api-client';

interface AdminProtectedRouteProps {
  children: ReactNode;
}

/**
 * A route component that only allows access to admin users.
 * Redirects to the dashboard if the user is not an admin.
 */
export function AdminProtectedRoute({ children }: AdminProtectedRouteProps) {
  const { isAuthenticated, user } = useAuthStore();
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkAdminStatus = async () => {
      if (!isAuthenticated) {
        setIsAdmin(false);
        setIsLoading(false);
        return;
      }

      try {
        // Try to access the admin API to check if the user is an admin
        await apiClient.get('/admin/users');
        setIsAdmin(true);
      } catch (error) {
        console.error('Error checking admin status:', error);
        setIsAdmin(false);
      } finally {
        setIsLoading(false);
      }
    };

    checkAdminStatus();
  }, [isAuthenticated, user]);

  // Show loading state while checking admin status
  if (isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  // Redirect to dashboard if not authenticated or not an admin
  if (!isAuthenticated || !isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  // Render children if user is an admin
  return <>{children}</>;
}
