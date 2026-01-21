import React, { useState } from 'react';
import { FileText, Calendar, Clock, CheckCircle, AlertCircle, Loader, Upload, Download, Trash2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { PatientDocument } from '../types';
import FileUpload from './FileUpload';
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
        
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowUploadModal(true)}
            className="btn-primary flex items-center space-x-2"
          >
            <Upload className="w-4 h-4" />
            <span>{t.documents.upload}</span>
          </button>
          <button
            disabled={true}
            className="btn-outline flex items-center space-x-2 opacity-50 cursor-not-allowed"
            title="Coming soon: Fetch documents from EHR server"
          >
            <Download className="w-4 h-4" />
            <span>{t.documents.fetchFromEhr}</span>
          </button>
        </div>
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
        <div className="space-y-4">
          {documents.map((document) => (
            <div key={document.uuid} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <FileText className="w-5 h-5 text-gray-500" />
                    <h3 className="text-lg font-medium text-gray-900">
                      {document.filename || `Document ${document.uuid.slice(0, 8)}`}
                    </h3>
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(document.status)}
                      <span className={getStatusBadgeClass(document.status)}>
                        {getStatusText(document.status).toUpperCase()}
                      </span>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm text-gray-600">
                    <div>
                      <span className="font-medium">{t.documents.info.type}:</span>{' '}
                      <span className="capitalize">{document.type.replace('_', ' ')}</span>
                    </div>
                    <div>
                      <span className="font-medium">{t.documents.info.source}:</span>{' '}
                      {document.source || 'Unknown'}
                    </div>
                    <div>
                      <span className="font-medium">{t.documents.info.category}:</span>{' '}
                      {document.document_category || 'Not categorized'}
                    </div>
                    <div>
                      <span className="font-medium">{t.documents.info.entities}:</span>{' '}
                      {getExtractedEntitiesCount(document)} {t.documents.info.extracted}
                    </div>
                  </div>

                  <div className="flex items-center space-x-4 mt-3 text-sm text-gray-500">
                    <div className="flex items-center space-x-1">
                      <Calendar className="w-4 h-4" />
                      <span>{t.documents.info.created} {formatDistanceToNow(new Date(document.created_at))} {t.documents.info.ago}</span>
                    </div>
                    {document.processing_completed_at && (
                      <div className="flex items-center space-x-1">
                        <CheckCircle className="w-4 h-4" />
                        <span>{t.documents.info.processed} {formatDistanceToNow(new Date(document.processing_completed_at))} {t.documents.info.ago}</span>
                      </div>
                    )}
                  </div>

                  {document.notes && (
                    <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-700">{document.notes}</p>
                    </div>
                  )}

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
                <div className="ml-4">
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
            </div>
          ))}
        </div>
      )}
    </div>
  );
} 