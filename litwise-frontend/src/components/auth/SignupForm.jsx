'use client'

import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Mail, Lock, AlertCircle, User, Sparkles, Eye, EyeOff } from 'lucide-react'
import Link from 'next/link'
import { toast } from 'sonner'

export default function SignupForm() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  
  const { signUp } = useAuth()
  const router = useRouter()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess(false)

    // Validation
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }

    setLoading(true)

    try {
      const { data, error } = await signUp(email, password, {
        full_name: fullName,
      })
      
      if (error) throw error
      
      // Check if user is already confirmed (email confirmation disabled)
      if (data?.user?.confirmed_at || data?.user?.email_confirmed_at) {
        // Email verification is disabled - auto confirm and redirect
        toast.success('Account created!', {
          description: 'Welcome to DocuParse! Redirecting...',
        })
        setTimeout(() => {
          router.push('/')
        }, 1500)
      } else {
        // Email verification is enabled - show check email screen
        setSuccess(true)
        toast.success('Account created!', {
          description: 'Please check your email to verify your account.',
        })
        
        // Redirect to login after 2 seconds if they close the modal
        setTimeout(() => {
          router.push('/auth')
        }, 2000)
      }
    } catch (err) {
      console.error('Signup error:', err)
      setError(err.message || 'Failed to create account. Please try again.')
      toast.error('Signup failed', {
        description: err.message || 'Please try again.',
      })
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <Card className="w-full max-w-md mx-auto shadow-2xl border-0 bg-white/95 backdrop-blur-sm">
        <CardHeader className="space-y-3 pb-6">
          <div className="flex justify-center mb-2">
            <div className="w-16 h-16 bg-linear-to-br from-green-500 to-emerald-600 rounded-2xl flex items-center justify-center shadow-lg">
              <Mail className="h-8 w-8 text-white" />
            </div>
          </div>
          <CardTitle className="text-3xl font-bold text-center bg-linear-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
            Check Your Email
          </CardTitle>
          <CardDescription className="text-center text-base text-gray-600">
            We&apos;ve sent you a verification link
          </CardDescription>
        </CardHeader>
        <CardContent className="px-8">
          <Alert className="border-green-200 bg-green-50">
            <Mail className="h-5 w-5 text-green-600" />
            <AlertDescription className="text-gray-700">
              Please check your email inbox and click the verification link to activate your account.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="w-full max-w-md mx-auto shadow-2xl border-0 bg-white/95 backdrop-blur-sm">
      <CardHeader className="space-y-3 pb-6">
        <div className="flex justify-center mb-2">
          <div className="w-16 h-16 bg-linear-to-br from-cyan-600 to-blue-600 rounded-2xl flex items-center justify-center shadow-lg">
            <Sparkles className="h-8 w-8 text-white" />
          </div>
        </div>
        <CardTitle className="text-3xl font-bold text-center bg-linear-to-r from-cyan-600 to-blue-600 bg-clip-text text-transparent">
          Create Account
        </CardTitle>
        <CardDescription className="text-center text-base text-gray-600">
          Start your research journey with DocuParse
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6 px-8">
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="fullName" className="text-sm font-semibold text-gray-700">Full Name</Label>
            <div className="relative">
              <User className="absolute left-3 top-3.5 h-5 w-5 text-gray-400" />
              <Input
                id="fullName"
                type="text"
                placeholder="John Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                disabled={loading}
                className="pl-11 h-12 border-gray-200 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200 transition-all"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="email" className="text-sm font-semibold text-gray-700">Email Address</Label>
            <div className="relative">
              <Mail className="absolute left-3 top-3.5 h-5 w-5 text-gray-400" />
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
                className="pl-11 h-12 border-gray-200 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200 transition-all"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="text-sm font-semibold text-gray-700">Password</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-3.5 h-5 w-5 text-gray-400" />
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
                className="pl-11 pr-10 h-12 border-gray-200 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200 transition-all"
                minLength={6}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-3.5 text-gray-400 hover:text-gray-600 transition-colors"
                tabIndex="-1"
              >
                {showPassword ? (
                  <EyeOff className="h-5 w-5" />
                ) : (
                  <Eye className="h-5 w-5" />
                )}
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-1">Must be at least 6 characters</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmPassword" className="text-sm font-semibold text-gray-700">Confirm Password</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-3.5 h-5 w-5 text-gray-400" />
              <Input
                id="confirmPassword"
                type={showConfirmPassword ? "text" : "password"}
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={loading}
                className="pl-11 pr-10 h-12 border-gray-200 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200 transition-all"
                minLength={6}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-3.5 text-gray-400 hover:text-gray-600 transition-colors"
                tabIndex="-1"
              >
                {showConfirmPassword ? (
                  <EyeOff className="h-5 w-5" />
                ) : (
                  <Eye className="h-5 w-5" />
                )}
              </button>
            </div>
          </div>

          <Button 
            type="submit" 
            className="w-full h-12 bg-linear-to-r from-cyan-600 to-blue-600 hover:from-cyan-700 hover:to-blue-700 text-white font-semibold shadow-lg hover:shadow-xl transition-all duration-200" 
            disabled={loading}
          >
            {loading && <Loader2 className="mr-2 h-5 w-5 animate-spin" />}
            Create Account
          </Button>
        </form>
      </CardContent>
      <CardFooter className="flex flex-col space-y-4 px-8 pb-8">
        <div className="text-center text-sm text-gray-600">
          Already have an account?{' '}
          <Link href="/auth" className="text-cyan-600 hover:text-cyan-700 font-semibold hover:underline transition-colors">
            Sign in
          </Link>
        </div>
      </CardFooter>
    </Card>
  )
}