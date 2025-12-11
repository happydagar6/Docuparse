'use client'

import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { Loader2 } from 'lucide-react'

// Routes that don't require authentication
const publicRoutes = ['/auth', '/auth/signup', '/auth/callback', '/auth/reset-password']

export function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  const isPublicRoute = publicRoutes.some(route => pathname?.startsWith(route))

  useEffect(() => {
    if (!loading) {
      // If not authenticated and trying to access protected route
      if (!user && !isPublicRoute) {
        router.push('/auth')
      }
      // If authenticated and trying to access auth pages, redirect to home
      if (user && isPublicRoute && pathname !== '/auth/callback') {
        router.push('/')
      }
    }
  }, [user, loading, isPublicRoute, pathname, router])

  // Show loading spinner while checking auth
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-linear-to-br from-blue-50 via-white to-cyan-50">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600 font-medium">Loading...</p>
        </div>
      </div>
    )
  }

  // If on public route and not authenticated, show the page
  if (isPublicRoute && !user) {
    return <>{children}</>
  }

  // If authenticated, show the page
  if (user) {
    return <>{children}</>
  }

  // Otherwise show loading (redirect is happening)
  return (
    <div className="min-h-screen flex items-center justify-center bg-linear-to-br from-blue-50 via-white to-cyan-50">
      <div className="text-center">
        <Loader2 className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
        <p className="text-gray-600 font-medium">Redirecting...</p>
      </div>
    </div>
  )
}
