'use client'

import LoginForm from '@/components/auth/LoginForm'
import { BookOpen, Brain, Search, Sparkles } from 'lucide-react'

export default function LoginPage() {
  return (
    <div className="min-h-screen flex">
      {/* Left Side - Branding & Features */}
      <div className="hidden lg:flex lg:w-1/2 bg-linear-to-br from-blue-600 via-blue-700 to-cyan-600 p-12 flex-col justify-between">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">LitWise</h1>
          <p className="text-blue-100 text-lg">AI-Powered Research Companion</p>
        </div>
        
        <div className="space-y-8">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-white/10 rounded-xl">
              <Brain className="h-6 w-6 text-white" />
            </div>
            <div>
              <h3 className="text-white font-semibold text-lg">AI-Powered Analysis</h3>
              <p className="text-blue-100 text-sm mt-1">
                Get instant insights from research papers with advanced AI understanding
              </p>
            </div>
          </div>
          
          <div className="flex items-start gap-4">
            <div className="p-3 bg-white/10 rounded-xl">
              <Search className="h-6 w-6 text-white" />
            </div>
            <div>
              <h3 className="text-white font-semibold text-lg">Semantic Search</h3>
              <p className="text-blue-100 text-sm mt-1">
                Find relevant research using natural language queries across all your papers
              </p>
            </div>
          </div>
          
          <div className="flex items-start gap-4">
            <div className="p-3 bg-white/10 rounded-xl">
              <BookOpen className="h-6 w-6 text-white" />
            </div>
            <div>
              <h3 className="text-white font-semibold text-lg">Literature Reviews</h3>
              <p className="text-blue-100 text-sm mt-1">
                Generate comprehensive literature reviews and citations automatically
              </p>
            </div>
          </div>
          
          <div className="flex items-start gap-4">
            <div className="p-3 bg-white/10 rounded-xl">
              <Sparkles className="h-6 w-6 text-white" />
            </div>
            <div>
              <h3 className="text-white font-semibold text-lg">Smart Summaries</h3>
              <p className="text-blue-100 text-sm mt-1">
                Get key findings, themes, and research gaps identified instantly
              </p>
            </div>
          </div>
        </div>
        
        <p className="text-blue-200 text-sm">
          Trusted by researchers worldwide
        </p>
      </div>
      
      {/* Right Side - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center bg-linear-to-br from-gray-50 to-white p-6 sm:p-12">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden text-center mb-8">
            <h1 className="text-3xl font-bold bg-linear-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent mb-2">
              LitWise
            </h1>
            <p className="text-gray-500">
              Your AI-powered research assistant
            </p>
          </div>
          
          <LoginForm />
        </div>
      </div>
    </div>
  )
}