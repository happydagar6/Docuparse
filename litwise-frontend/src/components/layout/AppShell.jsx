"use client";

import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { RootLayout } from "./Layout";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Loader2 } from "lucide-react";
import { Suspense } from "react";

// Routes that should NOT have the app shell (navigation, sidebar, etc.)
const authRoutes = [
  "/auth",
  "/auth/signup",
  "/auth/callback",
  "/auth/reset-password",
];

// Loading fallback for content while shell loads
function ShellLoadingFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-linear-to-br from-blue-50 via-white to-cyan-50">
      <div className="text-center">
        <div className="mb-6">
          <h1 className="text-4xl font-bold bg-linear-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">
            DocuParse
          </h1>
        </div>
        <Loader2 className="h-10 w-10 animate-spin text-blue-600 mx-auto mb-4" />
        <p className="text-gray-500">Loading your workspace...</p>
      </div>
    </div>
  );
}

export function AppShell({ children }) {
  const { user, loading } = useAuth();
  const pathname = usePathname();

  const isAuthRoute = authRoutes.some((route) => pathname?.startsWith(route));

  // Show loading screen while checking auth
  if (loading) {
    return <ShellLoadingFallback />;
  }

  // For auth routes (login, signup, etc.) - render without app shell
  if (isAuthRoute) {
    return <ProtectedRoute>{children}</ProtectedRoute>;
  }

  // For protected app routes - render with full app shell and suspense boundary
  return (
    <ProtectedRoute>
      <Suspense fallback={null}>
        <RootLayout>{children}</RootLayout>
      </Suspense>
    </ProtectedRoute>
  );
}
