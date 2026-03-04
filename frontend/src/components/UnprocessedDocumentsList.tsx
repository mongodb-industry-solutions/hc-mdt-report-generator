import React, { useState, useEffect, useCallback } from 'react';
import {
  FileText,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader,
  Play,
  RefreshCw,
  File,
  Check,
  Square,
  CheckSquare,
  FileImage,
  FileSpreadsheet,
  FileCode,
  XCircle,
  Sparkles,
  ArrowRight,
  Inbox,
  Zap,
  Upload
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import {
  UnprocessedDocument,
  PaginatedUnprocessedDocuments,
  ProcessDocumentsResponse,
  ProcessingStatus,
  PatientDocument
} from '../types';
import { apiService } from '../services/api';
import { useI18n } from '../i18n/context';
import ProcessingPipeline, { MiniPipeline } from './ProcessingPipeline';
import FileUpload from './FileUpload';

interface UnprocessedDocumentsListProps {
  patientId: string;
  onProcessingComplete?: () => void;
  onDocumentUploaded: (document: PatientDocument) => void;
  onDocumentStatusUpdate: (updatedDocument: PatientDocument) => void;
  onPatientIdChange?: (newPatientId: string) => void;
}

// Get file icon based on type
const getFileIcon = (fileType: string) => {
  const type = fileType.toLowerCase().replace('.', '');
  switch (type) {
    case 'pdf':
      return <FileText className="w-5 h-5 text-red-500" />;
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'avif':
      return <FileImage className="w-5 h-5 text-purple-500" />;
    case 'csv':
      return <FileSpreadsheet className="w-5 h-5 text-green-500" />;
    case 'json':
    case 'xml':
      return <FileCode className="w-5 h-5 text-orange-500" />;
    case 'docx':
    case 'pptx':
      return <FileText className="w-5 h-5 text-blue-500" />;
    default:
      return <File className="w-5 h-5 text-gray-500" />;
  }
};

// Format file size
const formatFileSize = (bytes?: number): string => {
  if (!bytes || bytes === 0) return 'Unknown size';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

export default function UnprocessedDocumentsList({
  patientId,
  onProcessingComplete,
  onDocumentUploaded, 
  onDocumentStatusUpdate, 
  onPatientIdChange 
}: UnprocessedDocumentsListProps) {
  const { t } = useI18n();
  
  // State
  const [documents, setDocuments] = useState<UnprocessedDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<Map<string, ProcessingStatus>>(new Map());
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const pageSize = 20;

  // Fetch documents
  const fetchDocuments = useCallback(async () => {
    // Guard against empty patient ID
    if (!patientId) {
      setIsLoading(false);
      setDocuments([]);
      setTotal(0);
      setHasMore(false);
      return;
    }
    
    setIsLoading(true);
    setError(null);
    try {
      const response: PaginatedUnprocessedDocuments = await apiService.getUnprocessedDocuments(
        patientId,
        page,
        pageSize
      );
      setDocuments(response.items);
      setTotal(response.total);
      setHasMore(response.has_more);
    } catch (err) {
      console.error('Failed to fetch unprocessed documents:', err);
      setError('Failed to load unprocessed documents. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [patientId, page, pageSize]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Selection handlers
  const toggleSelection = (id: string) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const selectAll = () => {
    if (selectedIds.size === documents.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(documents.map(d => d.id)));
    }
  };

  const isAllSelected = documents.length > 0 && selectedIds.size === documents.length;

  // Process selected documents
  const handleProcessSelected = async () => {
    if (selectedIds.size === 0) return;

    setIsProcessing(true);
    setError(null);

    // Initialize processing status for selected documents
    const initialStatus = new Map<string, ProcessingStatus>();
    selectedIds.forEach(id => {
      initialStatus.set(id, {
        document_id: id,
        status: 'pending',
        current_step: 'Queued for processing'
      });
    });
    setProcessingStatus(initialStatus);

    try {
      const response: ProcessDocumentsResponse = await apiService.processUnprocessedDocuments(
        patientId,
        Array.from(selectedIds)
      );

      console.log('Processing started:', response);

      // Update status based on response
      const newStatus = new Map(processingStatus);
      response.processing_jobs.forEach(job => {
        newStatus.set(job.unprocessed_document_id, {
          document_id: job.unprocessed_document_id,
          status: 'processing',
          current_step: 'Processing started',
          new_document_uuid: job.new_document_uuid
        });
      });
      response.errors.forEach(err => {
        newStatus.set(err.document_id, {
          document_id: err.document_id,
          status: 'failed',
          error: err.error
        });
      });
      setProcessingStatus(newStatus);

      // Start polling for status updates
      if (response.processing_started > 0) {
        pollProcessingStatus(Array.from(selectedIds));
      }

    } catch (err) {
      console.error('Failed to process documents:', err);
      setError('Failed to start processing. Please try again.');
      setIsProcessing(false);
    }
  };

  // Poll for processing status
  const pollProcessingStatus = async (documentIds: string[]) => {
    const pollInterval = 2000; // 2 seconds
    const maxPolls = 60; // Max 2 minutes
    let polls = 0;

    const poll = async () => {
      try {
        const response = await apiService.getUnprocessedProcessingStatus(patientId, documentIds);
        
        // Update status
        const newStatus = new Map<string, ProcessingStatus>();
        response.documents.forEach(status => {
          newStatus.set(status.document_id, status);
        });
        setProcessingStatus(newStatus);

        // Check if all done
        const allDone = response.completed + response.failed === documentIds.length;
        
        if (allDone || polls >= maxPolls) {
          setIsProcessing(false);
          setSelectedIds(new Set());
          
          // Refresh the document list
          fetchDocuments();
          
          // Notify parent that processing is complete
          if (onProcessingComplete) {
            onProcessingComplete();
          }
        } else {
          polls++;
          setTimeout(poll, pollInterval);
        }
      } catch (err) {
        console.error('Failed to poll processing status:', err);
        polls++;
        if (polls < maxPolls) {
          setTimeout(poll, pollInterval);
        } else {
          setIsProcessing(false);
        }
      }
    };

    poll();
  };

  // Get status badge for a document
  const getStatusBadge = (docId: string) => {
    const status = processingStatus.get(docId);
    if (!status) return null;

    // Show mini pipeline for processing documents
    if (status.status === 'processing' && status.steps) {
      return (
        <div className="flex flex-col items-end gap-1">
          <span className="flex items-center text-blue-600 text-xs">
            <Loader className="w-3 h-3 mr-1 animate-spin" />
            {status.progress || 0}%
          </span>
          <MiniPipeline status={status} />
        </div>
      );
    }

    switch (status.status) {
      case 'completed':
        return (
          <span className="flex items-center text-green-600 text-sm">
            <CheckCircle className="w-4 h-4 mr-1" />
            Processed
          </span>
        );
      case 'processing':
        return (
          <span className="flex items-center text-blue-600 text-sm">
            <Loader className="w-4 h-4 mr-1 animate-spin" />
            {status.current_step || 'Processing...'}
          </span>
        );
      case 'failed':
        return (
          <span className="flex items-center text-red-600 text-sm" title={status.error}>
            <XCircle className="w-4 h-4 mr-1" />
            Failed
          </span>
        );
      case 'pending':
        return (
          <span className="flex items-center text-yellow-600 text-sm">
            <Clock className="w-4 h-4 mr-1" />
            Pending
          </span>
        );
      default:
        return null;
    }
  };

  // Render
  if (isLoading && documents.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader className="w-8 h-8 text-blue-600 animate-spin" />
        <span className="ml-3 text-gray-600">Loading unprocessed documents...</span>
      </div>
    );
  }

  if (error && documents.length === 0) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Documents</h3>
        <p className="text-gray-500 mb-4">{error}</p>
        <button onClick={fetchDocuments} className="btn-primary">
          <RefreshCw className="w-4 h-4 mr-2" />
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 overflow-x-hidden w-full max-w-full">
      {/* Professional Action Bar */}
      <div className="bg-gradient-to-r from-white via-slate-50/30 to-white rounded-xl shadow-sm border border-slate-200/60 overflow-hidden">
        {/* Premium Header Section */}
        <div className="border-b border-slate-100/80 bg-gradient-to-r from-slate-50/40 via-white to-slate-50/40">
          <div className="p-6">
            <div className="flex flex-wrap items-center justify-between gap-6">
              <div className="flex items-center space-x-4">
                {/* Premium Icon Container */}
                <div className="relative">
                  <div className="w-12 h-12 bg-gradient-to-br from-slate-600 via-slate-700 to-slate-800 rounded-xl flex items-center justify-center shadow-lg">
                    <Inbox className="w-6 h-6 text-white" />
                  </div>
                  {/* Status indicator dot */}
                  <div className="absolute -top-1 -right-1 w-4 h-4 bg-gradient-to-r from-emerald-500 to-green-500 rounded-full border-2 border-white flex items-center justify-center">
                    <div className="w-1.5 h-1.5 bg-white rounded-full"></div>
                  </div>
                </div>
                
                {/* Professional Title Section */}
                <div className="space-y-1">
                  <div className="flex items-center space-x-3">
                    <h2 className="text-xl font-bold bg-gradient-to-r from-slate-800 to-slate-600 bg-clip-text text-transparent tracking-tight">
                      Incoming Documents
                    </h2>
                    {total > 0 && (
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-gradient-to-r from-amber-100 to-orange-100 text-amber-800 border border-amber-200/50">
                        {total} Pending
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-600 font-medium">
                    {total === 0 
                      ? 'No documents waiting for processing' 
                      : `${total} document${total !== 1 ? 's' : ''} awaiting intelligent extraction and processing`
                    }
                  </p>
                </div>
              </div>

              {/* Premium Action Buttons */}
              <div className="flex items-center space-x-3 flex-shrink-0">
                {/* Primary Process Button */}
                <button
                  onClick={handleProcessSelected}
                  disabled={selectedIds.size === 0 || isProcessing}
                  className={`
                    group relative inline-flex items-center space-x-2.5 px-6 py-3 rounded-xl font-semibold text-sm
                    transition-all duration-300 ease-out whitespace-nowrap overflow-hidden
                    ${selectedIds.size === 0 || isProcessing
                      ? 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200'
                      : 'bg-gradient-to-r from-slate-700 via-slate-800 to-slate-900 text-white hover:from-slate-800 hover:via-slate-900 hover:to-black shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 border border-slate-600/20'
                    }
                  `}
                >
                  {/* Background shimmer effect (only when enabled) */}
                  {selectedIds.size > 0 && !isProcessing && (
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent skew-x-12 -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
                  )}
                  
                  {isProcessing ? (
                    <>
                      <Loader className="w-4 h-4 animate-spin" />
                      <span>Processing Documents...</span>
                    </>
                  ) : (
                    <>
                      <div className="w-4 h-4 bg-gradient-to-br from-emerald-400 to-emerald-500 rounded-sm flex items-center justify-center">
                        <Zap className="w-2.5 h-2.5 text-white" />
                      </div>
                      <span>Process Selected ({selectedIds.size})</span>
                    </>
                  )}
                </button>
                
                {/* Secondary Refresh Button */}
                <button
                  onClick={fetchDocuments}
                  disabled={isLoading}
                  className="group inline-flex items-center space-x-2 px-5 py-3 rounded-xl font-medium text-sm
                    bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 hover:border-slate-300 
                    transition-all duration-200 whitespace-nowrap shadow-sm hover:shadow-md"
                >
                  <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : 'group-hover:rotate-180 transition-transform duration-500'}`} />
                  <span>Refresh</span>
                </button>

                {/* Disabled Upload Button with Professional Styling */}
                <div className="flex items-center space-x-3">
                  <button
                    type="button"
                    onClick={() =>
                      alert("This functionality is disabled for demo purposes due to security restrictions.")
                    }
                    className="group inline-flex items-center space-x-2 px-5 py-3 rounded-xl font-medium text-sm
                      bg-slate-100 border border-slate-200 text-slate-500 cursor-not-allowed
                      relative overflow-hidden"
                  >
                    {/* Disabled overlay pattern */}
                    <div className="absolute inset-0 bg-[repeating-linear-gradient(45deg,transparent,transparent_2px,rgba(0,0,0,0.03)_2px,rgba(0,0,0,0.03)_4px)]"></div>
                    <Upload className="w-4 h-4" />
                    <span>{t.documents.upload}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center space-x-3">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <span className="text-red-700 text-sm">{error}</span>
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] flex flex-col">
            {/* Modal Header - Fixed */}
            <div className="p-6 border-b border-gray-200 flex-shrink-0">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-gray-900">{t.documents.uploadModal.title}</h3>
                <button
                  onClick={() => setShowUploadModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <span className="sr-only">Close</span>
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            
            {/* Modal Content - Scrollable */}
            <div className="flex-1 overflow-y-auto p-6">
              <FileUpload
                patientId={patientId}
                onDocumentUploaded={onDocumentUploaded}
                onDocumentStatusUpdate={onDocumentStatusUpdate}
                onPatientIdChange={onPatientIdChange}
              />
            </div>
          </div>
        </div>
      )}

      {/* Premium Processing Pipelines - Show when processing */}
      {isProcessing && processingStatus.size > 0 && (
        <div className="bg-gradient-to-br from-white via-slate-50/30 to-white rounded-xl shadow-lg border border-slate-200/60 overflow-hidden w-full">
          {/* Professional Header */}
          <div className="px-6 py-5 border-b border-slate-100/80 bg-gradient-to-r from-blue-50/50 via-indigo-50/30 to-blue-50/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl flex items-center justify-center shadow-lg">
                  <Loader className="w-5 h-5 animate-spin text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-bold bg-gradient-to-r from-slate-800 to-slate-600 bg-clip-text text-transparent">
                    Intelligent Processing in Progress
                  </h3>
                  <p className="text-sm text-slate-600 font-medium">
                    Extracting and analyzing document content with AI
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <span className="text-xs text-slate-500 font-medium">Progress</span>
                <span className="inline-flex items-center bg-gradient-to-r from-slate-100 to-slate-200 px-4 py-2 rounded-lg border border-slate-300/50 text-sm font-bold text-slate-700">
                  {Array.from(processingStatus.values()).filter(s => s.status === 'completed').length} / {processingStatus.size} Complete
                </span>
              </div>
            </div>
          </div>
          
          {/* Premium Pipeline Items */}
          <div className="divide-y divide-slate-100/80">
            {Array.from(processingStatus.entries()).map(([docId, status], index) => {
              const doc = documents.find(d => d.id === docId);
              return (
                <div key={docId} className={`px-6 py-6 ${
                  index === 0 ? 'bg-slate-50/30' : index % 2 === 0 ? 'bg-slate-50/20' : 'bg-white'
                }`}>
                  {/* Professional Document Header */}
                  <div className="mb-5 flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      {/* Professional Status Indicator */}
                      <div className={`w-3 h-3 rounded-full border-2 border-white shadow-sm ${
                        status.status === 'completed' 
                          ? 'bg-gradient-to-r from-emerald-500 to-green-600' :
                        status.status === 'failed' 
                          ? 'bg-gradient-to-r from-red-500 to-red-600' :
                        'bg-gradient-to-r from-blue-500 to-indigo-600 animate-pulse'
                      }`} />
                      
                      <div className="space-y-1">
                        <span className="font-bold text-slate-900 text-sm">{doc?.file_name || docId}</span>
                        <div className="flex items-center space-x-2">
                          {doc?.file_type && (
                            <span className="text-xs font-semibold bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md">
                              {doc.file_type.toUpperCase()}
                            </span>
                          )}
                          <span className="text-xs text-slate-500 font-medium">
                            {status.status === 'completed' ? 'Extraction Complete' :
                             status.status === 'failed' ? 'Processing Failed' :
                             'Processing...'}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    {/* Professional Progress Badge */}
                    <span className={`text-sm font-bold px-4 py-2 rounded-lg shadow-sm border ${
                      status.status === 'completed' 
                        ? 'bg-gradient-to-r from-emerald-50 to-green-50 text-emerald-700 border-emerald-200' :
                      status.status === 'failed' 
                        ? 'bg-gradient-to-r from-red-50 to-red-50 text-red-700 border-red-200' :
                        'bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 border-blue-200'
                    }`}>
                      {status.status === 'completed' ? '✓ Complete' :
                       status.status === 'failed' ? '✗ Failed' :
                       `${status.progress || 0}%`}
                    </span>
                  </div>
                  
                  {/* Enhanced Pipeline */}
                  <div className="bg-gradient-to-r from-slate-50 to-white rounded-lg p-4 border border-slate-200/50">
                    <ProcessingPipeline 
                      status={status}
                      showLabels={true}
                      darkMode={false}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Premium Empty State */}
      {documents.length === 0 ? (
        <div className="bg-gradient-to-br from-white via-slate-50/30 to-white rounded-xl border border-slate-200/60 shadow-sm overflow-hidden">
          <div className="text-center py-20 px-6">
            {/* Premium Success Icon */}
            <div className="relative mx-auto mb-8 w-24 h-24">
              {/* Outer glow ring */}
              <div className="absolute inset-0 bg-gradient-to-br from-emerald-100 to-green-100 rounded-2xl opacity-60 blur-sm"></div>
              {/* Main container */}
              <div className="relative w-full h-full bg-gradient-to-br from-emerald-50 via-green-50 to-emerald-100 rounded-2xl flex items-center justify-center border border-emerald-200/50">
                <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-green-600 rounded-lg flex items-center justify-center shadow-lg">
                  <Sparkles className="w-6 h-6 text-white" />
                </div>
              </div>
              {/* Floating particles */}
              <div className="absolute top-2 right-4 w-2 h-2 bg-emerald-400 rounded-full opacity-60 animate-pulse"></div>
              <div className="absolute bottom-3 left-3 w-1.5 h-1.5 bg-green-500 rounded-full opacity-40 animate-pulse delay-300"></div>
            </div>
            
            {/* Premium Typography */}
            <div className="space-y-4 max-w-md mx-auto">
              <h3 className="text-2xl font-bold bg-gradient-to-r from-slate-800 via-slate-700 to-slate-600 bg-clip-text text-transparent leading-tight">
                All Caught Up!
              </h3>
              <p className="text-slate-600 leading-relaxed font-medium">
                Excellent work! All incoming documents have been successfully processed and are now available 
                for report generation in the <span className="font-semibold text-slate-700">Processed Documents</span> section.
              </p>
            </div>
            
            {/* Professional Status Badge */}
            <div className="mt-8 flex items-center justify-center">
              <div className="inline-flex items-center space-x-3 bg-gradient-to-r from-emerald-50 to-green-50 rounded-xl px-6 py-3 border border-emerald-200/50 shadow-sm">
                <div className="w-5 h-5 bg-gradient-to-br from-emerald-500 to-green-600 rounded-full flex items-center justify-center">
                  <CheckCircle className="w-3 h-3 text-white" />
                </div>
                <span className="text-sm font-semibold text-emerald-700">Ready for Report Generation</span>
                <ArrowRight className="w-4 h-4 text-emerald-500" />
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-gradient-to-br from-white via-slate-50/20 to-white rounded-xl shadow-lg border border-slate-200/60 overflow-hidden" style={{ maxWidth: '100%' }}>
          {/* Premium Table Header */}
          <div className="bg-gradient-to-r from-slate-600/5 via-slate-500/5 to-slate-600/5 border-b border-slate-200/80 px-6 py-5">
            <div className="flex items-center justify-between">
              {/* Professional Select All */}
              <button
                onClick={selectAll}
                className="group flex items-center space-x-3 text-slate-600 hover:text-slate-900 transition-all duration-200 px-3 py-2 rounded-lg hover:bg-slate-100/60"
              >
                <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all duration-200 ${
                  isAllSelected 
                    ? 'bg-slate-700 border-slate-700' 
                    : 'border-slate-300 group-hover:border-slate-400 bg-white'
                }`}>
                  {isAllSelected && <Check className="w-3 h-3 text-white" />}
                </div>
                <span className="text-sm font-semibold">
                  {isAllSelected ? 'Deselect All Documents' : 'Select All Documents'}
                </span>
                {!isAllSelected && (
                  <span className="text-xs text-slate-400 bg-slate-100 px-2 py-1 rounded-md">
                    {documents.length} items
                  </span>
                )}
              </button>
              
              {/* Professional Helper Text */}
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-gradient-to-r from-amber-400 to-orange-500 rounded-full animate-pulse"></div>
                <span className="text-xs text-slate-500 font-medium">
                  Select documents and click "Process Selected" to begin intelligent extraction
                </span>
              </div>
            </div>
          </div>

          {/* Premium Document Rows */}
          <div className="divide-y divide-slate-100/80">
            {documents.map((doc, index) => (
              <div
                key={doc.id}
                className={`
                  group px-6 py-5 transition-all duration-300 ease-out cursor-pointer relative
                  ${selectedIds.has(doc.id) 
                    ? 'bg-gradient-to-r from-slate-50 via-slate-50/50 to-white border-l-4 border-slate-600 shadow-sm' 
                    : 'hover:bg-slate-50/40 border-l-4 border-transparent hover:border-slate-200'
                  }
                  ${index === 0 ? 'rounded-t-none' : ''}
                  ${index === documents.length - 1 ? 'rounded-b-xl' : ''}
                `}
                onClick={() => !isProcessing && toggleSelection(doc.id)}
              >
                {/* Selection gradient overlay */}
                {selectedIds.has(doc.id) && (
                  <div className="absolute inset-0 bg-gradient-to-r from-slate-600/5 to-transparent opacity-20"></div>
                )}
                
                <div className="flex items-center space-x-5 overflow-hidden relative">
                  {/* Premium Checkbox */}
                  <div
                    className="flex-shrink-0 z-10"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all duration-200 ${
                      selectedIds.has(doc.id) 
                        ? 'bg-slate-700 border-slate-700 shadow-sm' 
                        : 'border-slate-300 bg-white group-hover:border-slate-400'
                    }`}>
                      {selectedIds.has(doc.id) && <Check className="w-3 h-3 text-white" />}
                    </div>
                  </div>

                  {/* Enhanced File Icon Container */}
                  <div className={`
                    flex-shrink-0 p-3 rounded-xl transition-all duration-200 shadow-sm
                    ${selectedIds.has(doc.id) 
                      ? 'bg-gradient-to-br from-slate-100 to-slate-200 border border-slate-200/50' 
                      : 'bg-gradient-to-br from-gray-50 to-gray-100 border border-gray-200/50 group-hover:from-slate-50 group-hover:to-slate-100 group-hover:border-slate-300/50'
                    }
                  `}>
                    {getFileIcon(doc.file_type)}
                  </div>

                  {/* Premium Document Info */}
                  <div className="flex-1 min-w-0 overflow-hidden space-y-2">
                    <div className="flex items-center space-x-3 overflow-hidden">
                      <h4 className={`text-sm font-bold truncate transition-colors duration-200 ${
                        selectedIds.has(doc.id) ? 'text-slate-900' : 'text-slate-800 group-hover:text-slate-900'
                      }`}>
                        {doc.file_name}
                      </h4>
                      <span className={`text-xs font-bold px-2.5 py-1 rounded-md transition-all duration-200 ${
                        selectedIds.has(doc.id)
                          ? 'bg-slate-600 text-white'
                          : 'bg-slate-100 text-slate-700 group-hover:bg-slate-200'
                      }`}>
                        {doc.file_type.toUpperCase()}
                      </span>
                    </div>
                    
                    {/* Professional Metadata */}
                    <div className="flex items-center space-x-4 text-xs font-medium">
                      <div className="flex items-center space-x-1.5 text-slate-500">
                        <div className="w-1.5 h-1.5 bg-slate-400 rounded-full"></div>
                        <span>{formatFileSize(doc.content_size)}</span>
                      </div>
                      {doc.source_system && (
                        <div className="flex items-center space-x-1.5 text-slate-500">
                          <div className="w-1.5 h-1.5 bg-blue-400 rounded-full"></div>
                          <span>Source: {doc.source_system}</span>
                        </div>
                      )}
                      {doc.created_at && (
                        <div className="flex items-center space-x-1.5 text-slate-500">
                          <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full"></div>
                          <span>
                            Added {formatDistanceToNow(new Date(doc.created_at), { addSuffix: true })}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Professional Status Indicator */}
                  <div className="flex-shrink-0">
                    <div className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all duration-200 ${
                      selectedIds.has(doc.id)
                        ? 'bg-amber-100 text-amber-800 border border-amber-200'
                        : 'bg-gray-100 text-gray-600 group-hover:bg-slate-100 group-hover:text-slate-700'
                    }`}>
                      Pending Extraction
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {(hasMore || page > 1) && (
            <div className="bg-gray-50 border-t border-gray-200 px-6 py-3 flex items-center justify-between">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className={`btn-outline text-sm ${page === 1 ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                Previous
              </button>
              <span className="text-sm text-gray-600">
                Page {page} of {Math.ceil(total / pageSize)}
              </span>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={!hasMore}
                className={`btn-outline text-sm ${!hasMore ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
