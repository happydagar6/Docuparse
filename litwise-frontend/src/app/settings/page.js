'use client'

import { useAuth } from '@/contexts/AuthContext'
import { PageLayout } from '@/components/layout/Layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { User, Mail, LogOut, Calendar, Settings as SettingsIcon } from 'lucide-react'
import { useRouter } from 'next/navigation'


export default function SettingsPage() {
  const { user, signOut } = useAuth()
  const router = useRouter()

  // Helper functions
  const getInitials = (email) => {
    if (!email) return 'U'
    const parts = email.split('@')[0].split('.')
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
    }
    return email.substring(0, 2).toUpperCase()
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  const handleSignOut = async () => {
    try {
      await signOut()
      router.push('/auth')
    } catch (error) {
      console.error('Sign out error:', error)
    }
  }

  return (
    <PageLayout>
      {/* Enhanced Header Section */}
      <div className="mb-8">
        <div className="relative bg-linear-to-br from-indigo-50 via-purple-50 to-pink-50 rounded-2xl p-8 md:p-10 border border-indigo-100/50 overflow-hidden">
          {/* Glassmorphic background elements */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-linear-to-br from-indigo-200 to-purple-200 rounded-full blur-3xl opacity-20 -z-10"></div>
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-linear-to-tr from-purple-200 to-pink-200 rounded-full blur-3xl opacity-15 -z-10"></div>
          
          <div className="relative z-10 flex items-start gap-6">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-white/60 backdrop-blur-md border border-white/40 shadow-lg">
              <SettingsIcon className="h-7 w-7 text-indigo-600" />
            </div>
            <div className="flex-1">
              <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">Settings & Profile</h1>
              <p className="text-gray-700 leading-relaxed">Manage your account, preferences, and view your activity overview.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto space-y-6">
        {/* User Profile Card */}
        <Card className="border-0 shadow-lg bg-white/60 backdrop-blur-sm">
          <CardHeader className="bg-linear-to-br from-white to-gray-50/50 border-b">
            <div className="flex items-center gap-4">
              <Avatar className="h-20 w-20">
                <AvatarFallback className="text-2xl bg-indigo-100 text-indigo-600 font-bold">
                  {getInitials(user?.email)}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1">
                <CardTitle className="text-2xl">{user?.email?.split('@')[0] || 'User'}</CardTitle>
                <p className="text-sm text-gray-600 mt-1">
                  {user?.email}
                </p>
              </div>
            </div>
          </CardHeader>
        </Card>

        {/* Account Information */}
        <Card className="border-0 shadow-lg">
          <CardHeader className="bg-linear-to-br from-blue-50/50 to-transparent">
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5 text-blue-600" />
              Account Information
            </CardTitle>
            <CardDescription>Your account details and profile information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pt-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div>
                <Label htmlFor="email" className="flex items-center gap-2 mb-2 font-semibold">
                  <Mail className="h-4 w-4 text-blue-600" />
                  Email Address
                </Label>
                <Input
                  id="email"
                  type="email"
                  value={user?.email || ''}
                  disabled
                  className="bg-gray-50 border-gray-200"
                />
              </div>

              <div>
                <Label htmlFor="member-since" className="flex items-center gap-2 mb-2 font-semibold">
                  <Calendar className="h-4 w-4 text-green-600" />
                  Member Since
                </Label>
                <Input
                  id="member-since"
                  type="text"
                  value={formatDate(user?.created_at)}
                  disabled
                  className="bg-gray-50 border-gray-200"
                />
              </div>
            </div>

            <Separator />

            <div>
              <Label htmlFor="user-id" className="flex items-center gap-2 mb-2 font-semibold">
                <SettingsIcon className="h-4 w-4 text-purple-600" />
                User ID
              </Label>
              <Input
                id="user-id"
                type="text"
                value={user?.id || ''}
                disabled
                className="bg-gray-50 border-gray-200 font-mono text-xs"
              />
              <p className="text-xs text-gray-500 mt-2">This unique identifier is used for account management</p>
            </div>
          </CardContent>
        </Card>

        {/* Sign Out */}
        <Card className="border-red-200 border-2 shadow-lg">
          <CardHeader className="bg-linear-to-br from-red-50/50 to-transparent">
            <CardTitle className="flex items-center gap-2 text-red-600">
              <LogOut className="h-5 w-5" />
              Sign Out
            </CardTitle>
            <CardDescription>
              Sign out of your account on this device
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <Button
              onClick={handleSignOut}
              className="w-full sm:w-auto bg-red-600 hover:bg-red-700 text-white shadow-md hover:shadow-lg transition-all"
            >
              <LogOut className="h-4 w-4 mr-2" />
              Sign Out
            </Button>
            <p className="text-sm text-gray-500 mt-3">
              You will be signed out from this device. You can sign back in anytime.
            </p>
          </CardContent>
        </Card>
      </div>
    </PageLayout>
  )
}
