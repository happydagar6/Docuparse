'use client'

import { useAuth } from '@/contexts/AuthContext'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { User, Mail, Calendar, Settings, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { useQuery } from '@tanstack/react-query'
import { getPapers } from '@/lib/api'
import { getLiteratureReviews } from '@/lib/literature-review-api'

export default function ProfilePage() {
  const { user } = useAuth()

  // Fetch user's papers
  const { data: papers = [], isLoading: papersLoading } = useQuery({
    queryKey: ['papers'],
    queryFn: getPapers,
    enabled: !!user,
  })

  // Fetch user's literature reviews
  const { data: reviews = [], isLoading: reviewsLoading } = useQuery({
    queryKey: ['literature-reviews'],
    queryFn: getLiteratureReviews,
    enabled: !!user,
  })

  // Calculate total chat sessions across all papers
  const totalChats = 0 // We'd need to aggregate from all papers' chat sessions

  // Get initials from email
  const getInitials = (email) => {
    if (!email) return 'U'
    const parts = email.split('@')[0].split('.')
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
    }
    return email.substring(0, 2).toUpperCase()
  }

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Profile</h1>
        <p className="text-gray-600 mt-2">View and manage your profile information</p>
      </div>

      {/* Profile Card */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Avatar className="h-20 w-20">
                <AvatarFallback className="text-2xl bg-blue-100 text-blue-600">
                  {getInitials(user?.email)}
                </AvatarFallback>
              </Avatar>
              <div>
                <CardTitle className="text-2xl">{user?.email?.split('@')[0] || 'User'}</CardTitle>
                <CardDescription className="text-base mt-1">
                  {user?.email}
                </CardDescription>
              </div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Account Details */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Account Details</CardTitle>
          <CardDescription>Your account information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-start gap-3 pb-4 border-b">
            <User className="h-5 w-5 text-gray-500 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-700">User ID</p>
              <p className="text-sm text-gray-600 mt-1 font-mono break-all">
                {user?.id || 'N/A'}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 pb-4 border-b">
            <Mail className="h-5 w-5 text-gray-500 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-700">Email Address</p>
              <p className="text-sm text-gray-600 mt-1">
                {user?.email || 'N/A'}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <Calendar className="h-5 w-5 text-gray-500 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-700">Member Since</p>
              <p className="text-sm text-gray-600 mt-1">
                {formatDate(user?.created_at)}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Card */}
      <Card>
        <CardHeader>
          <CardTitle>Activity Stats</CardTitle>
          <CardDescription>Your usage statistics</CardDescription>
        </CardHeader>
        <CardContent>
          {papersLoading || reviewsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 bg-blue-50 rounded-lg">
                <p className="text-2xl font-bold text-blue-600">{papers.length}</p>
                <p className="text-sm text-gray-600 mt-1">Papers Uploaded</p>
              </div>
              <div className="p-4 bg-green-50 rounded-lg">
                <p className="text-2xl font-bold text-green-600">{totalChats}</p>
                <p className="text-sm text-gray-600 mt-1">Chat Sessions</p>
              </div>
              <div className="p-4 bg-purple-50 rounded-lg">
                <p className="text-2xl font-bold text-purple-600">{reviews.length}</p>
                <p className="text-sm text-gray-600 mt-1">Literature Reviews</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
