/**
 * Upload Form Component
 * 
 * This is the main entry point of the Litwise application flow.
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
import { Upload, FileText, AlertCircle, CheckCircle, X } from 'lucide-react';
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
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="text-center flex items-center justify-center gap-2">
          <Upload className="h-6 w-6" />
          Upload Research Paper
        </CardTitle>
      </CardHeader>
      
      <CardContent>
        {/* Upload Area */}
        <div
          className={`
            relative border-2 border-dashed rounded-lg p-8 text-center transition-all duration-200
            ${isDragOver ? 'border-primary bg-primary/5' : 'border-gray-300'}
            ${selectedFile ? 'border-green-500 bg-green-50' : ''}
            ${isUploading ? 'border-blue-500 bg-blue-50' : ''}
          `}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
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
                className="space-y-4"
              >
                <Upload className="h-12 w-12 mx-auto text-gray-400" />
                <div>
                  <p className="text-lg font-medium text-gray-900">
                    Drop your PDF here or{' '}
                    <button
                      onClick={openFilePicker}
                      className="text-primary hover:text-primary/80 underline"
                    >
                      browse files
                    </button>
                  </p>
                  <p className="text-sm text-gray-500 mt-2">
                    Supports PDF files up to 10MB
                  </p>
                </div>
              </motion.div>
            )}
            
            {selectedFile && !isUploading && !uploadSuccess && (
              <motion.div
                key="file-selected"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="space-y-4"
              >
                <FileText className="h-12 w-12 mx-auto text-green-500" />
                <div>
                  <p className="text-lg font-medium text-gray-900">
                    {selectedFile.name}
                  </p>
                  <p className="text-sm text-gray-500">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
                <div className="flex gap-3 justify-center">
                  <Button onClick={handleUpload} size="lg">
                    Upload & Process
                  </Button>
                  <Button onClick={handleReset} variant="outline" size="lg">
                    <X className="h-4 w-4 mr-2" />
                    Remove
                  </Button>
                </div>
              </motion.div>
            )}
            
            {isUploading && (
              <motion.div
                key="uploading"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="space-y-4"
              >
                <Upload className="h-12 w-12 mx-auto text-blue-500 animate-pulse" />
                <div>
                  <p className="text-lg font-medium text-gray-900">
                    Processing your paper...
                  </p>
                  <p className="text-sm text-gray-500 mb-4">
                    Extracting text and generating AI insights
                  </p>
                  <Progress value={uploadProgress} className="w-full" />
                  <p className="text-xs text-gray-400 mt-2">
                    {uploadProgress}% complete
                  </p>
                </div>
              </motion.div>
            )}
            
            {uploadSuccess && (
              <motion.div
                key="success"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="space-y-4"
              >
                <CheckCircle className="h-12 w-12 mx-auto text-green-500" />
                <div>
                  <p className="text-lg font-medium text-gray-900">
                    Upload Successful!
                  </p>
                  <p className="text-sm text-gray-500">
                    Your paper has been processed and is ready to view
                  </p>
                </div>
                <Button onClick={handleReset} size="lg">
                  Upload Another Paper
                </Button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        
        {/* Error Display */}
        {uploadError && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3"
          >
            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-red-800">Upload Failed</p>
              <p className="text-sm text-red-600">{uploadError}</p>
            </div>
            <Button 
              onClick={handleReset} 
              variant="ghost" 
              size="sm"
              className="ml-auto"
            >
              Try Again
            </Button>
          </motion.div>
        )}
        
        {/* Processing Steps Info */}
        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <h4 className="text-sm font-medium text-gray-900 mb-2">
            What happens after upload:
          </h4>
          <ol className="text-xs text-gray-600 space-y-1">
            <li>1. Text extraction from PDF</li>
            <li>2. AI-powered summarization</li>
            <li>3. Topic linking and related works generation</li>
            <li>4. Semantic embeddings for search</li>
          </ol>
        </div>
      </CardContent>
    </Card>
  );
}