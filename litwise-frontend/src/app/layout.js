import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { RootLayout } from "@/components/layout/Layout";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/contexts/AuthContext";
import { QueryProvider as ReactQueryProvider} from "@/lib/react-query"

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "Litwise - AI-Powered Research Companion",
  description: "Upload, analyze, and discover insights from research papers using AI",
};

export default function Layout({ children }) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ReactQueryProvider>
          <AuthProvider> {/* ADD THIS WRAPPER */}
            {children}
            <Toaster position="top-right" richColors />
          </AuthProvider> {/* ADD THIS CLOSING TAG */}
        </ReactQueryProvider>
      </body>
    </html>
  );
}
