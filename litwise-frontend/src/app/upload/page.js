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
      title="Upload Research Paper"
      description="Upload a PDF research paper to extract insights and enable semantic search."
    >
      {/* Enhanced Hero Section */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50 rounded-2xl p-8 border border-purple-100 mb-12 relative overflow-hidden"
      >
        {/* Animated Background Elements */}
        <motion.div
          className="absolute top-0 right-0 w-40 h-40 bg-gradient-to-br from-purple-200/30 to-blue-200/30 rounded-full blur-2xl"
          animate={{ 
            x: [0, 30, 0],
            y: [0, -20, 0],
            scale: [1, 1.2, 1]
          }}
          transition={{ duration: 8, repeat: Infinity }}
        />
        <motion.div
          className="absolute bottom-0 left-0 w-32 h-32 bg-gradient-to-tr from-blue-200/30 to-indigo-200/30 rounded-full blur-xl"
          animate={{ 
            x: [0, -20, 0],
            y: [0, 20, 0],
            scale: [1, 1.3, 1]
          }}
          transition={{ duration: 6, repeat: Infinity }}
        />
        
        <div className="relative z-10 text-center max-w-4xl mx-auto">
          <motion.div
            className="bg-gradient-to-r from-purple-500 to-blue-500 rounded-2xl p-4 w-20 h-20 mx-auto mb-6"
            whileHover={{ 
              scale: 1.1, 
              rotate: 10,
              boxShadow: "0 15px 40px rgba(139, 92, 246, 0.4)"
            }}
            whileTap={{ scale: 0.95 }}
            transition={{ type: "spring", stiffness: 300 }}
          >
            <Upload className="h-12 w-12 text-white mx-auto" />
          </motion.div>
          
          <motion.h1 
            className="text-5xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent mb-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            Upload Your Research
          </motion.h1>
          
          <motion.p 
            className="text-xl text-gray-600 mb-8 leading-relaxed"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            Transform your PDFs into intelligent, searchable insights powered by AI
          </motion.p>
          
          {/* Feature Highlights */}
          <motion.div 
            className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-3xl mx-auto"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <motion.div 
              className="bg-white/70 backdrop-blur-sm rounded-xl p-6 border border-white/20"
              whileHover={{ scale: 1.05, y: -5 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <div className="bg-purple-100 rounded-lg p-3 w-fit mx-auto mb-4">
                <Brain className="h-6 w-6 text-purple-600" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">AI Analysis</h3>
              <p className="text-sm text-gray-600">
                Automatic summarization and key insights extraction
              </p>
            </motion.div>
            
            <motion.div 
              className="bg-white/70 backdrop-blur-sm rounded-xl p-6 border border-white/20"
              whileHover={{ scale: 1.05, y: -5 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <div className="bg-blue-100 rounded-lg p-3 w-fit mx-auto mb-4">
                <Sparkles className="h-6 w-6 text-blue-600" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">Smart Search</h3>
              <p className="text-sm text-gray-600">
                Semantic search across all your research papers
              </p>
            </motion.div>
            
            <motion.div 
              className="bg-white/70 backdrop-blur-sm rounded-xl p-6 border border-white/20"
              whileHover={{ scale: 1.05, y: -5 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <div className="bg-indigo-100 rounded-lg p-3 w-fit mx-auto mb-4">
                <Zap className="h-6 w-6 text-indigo-600" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">Instant Results</h3>
              <p className="text-sm text-gray-600">
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
        className="max-w-4xl mx-auto mt-16"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9 }}
      >
        <div className="bg-gradient-to-r from-gray-50 to-blue-50 rounded-2xl p-8 border border-gray-200">
          <h2 className="text-2xl font-bold text-center text-gray-900 mb-8">How It Works</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[
              {
                step: "1",
                title: "Upload PDF",
                description: "Select and upload your research paper",
                icon: Upload,
                color: "purple"
              },
              {
                step: "2", 
                title: "Extract Text",
                description: "AI processes and extracts content",
                icon: BookOpen,
                color: "blue"
              },
              {
                step: "3",
                title: "Generate Insights",
                description: "Create summaries and key points",
                icon: Brain,
                color: "indigo"
              },
              {
                step: "4",
                title: "Ready to Explore",
                description: "Chat, search, and discover insights",
                icon: Sparkles,
                color: "purple"
              }
            ].map((item, index) => (
              <motion.div
                key={index}
                className="text-center"
                whileHover={{ scale: 1.05, y: -5 }}
                transition={{ type: "spring", stiffness: 300 }}
              >
                <div className={`bg-gradient-to-br from-${item.color}-100 to-${item.color}-200 rounded-xl p-4 w-16 h-16 mx-auto mb-4 flex items-center justify-center relative`}>
                  <span className={`absolute -top-2 -right-2 bg-${item.color}-500 text-white text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center`}>
                    {item.step}
                  </span>
                  <item.icon className={`h-8 w-8 text-${item.color}-600`} />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{item.title}</h3>
                <p className="text-sm text-gray-600">{item.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>
    </PageLayout>
  );
}