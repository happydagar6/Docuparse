/**
 * Image Upload Modal Component
 * Handles figure upload with caption for APA-formatted research papers
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Upload, X, Loader2, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { getSupabaseClient } from '@/lib/supabase/client';
import Image from 'next/image';

export default function ImageUploadModal({ isOpen, onClose, onImageInsert }) {
    const [file, setFile] = useState(null);
    const [caption, setCaption] = useState('');
    const [altText, setAltText] = useState('');
    const [widthPercent, setWidthPercent] = useState(100);
    const [preview, setPreview] = useState(null);
    const [isUploading, setIsUploading] = useState(false);

    /**
     * Handle file selection
     * Creates preview and validates file type/size
     */
    const handleFileChange = (e) => {
        const selectedFile = e.target.files?.[0];
        if (!selectedFile) return;

        // Validate file type
        const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml'];
        if (!allowedTypes.includes(selectedFile.type)) {
            toast.error('Invalid file type. Please upload JPEG, PNG, GIF, WebP, or SVG images.');
            return;
        }

        // Validate file size (5MB max)
        const maxSize = 5 * 1024 * 1024; // 5MB
        if (selectedFile.size > maxSize) {
            toast.error(`File too large. Maximum size is 5MB. Your file is ${(selectedFile.size / 1024 / 1024).toFixed(1)}MB.`);
            return;
        }

        // Create preview
        const reader = new FileReader();
        reader.onloadend = () => {
            setPreview(reader.result);
        };
        reader.readAsDataURL(selectedFile);

        setFile(selectedFile);
    };

    /**
     * Remove selected file and reset form
     */
    const handleRemoveFile = () => {
        setFile(null);
        setPreview(null);
    };

    /**
     * Upload image to server and insert into editor
     */
    const handleUpload = async () => {
        if (!file) {
            toast.error('Please select an image file');
            return;
        }

        if (!caption.trim()) {
            toast.error('Please provide a figure caption');
            return;
        }

        setIsUploading(true);

        try {
            // Get backend API URL
            const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
            
            // Get Supabase authentication token
            const supabase = getSupabaseClient();
            const { data: { session } } = await supabase.auth.getSession();
            const token = session?.access_token;
            
            if (!token) {
                throw new Error('Not authenticated. Please log in again.');
            }
            
            // Create FormData for file upload
            const formData = new FormData();
            formData.append('file', file);
            formData.append('caption', caption.trim());

            // Upload to backend
            const response = await fetch(`${API_BASE_URL}/api/media/upload-figure`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to upload image');
            }

            const data = await response.json();

            // Insert image into editor with metadata
            // Ensure URL has full backend path
            const imageUrl = data.url.startsWith('http') ? data.url : `${API_BASE_URL}${data.url}`;
            
            onImageInsert({
                file_id: data.file_id,
                filename: data.filename,
                url: imageUrl,
                caption: caption.trim(),
                alt_text: altText.trim() || caption.trim(),
                width_percent: widthPercent,
            });

            // Reset form and close modal
            handleClose();
            toast.success('Figure uploaded successfully!');

        } catch (error) {
            console.error('Upload error:', error);
            toast.error(error.message || 'Failed to upload image');
        } finally {
            setIsUploading(false);
        }
    };

    /**
     * Close modal and reset form
     */
    const handleClose = () => {
        setFile(null);
        setPreview(null);
        setCaption('');
        setAltText('');
        setWidthPercent(100);
        onClose();
    };

    return (
        <Dialog open={isOpen} onOpenChange={handleClose}>
            <DialogContent className="sm:max-w-[600px]">
                <DialogHeader>
                    <DialogTitle>Insert Figure</DialogTitle>
                    <DialogDescription>
                        Upload an image for your research paper. Figures will be numbered automatically (Figure 1, Figure 2, etc.)
                        and formatted according to APA 7th Edition guidelines.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 mt-4">
                    {/* File Upload Area */}
                    {!file ? (
                        <div className="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-8">
                            <label
                                htmlFor="file-upload"
                                className="flex flex-col items-center justify-center cursor-pointer"
                            >
                                <Upload className="h-12 w-12 text-gray-400 mb-3" />
                                <span className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Click to upload image
                                </span>
                                <span className="text-xs text-gray-500 dark:text-gray-400">
                                    JPEG, PNG, GIF, WebP, or SVG (max 5MB)
                                </span>
                                <input
                                    id="file-upload"
                                    type="file"
                                    accept="image/jpeg,image/png,image/gif,image/webp,image/svg+xml"
                                    onChange={handleFileChange}
                                    className="hidden"
                                />
                            </label>
                        </div>
                    ) : (
                        <div className="relative">
                            {/* Image Preview */}
                            <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                                {preview && (
                                    <Image
                                        src={preview}
                                        alt="Preview"
                                        width={600}
                                        height={400}
                                        className="w-full h-auto max-h-64 object-contain bg-gray-50 dark:bg-gray-900"
                                        unoptimized
                                    />
                                )}
                            </div>

                            {/* Remove Button */}
                            <button
                                type="button"
                                onClick={handleRemoveFile}
                                className="absolute top-2 right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors"
                                title="Remove image"
                            >
                                <X className="h-4 w-4" />
                            </button>

                            {/* File Info */}
                            <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                                {file.name} ({(file.size / 1024).toFixed(1)} KB)
                            </div>
                        </div>
                    )}

                    {/* Caption Input (Required) */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Figure Caption *
                        </label>
                        <Textarea
                            value={caption}
                            onChange={(e) => setCaption(e.target.value)}
                            placeholder="e.g., Experimental setup showing the control and treatment groups."
                            rows={3}
                            className="w-full"
                        />
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            APA format: Sentence case (only first word and proper nouns capitalized)
                        </p>
                    </div>

                    {/* Alt Text (Optional) */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Alternative Text (for accessibility)
                        </label>
                        <Input
                            value={altText}
                            onChange={(e) => setAltText(e.target.value)}
                            placeholder="Brief description for screen readers"
                            className="w-full"
                        />
                    </div>

                    {/* Width Percentage */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Figure Width: {widthPercent}%
                        </label>
                        <input
                            type="range"
                            min="25"
                            max="100"
                            step="5"
                            value={widthPercent}
                            onChange={(e) => setWidthPercent(parseInt(e.target.value))}
                            className="w-full"
                        />
                        <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
                            <span>25%</span>
                            <span>50%</span>
                            <span>75%</span>
                            <span>100%</span>
                        </div>
                    </div>

                    {/* APA Guidelines Note */}
                    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
                        <div className="flex items-start gap-2">
                            <AlertCircle className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5 shrink-0" />
                            <div className="text-xs text-blue-800 dark:text-blue-300">
                                <strong>APA 7th Edition:</strong> Figures must be numbered sequentially (Figure 1, Figure 2, etc.)
                                and referenced in your text. Caption appears below the figure in sentence case.
                            </div>
                        </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex justify-end gap-2 pt-2">
                        <Button
                            type="button"
                            variant="outline"
                            onClick={handleClose}
                            disabled={isUploading}
                        >
                            Cancel
                        </Button>
                        <Button
                            type="button"
                            onClick={handleUpload}
                            disabled={!file || !caption.trim() || isUploading}
                        >
                            {isUploading ? (
                                <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Uploading...
                                </>
                            ) : (
                                'Insert Figure'
                            )}
                        </Button>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}
