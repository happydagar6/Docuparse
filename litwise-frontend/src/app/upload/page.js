/**
 * Upload Page - Minimal Interactive Design
 * 
 * Dedicated page for uploading and processing research papers with enhanced UI.
 */

'use client';

import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Upload, BookOpen, Sparkles, Zap, Brain } from 'lucide-react';
import { UploadForm } from '@/components/forms/UploadForm';
import { PageLayout } from '@/components/layout/Layout';

export default function UploadPage() {
  const router = useRouter();

  const handleUploadSuccess = (result) => {
    // Redirect to paper reader or papers list
    if (result?.id) {
      router.push(`/papers/${result.id}`);
    } else {
      router.push('/papers');
    }
  };

  return (
    <PageLayout
      title="Upload Your Documents"
      description="Upload PDF documents to extract insights and enable semantic search."
    >
      {/* Enhanced Hero Section */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-linear-to-br from-purple-50 via-blue-50 to-indigo-50 rounded-xl sm:rounded-2xl p-4 sm:p-6 lg:p-8 border border-purple-100 mb-6 sm:mb-8 lg:mb-12 relative overflow-hidden"
      >
        {/* Animated Background Elements */}
        <motion.div
          className="absolute top-0 right-0 w-24 sm:w-32 lg:w-40 h-24 sm:h-32 lg:h-40 bg-linear-to-br from-purple-200/30 to-blue-200/30 rounded-full blur-2xl"
          animate={{ 
            x: [0, 30, 0],
            y: [0, -20, 0],
            scale: [1, 1.2, 1]
          }}
          transition={{ duration: 8, repeat: Infinity }}
        />
        <motion.div
          className="absolute bottom-0 left-0 w-20 sm:w-24 lg:w-32 h-20 sm:h-24 lg:h-32 bg-linear-to-tr from-blue-200/30 to-indigo-200/30 rounded-full blur-xl"
          animate={{ 
            x: [0, -20, 0],
            y: [0, 20, 0],
            scale: [1, 1.3, 1]
          }}
          transition={{ duration: 6, repeat: Infinity }}
        />
        
        <div className="relative z-10 text-center max-w-4xl mx-auto">
          <motion.div
            className="bg-linear-to-r from-purple-500 to-blue-500 rounded-xl sm:rounded-2xl p-3 sm:p-4 w-14 h-14 sm:w-16 sm:h-16 lg:w-20 lg:h-20 mx-auto mb-4 sm:mb-6"
            whileHover={{ 
              scale: 1.1, 
              rotate: 10,
              boxShadow: "0 15px 40px rgba(139, 92, 246, 0.4)"
            }}
            whileTap={{ scale: 0.95 }}
            transition={{ type: "spring", stiffness: 300 }}
          >
            <Upload className="h-8 w-8 sm:h-10 sm:w-10 lg:h-12 lg:w-12 text-white mx-auto" />
          </motion.div>
          
          <motion.h1 
            className="text-2xl sm:text-3xl lg:text-5xl font-bold bg-linear-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent mb-2 sm:mb-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            Upload Your Documents
          </motion.h1>
          
          <motion.p 
            className="text-sm sm:text-base lg:text-xl text-gray-600 mb-4 sm:mb-6 lg:mb-8 leading-relaxed px-2"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            Transform your PDFs into intelligent, searchable insights powered by AI
          </motion.p>
          
          {/* Feature Highlights */}
          <motion.div 
            className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 lg:gap-6 max-w-3xl mx-auto"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <motion.div 
              className="bg-white/70 backdrop-blur-sm rounded-lg sm:rounded-xl p-4 sm:p-5 lg:p-6 border border-white/20"
              whileHover={{ scale: 1.05, y: -5 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <div className="bg-purple-100 rounded-lg p-2 sm:p-3 w-fit mx-auto mb-2 sm:mb-4">
                <Brain className="h-5 w-5 sm:h-6 sm:w-6 text-purple-600" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-1 sm:mb-2 text-sm sm:text-base">AI Analysis</h3>
              <p className="text-xs sm:text-sm text-gray-600">
                Automatic summarization and key insights extraction
              </p>
            </motion.div>
            
            <motion.div 
              className="bg-white/70 backdrop-blur-sm rounded-lg sm:rounded-xl p-4 sm:p-5 lg:p-6 border border-white/20"
              whileHover={{ scale: 1.05, y: -5 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <div className="bg-blue-100 rounded-lg p-2 sm:p-3 w-fit mx-auto mb-2 sm:mb-4">
                <Sparkles className="h-5 w-5 sm:h-6 sm:w-6 text-blue-600" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-1 sm:mb-2 text-sm sm:text-base">Smart Search</h3>
              <p className="text-xs sm:text-sm text-gray-600">
                Semantic search across all your research papers
              </p>
            </motion.div>
            
            <motion.div 
              className="bg-white/70 backdrop-blur-sm rounded-lg sm:rounded-xl p-4 sm:p-5 lg:p-6 border border-white/20"
              whileHover={{ scale: 1.05, y: -5 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <div className="bg-indigo-100 rounded-lg p-2 sm:p-3 w-fit mx-auto mb-2 sm:mb-4">
                <Zap className="h-5 w-5 sm:h-6 sm:w-6 text-indigo-600" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-1 sm:mb-2 text-sm sm:text-base">Instant Results</h3>
              <p className="text-xs sm:text-sm text-gray-600">
                Fast processing with immediate insights
              </p>
            </motion.div>
          </motion.div>
        </div>
      </motion.div>

      {/* Upload Form Container */}
      <motion.div 
        className="max-w-4xl mx-auto"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7 }}
      >
        <UploadForm onUploadSuccess={handleUploadSuccess} />
      </motion.div>

      {/* Process Steps */}
      <motion.div 
        className="max-w-4xl mx-auto mt-8 sm:mt-12 lg:mt-16"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9 }}
      >
        <div className="bg-linear-to-r from-gray-50 to-blue-50 rounded-xl sm:rounded-2xl p-4 sm:p-6 lg:p-8 border border-gray-200">
          <h2 className="text-lg sm:text-xl lg:text-2xl font-bold text-center text-gray-900 mb-4 sm:mb-6 lg:mb-8">How It Works</h2>
          
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 lg:gap-6">
            {[
              {
                step: "1",
                title: "Upload PDF",
                description: "Select and upload your document or paper",
                icon: Upload,
                bgColor: "#a855f7",
                lightBg1: "#f3e8ff",
                lightBg2: "#e9d5ff",
                textColor: "#6d28d9"
              },
              {
                step: "2", 
                title: "Extract Text",
                description: "AI processes and extracts content",
                icon: BookOpen,
                bgColor: "#3b82f6",
                lightBg1: "#dbeafe",
                lightBg2: "#bfdbfe",
                textColor: "#1e40af"
              },
              {
                step: "3",
                title: "Generate Insights",
                description: "Create summaries and key points",
                icon: Brain,
                bgColor: "#f97316",
                lightBg1: "#fed7aa",
                lightBg2: "#fdba74",
                textColor: "#ea580c"
              },
              {
                step: "4",
                title: "Ready to Explore",
                description: "Chat, search, and discover insights",
                icon: Sparkles,
                bgColor: "#a855f7",
                lightBg1: "#f3e8ff",
                lightBg2: "#e9d5ff",
                textColor: "#6d28d9"
              }
            ].map((item, index) => (
              <motion.div
                key={index}
                className="text-center"
                whileHover={{ scale: 1.05, y: -5 }}
                transition={{ type: "spring", stiffness: 300 }}
              >
                <div className="rounded-lg sm:rounded-xl p-2 sm:p-3 lg:p-4 w-10 h-10 sm:w-12 sm:h-12 lg:w-16 lg:h-16 mx-auto mb-2 sm:mb-3 lg:mb-4 flex items-center justify-center relative" style={{
                  backgroundImage: `linear-gradient(to bottom right, ${item.lightBg1}, ${item.lightBg2})`
                }}>
                  <span className="absolute -top-1 -right-1 sm:-top-2 sm:-right-2 text-white text-[10px] sm:text-xs font-bold rounded-full w-4 h-4 sm:w-5 sm:h-5 lg:w-6 lg:h-6 flex items-center justify-center" style={{ backgroundColor: item.bgColor }}>
                    {item.step}
                  </span>
                  <item.icon className="h-5 w-5 sm:h-6 sm:w-6 lg:h-8 lg:w-8" style={{ color: item.textColor }} />
                </div>
                <h3 className="font-semibold text-gray-900 mb-1 sm:mb-2 text-xs sm:text-sm lg:text-base">{item.title}</h3>
                <p className="text-[10px] sm:text-xs lg:text-sm text-gray-600 leading-tight">{item.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>
    </PageLayout>
  );
}