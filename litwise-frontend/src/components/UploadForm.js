"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Progress } from "./ui/progress";
import { Spinner } from "./ui/spinner";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { FileText, Upload, CheckCircle, AlertCircle } from "lucide-react";
import { useUploadPaper } from "../lib/react-query";
import { useUploadStore } from "../lib/stores";
import { toast } from "sonner";

export default function UploadForm() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  
  const uploadMutation = useUploadPaper();
  const { 
    isUploading, 
    uploadProgress, 
    uploadSuccess, 
    uploadError,
    resetUpload 
  } = useUploadStore();

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type !== 'application/pdf') {
        toast.error('Please select a PDF file only');
        return;
      }
      if (file.size > 10 * 1024 * 1024) { // 10MB limit
        toast.error('File size must be less than 10MB');
        return;
      }
      setSelectedFile(file);
      resetUpload();
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!selectedFile) {
      toast.error('Please select a PDF file to upload');
      return;
    }

    try {
      const result = await uploadMutation.mutateAsync(selectedFile);
      
      // Reset form on success
      setTitle("");
      setSelectedFile(null);
      if (e.target.reset) e.target.reset();
      
      // Optional: Navigate to papers list or individual paper
      setTimeout(() => {
        router.push('/papers');
      }, 2000);
      
    } catch (error) {
      // Error handling is done by the mutation
      console.error('Upload failed:', error);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="h-5 w-5" />
          Upload Research Paper
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Title Input */}
          <div className="space-y-2">
            <label htmlFor="title" className="text-sm font-medium">
              Paper Title (Optional)
            </label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter paper title..."
              disabled={isUploading}
            />
          </div>

          {/* File Input */}
          <div className="space-y-2">
            <label htmlFor="file" className="text-sm font-medium">
              PDF File <span className="text-red-500">*</span>
            </label>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-gray-400 transition-colors">
              <input
                id="file"
                type="file"
                accept=".pdf"
                onChange={handleFileSelect}
                disabled={isUploading}
                className="hidden"
              />
              <label
                htmlFor="file"
                className="cursor-pointer flex flex-col items-center gap-2"
              >
                <FileText className="h-8 w-8 text-gray-400" />
                <span className="text-sm text-gray-600">
                  Click to select a PDF file or drag and drop
                </span>
                <span className="text-xs text-gray-500">
                  Maximum file size: 10MB
                </span>
              </label>
            </div>
            
            {selectedFile && (
              <div className="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-blue-600" />
                  <div>
                    <p className="text-sm font-medium text-blue-900">
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-blue-700">
                      {formatFileSize(selectedFile.size)}
                    </p>
                  </div>
                </div>
                <Badge variant="outline" className="bg-blue-100 text-blue-800">
                  PDF
                </Badge>
              </div>
            )}
          </div>

          {/* Progress Bar */}
          {isUploading && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Uploading...</span>
                <span className="text-sm text-gray-500">{Math.round(uploadProgress)}%</span>
              </div>
              <Progress value={uploadProgress} className="h-2" />
            </div>
          )}

          {/* Success State */}
          {uploadSuccess && (
            <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-sm font-medium text-green-900">
                  Upload successful!
                </p>
                <p className="text-xs text-green-700">
                  Redirecting to papers page...
                </p>
              </div>
            </div>
          )}

          {/* Error State */}
          {uploadError && (
            <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
              <AlertCircle className="h-5 w-5 text-red-600" />
              <div>
                <p className="text-sm font-medium text-red-900">
                  Upload failed
                </p>
                <p className="text-xs text-red-700">
                  {uploadError}
                </p>
              </div>
            </div>
          )}

          {/* Submit Button */}
          <Button 
            type="submit" 
            disabled={!selectedFile || isUploading}
            className="w-full"
          >
            {isUploading ? (
              <>
                <Spinner className="mr-2 h-4 w-4" />
                Uploading... {Math.round(uploadProgress)}%
              </>
            ) : (
              <>
                <Upload className="mr-2 h-4 w-4" />
                Upload PDF
              </>
            )}
          </Button>

          <p className="text-xs text-gray-500 text-center">
            By uploading, you agree that the content will be processed by AI for research insights.
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
