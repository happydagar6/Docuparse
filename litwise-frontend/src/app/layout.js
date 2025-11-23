import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { RootLayout } from "@/components/layout/Layout";

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
        <RootLayout>{children}</RootLayout>
      </body>
    </html>
  );
}
