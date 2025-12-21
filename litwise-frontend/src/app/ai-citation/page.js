"use client";

import { useState, useEffect, useRef } from 'react';
import { generateAICitation } from '@/lib/api';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Upload, Sparkles, Copy, CheckCircle2, XCircle, FileText, Loader2, Check } from 'lucide-react';

export default function AICitationGenerator() {
  const [file, setFile] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [result, setResult] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [copied, setCopied] = useState(false);
  const fileInputRef = useRef(null);

  // Smart loading message timer
  useEffect(() => {
    if (isGenerating) {
      setLoadingMessage('Scanning for DOI...');
      
      const timer = setTimeout(() => {
        setLoadingMessage('Consulting AI for details...');
      }, 2000);
      
      return () => clearTimeout(timer);
    }
  }, [isGenerating]);

  const handleFileSelect = (selectedFile) => {
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setResult(null);
      toast.success(`Selected: ${selectedFile.name}`);
    } else {
      toast.error('Please select a valid PDF file');
    }
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      handleFileSelect(selectedFile);
    }
  };

  // Drag and drop handlers
  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  };

  const handleGenerate = async () => {
    if (!file) {
      toast.error('Please select a PDF file first');
      return;
    }

    setIsGenerating(true);
    try {
      console.log('🚀 Generating citation for:', file.name);
      const response = await generateAICitation(file);
      
      console.log('✅ Citation generated:', response);
      setResult(response);
      
      if (response.success) {
        toast.success(`Citation generated using ${response.source === 'crossref' ? 'Crossref API (free!)' : 'Grok AI'}`);
      } else {
        toast.error(response.error || 'Citation generation failed');
      }
    } catch (error) {
      console.error('❌ Citation generation error:', error);
      toast.error(error.message || 'Failed to generate citation');
      setResult({
        success: false,
        error: error.message
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = async () => {
    if (result?.citation) {
      await navigator.clipboard.writeText(result.citation);
      setCopied(true);
      toast.success('Citation copied to clipboard!');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="container max-w-4xl mx-auto py-8 px-4">
      <Card className="shadow-lg">
        <CardHeader className="bg-linear-to-r from-blue-50 to-indigo-50 border-b">
          <CardTitle className="flex items-center gap-2 text-2xl">
            <Sparkles className="w-7 h-7 text-blue-600" />
            AI-Powered Citation Generator
          </CardTitle>
          <CardDescription className="text-base">
            Upload a PDF to generate an APA 7th Edition citation using our hybrid DOI + AI approach.
            We first try to find the DOI and use the free Crossref API, then fall back to Grok AI if needed.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 pt-6">
          {/* Drag & Drop Zone */}
          <div
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`
              relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
              transition-all duration-200 ease-in-out
              ${isDragging 
                ? 'border-blue-500 bg-blue-50 scale-[1.02]' 
                : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
              }
              ${file ? 'bg-green-50 border-green-400' : ''}
            `}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="hidden"
            />
            
            <div className="flex flex-col items-center gap-4">
              {file ? (
                <>
                  <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
                    <FileText className="w-8 h-8 text-green-600" />
                  </div>
                  <div>
                    <p className="text-lg font-semibold text-green-800">{file.name}</p>
                    <p className="text-sm text-green-600 mt-1">
                      {(file.size / 1024).toFixed(1)} KB · Click to change
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center">
                    <Upload className="w-8 h-8 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-lg font-semibold text-gray-700">
                      {isDragging ? 'Drop your PDF here' : 'Drag & drop your PDF here'}
                    </p>
                    <p className="text-sm text-gray-500 mt-1">or click to browse files</p>
                  </div>
                  <p className="text-xs text-gray-400 mt-2">
                    Supports academic papers in PDF format
                  </p>
                </>
              )}
            </div>
          </div>

          {/* Generate Button with Smart Loading */}
          <Button
            onClick={handleGenerate}
            disabled={!file || isGenerating}
            className="w-full h-14 text-lg font-semibold"
            size="lg"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                {loadingMessage}
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5 mr-2" />
                Generate APA Citation
              </>
            )}
          </Button>

          {/* Results */}
          {result && (
            <div className="mt-6 space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
              {result.success ? (
                <>
                  {/* Citation Display Card */}
                  <Card className="border-2 border-gray-200 shadow-md overflow-hidden">
                    <CardHeader className="bg-linear-to-r from-gray-50 to-gray-100 border-b pb-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <CheckCircle2 className="w-6 h-6 text-green-600" />
                          <div>
                            <CardTitle className="text-lg">APA 7th Edition Citation</CardTitle>
                            <CardDescription className="text-xs mt-1">
                              Ready to use in your research paper
                            </CardDescription>
                          </div>
                        </div>
                        
                        {/* Source Badge */}
                        {result.source === 'crossref' ? (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-green-100 text-green-800 text-xs font-semibold rounded-full border border-green-300">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Verified Source
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-yellow-100 text-yellow-800 text-xs font-semibold rounded-full border border-yellow-300">
                            <Sparkles className="w-3.5 h-3.5" />
                            AI Generated
                          </span>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="p-6">
                      {/* Citation Text Block */}
                      <div className="relative bg-gray-50 border border-gray-200 rounded-lg p-5">
                        <p className="text-sm leading-loose text-gray-800 font-serif whitespace-pre-wrap">
                          {result.citation}
                        </p>
                        
                        {/* Copy Button - Positioned in top right */}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={handleCopy}
                          className="absolute top-3 right-3 h-8"
                        >
                          {copied ? (
                            <>
                              <Check className="w-4 h-4 mr-1 text-green-600" />
                              <span className="text-green-600">Copied!</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-4 h-4 mr-1" />
                              Copy
                            </>
                          )}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Metadata */}
                  {result.metadata && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Extracted Metadata</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <dl className="grid grid-cols-1 gap-3 text-sm">
                          {result.metadata.title && (
                            <>
                              <dt className="font-semibold text-gray-700">Title:</dt>
                              <dd className="text-gray-600">{result.metadata.title}</dd>
                            </>
                          )}
                          {result.metadata.authors && result.metadata.authors.length > 0 && (
                            <>
                              <dt className="font-semibold text-gray-700">Authors:</dt>
                              <dd className="text-gray-600">{result.metadata.authors.join(', ')}</dd>
                            </>
                          )}
                          {result.metadata.year && (
                            <>
                              <dt className="font-semibold text-gray-700">Year:</dt>
                              <dd className="text-gray-600">{result.metadata.year}</dd>
                            </>
                          )}
                          {result.metadata.journal && (
                            <>
                              <dt className="font-semibold text-gray-700">Journal:</dt>
                              <dd className="text-gray-600 italic">{result.metadata.journal}</dd>
                            </>
                          )}
                          {result.metadata.doi && (
                            <>
                              <dt className="font-semibold text-gray-700">DOI:</dt>
                              <dd className="text-gray-600">
                                <a 
                                  href={`https://doi.org/${result.metadata.doi.replace('doi:', '').replace('https://doi.org/', '').trim()}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-blue-600 hover:underline"
                                >
                                  {result.metadata.doi.replace('doi:', '').replace('https://doi.org/', '').trim()}
                                </a>
                              </dd>
                            </>
                          )}
                        </dl>
                      </CardContent>
                    </Card>
                  )}
                </>
              ) : (
                /* Error */
                <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <XCircle className="w-5 h-5 text-red-600 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-red-800">Citation Generation Failed</p>
                    <p className="text-sm text-red-700 mt-1">{result.error}</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Info */}
          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h4 className="text-sm font-semibold text-blue-900 mb-2">How it works:</h4>
            <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
              <li>Extracts text from the first 2 pages of your PDF</li>
              <li>Searches for a DOI (Digital Object Identifier)</li>
              <li>If DOI found: Fetches official metadata from Crossref (free!)</li>
              <li>If no DOI: Uses Grok AI to extract metadata intelligently</li>
              <li>Formats the citation according to APA 7th Edition standards</li>
            </ol>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
