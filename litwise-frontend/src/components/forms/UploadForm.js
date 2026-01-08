/**
 * Upload Form Component - Minimal Interactive Design
 * 
 * Enhanced drag & drop interface with modern animations and visual feedback.
 * 
 * COMPONENT LOGIC FLOW:
 * 1. User drags & drops or selects a PDF file
 * 2. File validation (size, type, format) 
 * 3. File upload to FastAPI backend (/upload endpoint)
 * 4. Backend extracts text → runs LangGraph pipeline → stores in Supabase/Qdrant
 * 5. Progress tracking and success/error handling
 * 6. Redirect to paper reader on success
 * 
 * STATE MANAGEMENT:
 * - Zustand store for upload progress and UI state
 * - React Query for API calls and server state
 * - Local state for drag/drop interactions
 */

'use client';

import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileText, AlertCircle, CheckCircle, X, Sparkles, Zap, Brain } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { useUploadPaper } from '@/lib/react-query';
import { useUploadStore } from '@/lib/stores';
import { validatePDFFile } from '@/lib/api';

export function UploadForm({ onUploadSuccess }) {
  // Local state for drag/drop interactions
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
   
  // Ref for hidden file input
  const fileInputRef = useRef(null);
  
  // Zustand store for upload state
  const {
    isUploading,
    uploadProgress,
    uploadError,
    uploadSuccess,
    resetUpload
  } = useUploadStore();
  
  // React Query mutation for upload
  const uploadMutation = useUploadPaper();

  /**
   * Handle file selection (from input or drag/drop)
   * 
   * @param {File} file - Selected PDF file
   */
  const handleFileSelect = async (file) => {
    try {
      // Reset previous upload state
      resetUpload();
      
      // Validate file before upload
      validatePDFFile(file);
      
      // Set selected file for UI display
      setSelectedFile(file);
      
    } catch (error) {
      // Handle validation errors
      console.error('File validation failed:', error);
      // You could show an error notification here
    }
  };

  /**
   * Handle file upload to backend
   */
  const handleUpload = async () => {
    if (!selectedFile) return;
    
    try {
      // Start upload mutation
      const result = await uploadMutation.mutateAsync(selectedFile);
      
      // Call success callback (e.g., redirect to paper reader)
      if (onUploadSuccess) {
        onUploadSuccess(result);
      }
      
    } catch (error) {
      // Error handling is done in React Query mutation
      console.error('Upload failed:', error);
    }
  };

  /**
   * Drag and Drop Event Handlers
   */
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  /**
   * File Input Change Handler
   */
  const handleFileChange = (e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  /**
   * Reset form to initial state
   */
  const handleReset = () => {
    setSelectedFile(null);
    resetUpload();
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  /**
   * Open file picker
   */
  const openFilePicker = () => {
    fileInputRef.current?.click();
  };

  return (
    <Card className="w-full max-w-3xl mx-auto rounded-xl sm:rounded-2xl border-2 border-gray-100 shadow-xl sm:shadow-2xl bg-white/90 backdrop-blur-sm">
      <CardHeader className="pb-4 sm:pb-6 px-4 sm:px-6">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center"
        >
          <motion.div
            className="bg-linear-to-r from-blue-500 to-purple-500 rounded-lg sm:rounded-xl p-2 sm:p-3 w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-3 sm:mb-4"
            whileHover={{ 
              scale: 1.1, 
              rotate: 5,
              boxShadow: "0 10px 30px rgba(59, 130, 246, 0.3)"
            }}
            transition={{ type: "spring", stiffness: 300 }}
          >
            <Upload className="h-8 w-8 sm:h-10 sm:w-10 text-white mx-auto" />
          </motion.div>
          <CardTitle className="text-xl sm:text-2xl lg:text-3xl font-bold bg-linear-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Upload Research Paper
          </CardTitle>
          <p className="text-gray-600 mt-1 sm:mt-2 text-sm sm:text-base px-2">
            Transform your documents into an intelligent, searchable research companion
          </p>
        </motion.div>
      </CardHeader>
      
      <CardContent className="px-4 sm:px-6 lg:px-8 pb-4 sm:pb-6 lg:pb-8">
        {/* Enhanced Upload Area */}
        <motion.div
          className={`
            relative border-2 sm:border-3 border-dashed rounded-xl sm:rounded-2xl p-6 sm:p-8 lg:p-12 text-center transition-all duration-300 overflow-hidden
            ${isDragOver 
              ? 'border-blue-400 bg-linear-to-r from-blue-50 to-purple-50 scale-[1.02]' 
              : 'border-gray-300 hover:border-gray-400'
            }
            ${selectedFile ? 'border-green-400 bg-linear-to-r from-green-50 to-emerald-50' : ''}
            ${isUploading ? 'border-blue-400 bg-linear-to-r from-blue-50 to-indigo-50' : ''}
          `}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          whileHover={{ scale: selectedFile || isUploading ? 1 : 1.01 }}
          transition={{ type: "spring", stiffness: 200 }}
        >
          {/* Animated Background Particles */}
          {isDragOver && (
            <>
              <motion.div
                className="absolute top-4 left-4 w-2 h-2 bg-blue-400 rounded-full"
                animate={{ 
                  y: [0, -20, 0],
                  opacity: [0, 1, 0]
                }}
                transition={{ duration: 2, repeat: Infinity }}
              />
              <motion.div
                className="absolute top-8 right-8 w-3 h-3 bg-purple-400 rounded-full"
                animate={{ 
                  y: [0, -30, 0],
                  opacity: [0, 1, 0]
                }}
                transition={{ duration: 2.5, repeat: Infinity, delay: 0.5 }}
              />
              <motion.div
                className="absolute bottom-6 left-12 w-2 h-2 bg-indigo-400 rounded-full"
                animate={{ 
                  y: [0, -25, 0],
                  opacity: [0, 1, 0]
                }}
                transition={{ duration: 1.8, repeat: Infinity, delay: 1 }}
              />
            </>
          )}
          
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.md,.markdown,.csv,.tsv"
            onChange={handleFileChange}
            className="hidden"
          />
          
          <AnimatePresence mode="wait">
            {!selectedFile && !isUploading && !uploadSuccess && (
              <motion.div
                key="upload-area"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="space-y-4 sm:space-y-6"
              >
                <motion.div
                  className="bg-linear-to-r from-gray-100 to-blue-100 rounded-full p-4 sm:p-6 w-16 h-16 sm:w-20 sm:h-20 lg:w-24 lg:h-24 mx-auto"
                  animate={{ 
                    rotate: [0, 5, -5, 0],
                    scale: [1, 1.05, 1]
                  }}
                  transition={{ duration: 4, repeat: Infinity }}
                >
                  <Upload className="h-8 w-8 sm:h-10 sm:w-10 lg:h-12 lg:w-12 mx-auto text-blue-600" />
                </motion.div>
                <div>
                  <p className="text-lg sm:text-xl lg:text-2xl font-bold text-gray-900 mb-1 sm:mb-2">
                    Drop your document here
                  </p>
                  <p className="text-sm sm:text-base lg:text-lg text-gray-600 mb-3 sm:mb-4">
                    or{' '}
                    <motion.button
                      onClick={openFilePicker}
                      className="text-blue-600 hover:text-blue-700 underline font-semibold"
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      browse your files
                    </motion.button>
                  </p>
                  <div className="bg-white/60 backdrop-blur-sm rounded-lg sm:rounded-xl p-3 sm:p-4 border border-white/40 max-w-md mx-auto">
                    <p className="text-xs sm:text-sm text-gray-600 mb-2 sm:mb-3">
                      <strong>Supported:</strong> PDF, TXT, MD, CSV files up to 50MB
                    </p>
                    <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-6 text-[10px] sm:text-xs text-gray-500">
                      <div className="flex items-center gap-1">
                        <Brain className="h-3 w-3" />
                        AI Analysis
                      </div>
                      <div className="flex items-center gap-1">
                        <Sparkles className="h-3 w-3" />
                        Smart Search
                      </div>
                      <div className="flex items-center gap-1">
                        <Zap className="h-3 w-3" />
                        Instant Insights
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
            
            {selectedFile && !isUploading && !uploadSuccess && (
              <motion.div
                key="file-selected"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="space-y-4 sm:space-y-6"
              >
                <motion.div
                  className="bg-linear-to-r from-green-100 to-emerald-100 rounded-full p-4 sm:p-6 w-16 h-16 sm:w-20 sm:h-20 lg:w-24 lg:h-24 mx-auto"
                  animate={{ 
                    scale: [1, 1.1, 1],
                    rotate: [0, 10, 0]
                  }}
                  transition={{ duration: 0.6 }}
                >
                  <FileText className="h-8 w-8 sm:h-10 sm:w-10 lg:h-12 lg:w-12 mx-auto text-green-600" />
                </motion.div>
                <div>
                  <p className="text-base sm:text-lg lg:text-2xl font-bold text-gray-900 mb-2 px-2 break-all">
                    {selectedFile.name}
                  </p>
                  <div className="bg-white/60 backdrop-blur-sm rounded-lg sm:rounded-xl p-2 sm:p-3 border border-white/40 max-w-sm mx-auto mb-4 sm:mb-6">
                    <p className="text-sm sm:text-base lg:text-lg text-gray-600 font-medium">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center">
                  <motion.div
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <Button 
                      onClick={handleUpload} 
                      size="lg"
                      className="w-full sm:w-auto px-6 sm:px-8 py-3 sm:py-4 rounded-lg sm:rounded-xl bg-linear-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 text-white border-0 shadow-lg hover:shadow-xl transition-all text-sm sm:text-base"
                    >
                      <Sparkles className="h-4 w-4 sm:h-5 sm:w-5 mr-2" />
                      Upload & Process
                    </Button>
                  </motion.div>
                  <motion.div
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <Button 
                      onClick={handleReset} 
                      variant="outline" 
                      size="lg"
                      className="w-full sm:w-auto px-6 sm:px-8 py-3 sm:py-4 rounded-lg sm:rounded-xl border-2 text-sm sm:text-base"
                    >
                      <X className="h-4 w-4 sm:h-5 sm:w-5 mr-2" />
                      Remove
                    </Button>
                  </motion.div>
                </div>
              </motion.div>
            )}
            
            {isUploading && (
              <motion.div
                key="uploading"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="space-y-4 sm:space-y-6"
              >
                <motion.div
                  className="bg-linear-to-r from-blue-100 to-indigo-100 rounded-full p-4 sm:p-6 w-16 h-16 sm:w-20 sm:h-20 lg:w-24 lg:h-24 mx-auto"
                  animate={{ 
                    rotate: 360,
                    scale: [1, 1.1, 1]
                  }}
                  transition={{ 
                    rotate: { duration: 2, repeat: Infinity, ease: "linear" },
                    scale: { duration: 1, repeat: Infinity }
                  }}
                >
                  <Upload className="h-8 w-8 sm:h-10 sm:w-10 lg:h-12 lg:w-12 mx-auto text-blue-600" />
                </motion.div>
                <div>
                  <p className="text-lg sm:text-xl lg:text-2xl font-bold text-gray-900 mb-1 sm:mb-2">
                    Processing your research...
                  </p>
                  <p className="text-sm sm:text-base lg:text-lg text-gray-600 mb-4 sm:mb-6 px-2">
                    Our AI is extracting insights and generating summaries
                  </p>
                  <div className="max-w-md mx-auto px-4">
                    <Progress value={uploadProgress} className="w-full h-2 sm:h-3 rounded-full mb-2 sm:mb-3" />
                    <motion.p 
                      className="text-xs sm:text-sm text-blue-600 font-semibold"
                      animate={{ opacity: [0.5, 1, 0.5] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                    >
                      {uploadProgress}% complete
                    </motion.p>
                  </div>
                </div>
              </motion.div>
            )}
            
            {uploadSuccess && (
              <motion.div
                key="success"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="space-y-4 sm:space-y-6"
              >
                <motion.div
                  className="bg-linear-to-r from-green-100 to-emerald-100 rounded-full p-4 sm:p-6 w-16 h-16 sm:w-20 sm:h-20 lg:w-24 lg:h-24 mx-auto"
                  animate={{ 
                    scale: [0.8, 1.2, 1],
                    rotate: [0, 15, 0]
                  }}
                  transition={{ duration: 0.8 }}
                >
                  <CheckCircle className="h-8 w-8 sm:h-10 sm:w-10 lg:h-12 lg:w-12 mx-auto text-green-600" />
                </motion.div>
                <div>
                  <p className="text-lg sm:text-xl lg:text-2xl font-bold text-gray-900 mb-1 sm:mb-2">
                    Upload Successful! 🎉
                  </p>
                  <p className="text-sm sm:text-base lg:text-lg text-gray-600 mb-4 sm:mb-6 px-2">
                    Your paper has been processed and is ready for intelligent exploration
                  </p>
                </div>
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Button 
                    onClick={handleReset} 
                    size="lg"
                    className="px-6 sm:px-8 py-3 sm:py-4 rounded-lg sm:rounded-xl bg-linear-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white border-0 shadow-lg hover:shadow-xl transition-all text-sm sm:text-base"
                  >
                    Upload Another Paper
                  </Button>
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
        
        {/* Enhanced Error Display */}
        {uploadError && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            className="mt-4 sm:mt-6 p-4 sm:p-6 bg-linear-to-r from-red-50 to-rose-50 border-2 border-red-200 rounded-xl sm:rounded-2xl"
          >
            <div className="flex items-start gap-3 sm:gap-4">
              <motion.div
                className="bg-red-100 rounded-full p-1.5 sm:p-2 shrink-0"
                whileHover={{ scale: 1.1 }}
                transition={{ type: "spring", stiffness: 300 }}
              >
                <AlertCircle className="h-5 w-5 sm:h-6 sm:w-6 text-red-500" />
              </motion.div>
              <div className="flex-1 min-w-0">
                <p className="text-base sm:text-lg font-semibold text-red-800 mb-1">Upload Failed</p>
                <p className="text-sm sm:text-base text-red-700 mb-3 sm:mb-4 leading-relaxed wrap-break-word">{uploadError}</p>
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Button 
                    onClick={handleReset} 
                    variant="outline" 
                    size="sm"
                    className="border-red-300 text-red-700 hover:bg-red-100 rounded-lg sm:rounded-xl text-xs sm:text-sm"
                  >
                    Try Again
                  </Button>
                </motion.div>
              </div>
            </div>
          </motion.div>
        )}
        
        {/* Enhanced Processing Steps Info */}
        <motion.div 
          className="mt-6 sm:mt-8 bg-linear-to-r from-blue-50 via-indigo-50 to-purple-50 rounded-xl sm:rounded-2xl p-4 sm:p-6 border border-blue-200"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <div className="flex items-center gap-2 sm:gap-3 mb-3 sm:mb-4">
            <motion.div
              className="bg-linear-to-r from-blue-500 to-purple-500 rounded-lg p-1.5 sm:p-2"
              whileHover={{ scale: 1.1, rotate: 5 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <Sparkles className="h-4 w-4 sm:h-5 sm:w-5 text-white" />
            </motion.div>
            <h4 className="text-sm sm:text-base lg:text-lg font-bold text-gray-900">
              What happens after upload:
            </h4>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-4">
            {[
              {
                step: "1",
                title: "Text Extraction",
                description: "Advanced PDF parsing and content extraction",
                icon: FileText,
                bgColor: "#3b82f6",
                lightBg: "#dbeafe",
                textColor: "#1e40af"
              },
              {
                step: "2", 
                title: "AI Summarization",
                description: "Generate intelligent summaries and insights",
                icon: Brain,
                bgColor: "#a855f7",
                lightBg: "#f3e8ff",
                textColor: "#6d28d9"
              },
              {
                step: "3",
                title: "Topic Linking",
                description: "Connect themes and find related research",
                icon: Zap,
                bgColor: "#f97316",
                lightBg: "#fed7aa",
                textColor: "#ea580c"
              },
              {
                step: "4",
                title: "Semantic Search",
                description: "Enable intelligent content discovery",
                icon: Sparkles,
                bgColor: "#3b82f6",
                lightBg: "#dbeafe",
                textColor: "#1e40af"
              }
            ].map((item, index) => (
              <motion.div
                key={index}
                className="flex items-center gap-2 sm:gap-3 p-2 sm:p-3 bg-white/60 backdrop-blur-sm rounded-lg sm:rounded-xl border border-white/40"
                whileHover={{ scale: 1.02, y: -2 }}
                transition={{ type: "spring", stiffness: 300 }}
              >
                <div className="rounded-lg p-1.5 sm:p-2 shrink-0" style={{ backgroundColor: item.lightBg }}>
                  <item.icon className="h-3 w-3 sm:h-4 sm:w-4" style={{ color: item.textColor }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-gray-900 text-xs sm:text-sm">{item.title}</p>
                  <p className="text-[10px] sm:text-xs text-gray-600 leading-tight">{item.description}</p>
                </div>
                <span className="text-white text-[10px] sm:text-xs font-bold rounded-full w-4 h-4 sm:w-5 sm:h-5 flex items-center justify-center shrink-0" style={{ backgroundColor: item.bgColor }}>
                  {item.step}
                </span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </CardContent>
    </Card>
  );
}