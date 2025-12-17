'use client'

import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Mail, Lock, AlertCircle, User, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { toast } from 'sonner'

export default function SignupForm() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  
  const { signUp, signInWithGoogle } = useAuth()
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
      await signUp(email, password, {
        full_name: fullName,
      })
      
      setSuccess(true)
      toast.success('Account created!', {
        description: 'Please check your email to verify your account.',
      })
      
      // Redirect to login after 2 seconds
      setTimeout(() => {
        router.push('/auth')
      }, 2000)
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

  const handleGoogleSignIn = async () => {
    setError('')
    setLoading(true)
    try {
      await signInWithGoogle()
    } catch (err) {
      console.error('Google sign-in error:', err)
      setError(err.message || 'Failed to sign in with Google.')
      toast.error('Google sign-in failed', {
        description: err.message,
      })
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
          Start your research journey with LitWise
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
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
                className="pl-11 h-12 border-gray-200 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200 transition-all"
                minLength={6}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">Must be at least 6 characters</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmPassword" className="text-sm font-semibold text-gray-700">Confirm Password</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-3.5 h-5 w-5 text-gray-400" />
              <Input
                id="confirmPassword"
                type="password"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={loading}
                className="pl-11 h-12 border-gray-200 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200 transition-all"
                minLength={6}
              />
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

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-gray-200" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="bg-white px-4 text-gray-500 font-medium">
              Or continue with
            </span>
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          onClick={handleGoogleSignIn}
          disabled={loading}
          className="w-full h-12 border-2 border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all duration-200 font-semibold"
        >
          <svg className="mr-3 h-5 w-5" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          Continue with Google
        </Button>
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