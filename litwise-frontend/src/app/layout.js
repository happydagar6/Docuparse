'use client';

import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/contexts/AuthContext";
import { QueryProvider as ReactQueryProvider} from "@/lib/react-query"
import { AppShell } from "@/components/layout/AppShell"

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export default function Layout({ children }) {
  return (
    <html lang="en">
      <head>
        <title>Litwise - AI-Powered Research Companion</title>
        <meta name="description" content="Upload, analyze, and discover insights from your documents and papers using AI" />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ReactQueryProvider>
          <AuthProvider>
            <AppShell>
              {children}
            </AppShell>
            <Toaster position="top-right" richColors />
          </AuthProvider>
        </ReactQueryProvider>
      </body>
    </html>
  );
}
