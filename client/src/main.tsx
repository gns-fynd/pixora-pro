import { StrictMode, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { ThemeProvider } from "@/components/theme-provider";
import { ChatProvider } from "@/context/ChatContext";
import { createBrowserRouter, RouterProvider, Outlet } from "react-router-dom";
import { Loader } from "@/components/ui/loader";
import "@fontsource/space-grotesk/400.css";
import "@fontsource/space-grotesk/500.css";
import "@fontsource/space-grotesk/600.css";
import "@fontsource/space-grotesk/700.css";
import "non.geist";
import "./index.css";
import App from "./app";
import { Auth, SignUp, ResetPassword } from "./pages/auth";
import EmailVerification from "./pages/auth/email-verification";
import AuthCallback from "./pages/auth/auth-callback";
import { ProtectedRoute } from "@/components/protected-route";
import useAuthStore from "@/store/use-auth-store";
import Landing from "@/pages/landing";
import SceneBreakdown from "@/pages/scene-breakdown";
import Generation from "@/pages/generation";
import Dashboard from "@/pages/dashboard";
import Profile from "@/pages/profile";
import LoaderDemo from "@/pages/loader-demo";
import { AppLayout } from "@/components/shared/AppLayout";

// Global flag to track if session has been checked
let sessionChecked = false;

// Root component to handle global session check
const Root = ({ children }: { children: React.ReactNode }) => {
  const { checkSession, isLoading } = useAuthStore();
  
  useEffect(() => {
    // Check session on app load - only once
    const initializeAuth = async () => {
      // Only check session if it hasn't been checked yet
      if (!sessionChecked) {
        try {
          console.log('Checking session on app initialization (Root component)');
          await checkSession();
          // Set the flag to true after checking
          sessionChecked = true;
        } catch (err) {
          console.error('Error checking session on app initialization:', err);
        }
      } else {
        console.debug('Session already checked, skipping initialization check');
      }
    };
    
    // Only run this once on mount
    initializeAuth();
    
    // No periodic checks - we'll rely on Supabase's built-in refresh mechanism
  }, [checkSession]);
  
  if (isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-gradient-to-br from-background to-background/80 dark:from-background dark:to-background/90">
        <div className="space-y-4 text-center">
          <Loader autoAnimate={true} message="Loading application..." />
        </div>
      </div>
    );
  }
  
  return <>{children}</>;
};


// Layout wrapper for authenticated routes
const AuthenticatedLayout = () => {
  return (
    <ProtectedRoute>
      <AppLayout>
        <Outlet />
      </AppLayout>
    </ProtectedRoute>
  );
};

const router = createBrowserRouter([
  {
    path: "/",
    element: <Landing />,
  },
  {
    path: "/auth",
    element: <Auth />,
  },
  {
    path: "/auth/callback",
    element: <AuthCallback />,
  },
  {
    path: "/auth/sign-up",
    element: <SignUp />,
  },
  {
    path: "/auth/reset-password",
    element: <ResetPassword />,
  },
  {
    path: "/auth/email-verification",
    element: <EmailVerification />,
  },
  {
    path: "/loader-demo",
    element: <LoaderDemo />,
  },
  {
    // Authenticated routes with shared layout
    element: <AuthenticatedLayout />,
    children: [
      {
        path: "/dashboard",
        element: <Dashboard />,
      },
      {
        path: "/profile",
        element: <Profile />,
      },
      {
        path: "/scene-breakdown",
        element: <SceneBreakdown />,
      },
      {
        path: "/generation",
        element: <Generation />,
      },
      {
        path: "/editor",
        element: <App />,
      },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <ChatProvider>
        <Root>
          <RouterProvider router={router} />
        </Root>
      </ChatProvider>
    </ThemeProvider>
  </StrictMode>,
);
