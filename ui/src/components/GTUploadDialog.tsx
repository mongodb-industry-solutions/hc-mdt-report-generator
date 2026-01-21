import React, { useState, useRef } from 'react';
import { Upload, X, FileText, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { apiService } from '../services/api';
import { GTUploadProgress, GroundTruthEntity } from '../types';

interface GTUploadDialogProps {
  isOpen: boolean;
  onClose: () => void;
  patientId: string;
  reportUuid: string;
  onComplete: (entities: GroundTruthEntity[]) => void;
}


export default function GTUploadDialog({
  isOpen,
  onClose,
  patientId,
  reportUuid,
  onComplete,
}: GTUploadDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const [ocrEngine, setOcrEngine] = useState<'mistral' | 'easyocr'>('easyocr');
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState<GTUploadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (selectedFile.type !== 'application/pdf') {
        setError('Please select a PDF file');
        return;
      }
      if (selectedFile.size > 20 * 1024 * 1024) {
        setError('File size must be less than 20MB');
        return;
      }
      setFile(selectedFile);
      setError(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      if (droppedFile.type !== 'application/pdf') {
        setError('Please select a PDF file');
        return;
      }
      if (droppedFile.size > 20 * 1024 * 1024) {
        setError('File size must be less than 20MB');
        return;
      }
      setFile(droppedFile);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    setError(null);
    setProgress(null);

    try {
      // LLM provider is determined by backend from LLM_PROVIDER env var
      let completed = false;
      const result = await apiService.uploadGroundTruth(
        patientId,
        reportUuid,
        file,
        ocrEngine,
        (data) => {
          setProgress(data);
          if (data.status === 'FAILED') {
            setError(data.message);
            setIsUploading(false);
          }
          // Handle COMPLETED in callback since SSE stream may not close properly in production
          if (data.status === 'COMPLETED' && data.data?.entities && !completed) {
            completed = true;
            setIsUploading(false);
            onComplete(data.data.entities);
          }
        }
      );

      // Fallback: also check result in case stream closed normally
      if (!completed && result?.status === 'COMPLETED' && result.data?.entities) {
        onComplete(result.data.entities);
      }
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleClose = () => {
    if (!isUploading) {
      setFile(null);
      setProgress(null);
      setError(null);
      onClose();
    }
  };

  const getStatusIcon = () => {
    if (!progress) return null;
    switch (progress.status) {
      case 'COMPLETED':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'FAILED':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Loader2 className="w-5 h-5 text-medical-600 animate-spin" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-xl font-semibold text-gray-900">
            Upload Ground Truth PDF
          </h2>
          <button
            onClick={handleClose}
            disabled={isUploading}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* File Drop Zone */}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`
              border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
              transition-colors duration-200
              ${file ? 'border-medical-500 bg-medical-50' : 'border-gray-300 hover:border-medical-400 hover:bg-gray-50'}
              ${isUploading ? 'pointer-events-none opacity-60' : ''}
            `}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileSelect}
              className="hidden"
              disabled={isUploading}
            />
            {file ? (
              <div className="flex flex-col items-center">
                <FileText className="w-12 h-12 text-medical-600 mb-3" />
                <p className="text-sm font-medium text-gray-900">{file.name}</p>
                <p className="text-xs text-gray-500 mt-1">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <Upload className="w-12 h-12 text-gray-400 mb-3" />
                <p className="text-sm font-medium text-gray-700">
                  Drop PDF here or click to browse
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Maximum file size: 20MB
                </p>
              </div>
            )}
          </div>

          {/* OCR Engine Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              OCR Engine
            </label>
            <div className="flex gap-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="ocr-engine"
                  value="easyocr"
                  checked={ocrEngine === 'easyocr'}
                  onChange={() => setOcrEngine('easyocr')}
                  disabled={isUploading}
                  className="w-4 h-4 text-medical-600 focus:ring-medical-500"
                />
                <span className="ml-2 text-sm text-gray-700">
                  EasyOCR
                  <span className="text-xs text-gray-500 ml-1">(faster, local)</span>
                </span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="ocr-engine"
                  value="mistral"
                  checked={ocrEngine === 'mistral'}
                  onChange={() => setOcrEngine('mistral')}
                  disabled={isUploading}
                  className="w-4 h-4 text-medical-600 focus:ring-medical-500"
                />
                <span className="ml-2 text-sm text-gray-700">
                  Mistral OCR
                  <span className="text-xs text-gray-500 ml-1">(better quality)</span>
                </span>
              </label>
            </div>
          </div>

          {/* Progress */}
          {progress && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                {getStatusIcon()}
                <span className="text-sm font-medium text-gray-700">
                  {progress.message}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all duration-300 ${
                    progress.status === 'FAILED' ? 'bg-red-500' : 'bg-medical-600'
                  }`}
                  style={{ width: `${progress.progress}%` }}
                />
              </div>
              {progress.status === 'COMPLETED' && progress.data && (
                <p className="text-sm text-green-600">
                  ✓ Extracted {progress.data.entity_count} entities from {progress.data.page_count} pages
                </p>
              )}
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t bg-gray-50 rounded-b-xl">
          <button
            onClick={handleClose}
            disabled={isUploading}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={!file || isUploading || progress?.status === 'COMPLETED'}
            className="px-4 py-2 text-sm font-medium text-white bg-medical-600 rounded-lg hover:bg-medical-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Processing...
              </>
            ) : progress?.status === 'COMPLETED' ? (
              <>
                <CheckCircle className="w-4 h-4" />
                Done
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                Upload & Extract
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

