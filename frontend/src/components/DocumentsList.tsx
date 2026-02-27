import React, { useState } from 'react';
import { FileText, Calendar, Clock, CheckCircle, AlertCircle, Loader, Upload, Download, Trash2, Eye, Search, FileSearch } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { PatientDocument } from '../types';
import FileUpload from './FileUpload';
import DocumentPreviewModal from './DocumentPreviewModal';
import { useI18n } from '../i18n/context';

interface DocumentsListProps {
  documents: PatientDocument[];
  onRefresh: () => void;
  patientId: string;
  onDocumentUploaded: (document: PatientDocument) => void;
  onDocumentStatusUpdate: (updatedDocument: PatientDocument) => void;
  onPatientIdChange?: (newPatientId: string) => void;
}

const getStatusIcon = (status: PatientDocument['status']) => {
  switch (status) {
    case 'done':
      return <CheckCircle className="w-4 h-4 text-green-600" />;
    case 'processing':
      return <Loader className="w-4 h-4 text-blue-600 animate-spin" />;
    case 'failed':
      return <AlertCircle className="w-4 h-4 text-red-600" />;
    default:
      return <Clock className="w-4 h-4 text-yellow-600" />;
  }
};

const getStatusBadgeClass = (status: PatientDocument['status']) => {
  switch (status) {
    case 'done':
      return 'status-done';
    case 'processing':
      return 'status-processing';
    case 'failed':
      return 'status-failed';
    default:
      return 'status-queued';
  }
};

