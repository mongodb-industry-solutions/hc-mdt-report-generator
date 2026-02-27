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
      {/* Action Bar */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
              <Inbox className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Incoming Documents</h2>
              <p className="text-sm text-gray-500">
                {total} document{total !== 1 ? 's' : ''} ready for processing
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3 flex-shrink-0">
            <button
              onClick={handleProcessSelected}
              disabled={selectedIds.size === 0 || isProcessing}
              className={`
                inline-flex items-center space-x-2 px-5 py-2.5 rounded-lg font-semibold text-sm
                transition-all duration-200 whitespace-nowrap
                ${selectedIds.size === 0 || isProcessing
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700 shadow-md hover:shadow-lg'
                }
              `}
            >
              {isProcessing ? (
                <>
                  <Loader className="w-4 h-4 animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  <span>Process Selected ({selectedIds.size})</span>
                </>
              )}
            </button>
            <button
              onClick={fetchDocuments}
              disabled={isLoading}
              className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-lg font-medium text-sm
                bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 transition-all whitespace-nowrap"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>

            {/* Block this button- Message: Due to Security Restrictions, this functionality is disabled for demo purposes */}

          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={() =>
                alert("This functionality is disabled for demo purposes due to security restrictions.")
              }
              className="btn-primary flex items-center space-x-2 opacity-60 cursor-not-allowed"
            >
              <Upload className="w-4 h-4" />
              <span>{t.documents.upload}</span>
            </button>
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

      {/* Processing Pipelines - Show when processing */}
      {isProcessing && processingStatus.size > 0 && (
        <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden w-full">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-blue-50 to-indigo-50">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center mr-3">
                  <Loader className="w-4 h-4 animate-spin text-white" />
                </div>
                Processing in Progress
              </h3>
              <span className="text-sm text-gray-500 bg-white px-3 py-1 rounded-full border border-gray-200">
                {Array.from(processingStatus.values()).filter(s => s.status === 'completed').length} / {processingStatus.size} complete
              </span>
            </div>
          </div>
          
          {/* Pipeline items */}
          <div className="divide-y divide-gray-100">
            {Array.from(processingStatus.entries()).map(([docId, status]) => {
              const doc = documents.find(d => d.id === docId);
              return (
                <div key={docId} className="px-6 py-5 bg-gray-50/50">
                  {/* Document name */}
                  <div className="mb-4 flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className={`w-2 h-2 rounded-full ${
                        status.status === 'completed' ? 'bg-green-500' :
                        status.status === 'failed' ? 'bg-red-500' :
                        'bg-blue-500 animate-pulse'
                      }`} />
                      <span className="font-medium text-gray-900">{doc?.file_name || docId}</span>
                    </div>
                    <span className={`text-sm font-semibold px-3 py-1 rounded-full ${
                      status.status === 'completed' ? 'bg-green-100 text-green-700' :
                      status.status === 'failed' ? 'bg-red-100 text-red-700' :
                      'bg-blue-100 text-blue-700'
                    }`}>
                      {status.progress || 0}%
                    </span>
                  </div>
                  
                  {/* Pipeline */}
                  <ProcessingPipeline 
                    status={status}
                    showLabels={true}
                    darkMode={false}
                  />
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Documents List */}
      {documents.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="text-center py-16 px-6">
            <div className="w-20 h-20 bg-gradient-to-br from-green-100 to-emerald-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
              <Sparkles className="w-10 h-10 text-green-500" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">All Caught Up!</h3>
            <p className="text-gray-500 max-w-md mx-auto mb-6">
              There are no documents waiting to be processed. All incoming documents have been successfully processed and are available in the Processed section.
            </p>
            <div className="flex items-center justify-center space-x-2 text-sm text-green-600 bg-green-50 rounded-lg px-4 py-2 w-fit mx-auto">
              <CheckCircle className="w-4 h-4" />
              <span>Ready to generate reports</span>
              <ArrowRight className="w-4 h-4" />
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden" style={{ maxWidth: '100%' }}>
          {/* Table Header */}
          <div className="bg-gradient-to-r from-gray-50 to-slate-50 border-b border-gray-200 px-6 py-4">
            <div className="flex items-center justify-between">
              <button
                onClick={selectAll}
                className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
              >
                {isAllSelected ? (
                  <CheckSquare className="w-5 h-5 text-blue-600" />
                ) : (
                  <Square className="w-5 h-5" />
                )}
                <span className="ml-2 text-sm font-medium">
                  {isAllSelected ? 'Deselect All' : 'Select All'}
                </span>
              </button>
              <span className="text-xs text-gray-400">
                Select documents and click "Process Selected" to begin extraction
              </span>
            </div>
          </div>

          {/* Document Rows */}
          <div className="divide-y divide-gray-100">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className={`
                  px-6 py-4 transition-all duration-200 cursor-pointer
                  ${selectedIds.has(doc.id) 
                    ? 'bg-blue-50 border-l-4 border-blue-500' 
                    : 'hover:bg-gray-50 border-l-4 border-transparent'
                  }
                `}
                onClick={() => !isProcessing && toggleSelection(doc.id)}
              >
                <div className="flex items-center space-x-4 overflow-hidden">
                  {/* Checkbox */}
                  <div
                    className="flex-shrink-0"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {selectedIds.has(doc.id) ? (
                      <CheckSquare className="w-5 h-5 text-blue-600" />
                    ) : (
                      <Square className="w-5 h-5 text-gray-400" />
                    )}
                  </div>

                  {/* File Icon */}
                  <div className={`flex-shrink-0 p-2.5 rounded-xl ${
                    selectedIds.has(doc.id) ? 'bg-blue-100' : 'bg-gray-100'
                  }`}>
                    {getFileIcon(doc.file_type)}
                  </div>

                  {/* Document Info */}
                  <div className="flex-1 min-w-0 overflow-hidden">
                    <div className="flex items-center space-x-2 overflow-hidden">
                      <h4 className="text-sm font-semibold text-gray-900 truncate">
                        {doc.file_name}
                      </h4>
                      <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-md font-medium">
                        {doc.file_type.toUpperCase()}
                      </span>
                    </div>
                    <div className="flex items-center space-x-4 mt-1 text-xs text-gray-500">
                      <span>{formatFileSize(doc.content_size)}</span>
                      {doc.source_system && (
                        <span>Source: {doc.source_system}</span>
                      )}
                      {doc.created_at && (
                        <span>
                          Added {formatDistanceToNow(new Date(doc.created_at), { addSuffix: true })}
                        </span>
                      )}
                    </div>
                    {doc.content_preview && (
                      <p className="text-xs text-gray-400 mt-1 overflow-hidden text-ellipsis whitespace-nowrap" style={{ maxWidth: '100%' }}>
                        {doc.content_preview.substring(0, 100)}{doc.content_preview.length > 100 ? '...' : ''}
                      </p>
                    )}
                  </div>

                  {/* Processing Status */}
                  <div className="flex-shrink-0">
                    {getStatusBadge(doc.id)}
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
