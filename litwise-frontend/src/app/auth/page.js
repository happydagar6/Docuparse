import LoginForm from '@/components/auth/LoginForm'

export const metadata = {
  title: 'Login | LitWise',
  description: 'Sign in to your LitWise account',
}

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-linear-to-br from-blue-50 via-white to-cyan-50 p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold bg-linear-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent mb-2">
            LitWise
          </h1>
          <p className="text-muted-foreground">
            Your AI-powered research assistant
          </p>
        </div>
        <LoginForm />
      </div>
    </div>
  )
}