export default function DocumentsList({ documents, onRefresh, patientId, onDocumentUploaded, onDocumentStatusUpdate, onPatientIdChange }: DocumentsListProps) {
  const { t } = useI18n();
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [previewDocument, setPreviewDocument] = useState<PatientDocument | null>(null);

  const getStatusText = (status: PatientDocument['status']) => {
    switch (status) {
      case 'done':
        return t.documents.status.done;
      case 'processing':
        return t.documents.status.processing;
      case 'failed':
        return t.documents.status.failed;
      default:
        return t.documents.status.queued;
    }
  };

  const getExtractedEntitiesCount = (document: PatientDocument): number => {
    if (!document.extracted_data) return 0;
    
    // Count entities in extracted data
    const extractedData = document.extracted_data;
    let count = 0;
    
    if (typeof extractedData === 'object' && extractedData !== null) {
      // Count non-null, non-empty values
      count = Object.values(extractedData).filter(value => {
        if (value === null || value === undefined || value === '') return false;
        if (typeof value === 'object' && Object.keys(value).length === 0) return false;
        return true;
      }).length;
    }
    
    return count;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{t.documents.title}</h2>
          <p className="text-gray-600">
            {documents.length} {t.documents.documentsFor} {patientId}
          </p>
        </div>
        
        {/* <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowUploadModal(true)}
            className="btn-primary flex items-center space-x-2"
          >
            <Upload className="w-4 h-4" />
            <span>{t.documents.upload}</span>
          </button>
        </div> */}
      </div>

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

      {/* Documents List */}
      {documents.length === 0 ? (
        <div className="card text-center py-12">
          <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">{t.documents.empty.title}</h3>
          <p className="text-gray-500 mb-4">
            {t.documents.empty.description}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {documents.map((document) => (
            <div key={document.uuid} className="bg-white rounded-xl shadow-lg border border-gray-200 hover:shadow-xl transition-all duration-300 overflow-hidden">
              {/* Document Header */}
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-4 border-b">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3">
                    <div className="p-2 bg-white rounded-lg shadow-sm flex-shrink-0">
                      <FileText className="w-6 h-6 text-blue-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-base font-semibold text-gray-900 break-words leading-tight">
                        {document.filename || `Document ${document.uuid.slice(0, 8)}`}
                      </h3>
                      <div className="flex items-center space-x-2 mt-1">
                        {getStatusIcon(document.status)}
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusBadgeClass(document.status)}`}>
                          {getStatusText(document.status).toUpperCase()}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Document Content Preview */}
              <div className="p-4">
                {/* Quick Info Grid */}
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">{t.documents.info.type}</div>
                    <div className="text-sm font-semibold text-gray-900 mt-1 capitalize">
                      {document.type.replace('_', ' ')}
                    </div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">{t.documents.info.source}</div>
                    <div className="text-sm font-semibold text-gray-900 mt-1">
                      {document.source || 'Unknown'}
                    </div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">{t.documents.info.category}</div>
                    <div className="text-sm font-semibold text-gray-900 mt-1">
                      {document.document_category || 'Not categorized'}
                    </div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-3">
                    <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">{t.documents.info.entities}</div>
                    <div className="text-sm font-semibold text-gray-900 mt-1">
                      {getExtractedEntitiesCount(document)} {t.documents.info.extracted}
                    </div>
                  </div>
                </div>

                {/* OCR Text Preview */}
                {document.ocr_text && (
                  <div className="bg-blue-50 rounded-lg p-3 mb-4">
                    <div className="flex items-center space-x-2 mb-2">
                      <FileSearch className="w-4 h-4 text-blue-600" />
                      <span className="text-xs font-medium text-blue-700 uppercase tracking-wide">Text Preview</span>
                    </div>
                    <p className="text-sm text-gray-700 line-clamp-3">
                      {document.ocr_text.substring(0, 200)}{document.ocr_text.length > 200 ? '...' : ''}
                    </p>
                    <div className="text-xs text-blue-600 mt-1">
                      {document.character_count} chars • {document.word_count} words
                    </div>
                  </div>
                )}

                {/* Dates */}
                <div className="flex items-center justify-between text-xs text-gray-500 mb-4">
                  <div className="flex items-center space-x-1">
                    <Calendar className="w-3 h-3" />
                    <span>{t.documents.info.created} {formatDistanceToNow(new Date(document.created_at))} {t.documents.info.ago}</span>
                  </div>
                  {document.processing_completed_at && (
                    <div className="flex items-center space-x-1">
                      <CheckCircle className="w-3 h-3 text-green-500" />
                      <span>{t.documents.info.processed} {formatDistanceToNow(new Date(document.processing_completed_at))} {t.documents.info.ago}</span>
                    </div>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="flex items-center justify-between pt-3 border-t border-gray-200">
                  <button
                    onClick={() => setPreviewDocument(document)}
                    className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                  >
                    <Eye className="w-4 h-4" />
                    <span>Preview</span>
                  </button>
                  
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={async () => {
                        try {
                          const { apiService } = await import('../services/api');
                          const fullDoc = await apiService.getDocument(patientId, document.uuid);
                          if (fullDoc.file_content) {
                            const blob = new Blob([atob(fullDoc.file_content)], { type: 'application/octet-stream' });
                            const url = URL.createObjectURL(blob);
                            const link = window.document.createElement('a');
                            link.href = url;
                            link.download = document.filename || 'document.pdf';
                            link.click();
                            URL.revokeObjectURL(url);
                          }
                        } catch (error) {
                          console.error('Download failed:', error);
                          alert('Download failed. Please try again.');
                        }
                      }}
                      title="Download document"
                      className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                    <button
                      onClick={async () => {
                        if (!window.confirm('Delete this document permanently?')) return;
                        const { apiService } = await import('../services/api');
                        await apiService.deleteDocument(patientId, document.uuid);
                        onRefresh();
                      }}
                      title="Delete document"
                      className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Notes */}
                {document.notes && (
                  <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-sm text-yellow-800">{document.notes}</p>
                  </div>
                )}

                {/* Errors */}
                {(document.errors?.length ?? 0) > 0 && (
                  <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <h4 className="text-sm font-medium text-red-800 mb-1">Processing Errors:</h4>
                    <ul className="text-sm text-red-700 space-y-1">
                      {(document.errors || []).map((error, index) => (
                        <li key={index}>• {error}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      {/* Document Preview Modal */}
      {previewDocument && (
        <DocumentPreviewModal
          isOpen={true}
          onClose={() => setPreviewDocument(null)}
          document={previewDocument}
          patientId={patientId}
        />
      )}
    </div>
  );
} 