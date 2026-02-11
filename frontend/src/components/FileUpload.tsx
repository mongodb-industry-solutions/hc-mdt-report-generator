import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, FileText, CheckCircle, AlertCircle, Loader, AlertTriangle } from 'lucide-react';
import { apiService } from '../services/api';
import { PatientDocument, UploadProgress } from '../types';
import { useI18n } from '../i18n/context';

interface FileUploadProps {
  patientId?: string | null;  // Now optional for UUID-first uploads
  onDocumentUploaded: (document: PatientDocument) => void;
  onDocumentStatusUpdate?: (document: PatientDocument) => void;
  onPatientIdChange?: (newPatientId: string) => void;
}

export default function FileUpload({ patientId, onDocumentUploaded, onDocumentStatusUpdate, onPatientIdChange }: FileUploadProps) {
  const { t } = useI18n();
  
  // State for manual patient ID input (UUID-first workflow)
  const [manualPatientIds, setManualPatientIds] = useState<{[uuid: string]: string}>({});
  const [assigningPatientId, setAssigningPatientId] = useState<{[uuid: string]: boolean}>({});
  
  const documentTypes = [
    { value: 'other', label: t.upload.form.autoDetect },
    { value: 'lab_report', label: t.upload.types.labReport },
    { value: 'diagnosis', label: t.upload.types.diagnosis },
    { value: 'treatment_plan', label: t.upload.types.treatmentPlan },
    { value: 'medical_history', label: t.upload.types.medicalHistory },
    { value: 'imaging', label: t.upload.types.imaging },
    { value: 'prescription', label: t.upload.types.prescription },
    { value: 'referral', label: t.upload.types.referral },
    { value: 'discharge_summary', label: t.upload.types.discharge },
    { value: 'operation_report', label: t.upload.types.operationReport },
    { value: 'consultation', label: t.upload.types.consultation },
  ];

  const sources = [
    { value: '', label: t.upload.form.sourceAutoDetect },
    { value: 'hospital', label: t.upload.sources.hospital },
    { value: 'clinic', label: t.upload.sources.clinic },
    { value: 'lab', label: t.upload.sources.laboratory },
    { value: 'gp', label: t.upload.sources.gp },
    { value: 'specialist', label: t.upload.sources.specialist },
    { value: 'pharmacy', label: t.upload.sources.pharmacy },
    { value: 'other', label: t.upload.types.other },
  ];
  // Load persisted uploads from sessionStorage (UUID-based, not patient-specific)
  const loadPersistedUploads = (): UploadProgress[] => {
    try {
      const stored = sessionStorage.getItem('uuid_uploads');
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  };

  const [uploads, setUploads] = useState<UploadProgress[]>(loadPersistedUploads);
  const [defaultDocType] = useState('other');
  const [defaultSource] = useState('');
  const [defaultNotes, setDefaultNotes] = useState('');

  // Persist uploads to sessionStorage whenever uploads change
  React.useEffect(() => {
    try {
      sessionStorage.setItem('uuid_uploads', JSON.stringify(uploads));
    } catch (error) {
      console.warn('Failed to persist uploads to sessionStorage:', error);
    }
  }, [uploads]);

  // Resume polling for any uploads that were in progress
  React.useEffect(() => {
    uploads.forEach((upload, index) => {
      if (upload.status === 'processing' && upload.uuid) {
        console.log(`Resuming polling for upload: ${upload.filename} (${upload.uuid})`);
        pollDocumentStatus(upload.uuid, index);
      }
    });
  }, []); // Only run on mount

  const onDrop = useCallback((acceptedFiles: File[]) => {
    // Initialize upload progress for each file
    const newUploads: UploadProgress[] = acceptedFiles.map(file => ({
      filename: file.name,
      progress: 0,
      status: 'pending'
    }));
    
    setUploads(prev => [...prev, ...newUploads]);

    // Upload each file
    acceptedFiles.forEach((file, index) => {
      uploadFile(file, uploads.length + index);
    });
  }, [defaultDocType, defaultSource, defaultNotes, uploads.length]);

  const uploadFile = async (file: File, uploadIndex: number) => {
    const updateProgress = (progress: number, status: UploadProgress['status'], error?: string, uuid?: string, message?: string) => {
      setUploads(prev => prev.map((upload, index) => 
        index === uploadIndex 
          ? { ...upload, progress, status, error, uuid, message }
          : upload
      ));
    };

    try {
      updateProgress(0, 'uploading');

      // Use UUID-first upload (no patient_id required)
      const document = await apiService.uploadDocumentUuidFirst(
        {
          file,
          type: defaultDocType,
          source: defaultSource,
          notes: defaultNotes,
        },
        (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            updateProgress(progress, 'uploading');
          }
        }
      );

      console.log(`📤 Document uploaded with UUID: ${document.uuid} (patient_id will be extracted)`);
      updateProgress(100, 'processing', undefined, document.uuid);
      
      // Start polling for document processing status using UUID-only endpoint
      pollDocumentStatus(document.uuid, uploadIndex);
      
      onDocumentUploaded(document);
      
    } catch (error) {
      console.error('Upload failed:', error);
      updateProgress(0, 'error', error instanceof Error ? error.message : 'Upload failed');
    }
  };

  const pollDocumentStatus = async (uuid: string, uploadIndex: number) => {
    const maxAttempts = 60; // 10 minutes max
    let attempts = 0;

    const poll = async () => {
      try {
        console.log(`📊 Polling document status for ${uuid}, attempt ${attempts + 1}`);
        
        // Use UUID-only endpoint (works regardless of patient_id)
        const document = await apiService.getDocumentByUuid(uuid);
        console.log(`Document status: ${document.status}, patient_id: ${document.patient_id}`, document);
        
        // Check if patient_id was extracted
        if (document.patient_id && onPatientIdChange) {
          console.log(`✅ Patient ID extracted: ${document.patient_id}`);
          onPatientIdChange(document.patient_id);
        }
        
        // Handle successful completion
        if (document.status === 'done' || document.status === 'completed' || document.status === 'processed') {
          console.log(`✅ Document processing completed for ${uuid}`);
          setUploads(prev => prev.map((upload, index) => 
            index === uploadIndex 
              ? { ...upload, status: 'completed', progress: 100 }
              : upload
          ));
          
          if (onDocumentStatusUpdate) {
            onDocumentStatusUpdate(document);
          }
          return;
        }
        
        // Handle requires_manual_input (patient_id not found)
        if (document.status === 'requires_manual_input') {
          console.log(`⚠️ Patient ID not found for ${uuid}, manual input required`);
          setUploads(prev => prev.map((upload, index) => 
            index === uploadIndex 
              ? { 
                  ...upload, 
                  status: 'requires_input' as any,
                  progress: 100,
                  message: 'Patient ID not found in document'
                }
              : upload
          ));
          
          if (onDocumentStatusUpdate) {
            onDocumentStatusUpdate(document);
          }
          return; // Stop polling
        }
        
        // Handle failure
        if (document.status === 'failed' || document.status === 'error') {
          console.log(`❌ Document processing failed for ${uuid}`);
          setUploads(prev => prev.map((upload, index) => 
            index === uploadIndex 
              ? { ...upload, status: 'error', error: 'Processing failed' }
              : upload
          ));
          
          if (onDocumentStatusUpdate) {
            onDocumentStatusUpdate(document);
          }
          return;
        }

        // Also check if extraction is completed as an indicator of completion
        if (document.extraction_status === 'success' || document.extraction_completed_at) {
          console.log(`✅ Document extraction completed for ${uuid}`);
          setUploads(prev => prev.map((upload, index) => 
            index === uploadIndex 
              ? { ...upload, status: 'completed', progress: 100 }
              : upload
          ));
          
          if (onDocumentStatusUpdate) {
            onDocumentStatusUpdate(document);
          }
          return;
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000); // Poll every 5 seconds
        } else {
          console.log(`⏰ Polling timeout for ${uuid} after ${maxAttempts} attempts`);
          setUploads(prev => prev.map((upload, index) => 
            index === uploadIndex 
              ? { ...upload, status: 'error', error: 'Processing timeout' }
              : upload
          ));
        }
      } catch (error) {
        console.error('❌ Polling failed:', error);
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000);
        }
      }
    };

    poll();
  };

  // Handle manual patient ID assignment
  const handleAssignPatientId = async (uuid: string) => {
    const inputPatientId = manualPatientIds[uuid]?.trim();
    if (!inputPatientId) return;
    
    setAssigningPatientId(prev => ({ ...prev, [uuid]: true }));
    
    try {
      console.log(`📝 Assigning patient ID ${inputPatientId} to document ${uuid}`);
      const document = await apiService.assignPatientId(uuid, inputPatientId);
      
      console.log(`✅ Patient ID assigned successfully`);
      
      // Update upload status to completed
      setUploads(prev => prev.map(upload =>
        upload.uuid === uuid
          ? { ...upload, status: 'completed', progress: 100, message: undefined }
          : upload
      ));
      
      // Notify parent of the new patient ID
      if (onPatientIdChange) {
        onPatientIdChange(document.patient_id!);
      }
      
      if (onDocumentStatusUpdate) {
        onDocumentStatusUpdate(document);
      }
      
      // Clear the manual input
      setManualPatientIds(prev => {
        const next = { ...prev };
        delete next[uuid];
        return next;
      });
      
    } catch (error) {
      console.error('❌ Failed to assign patient ID:', error);
      // Show error in UI
      setUploads(prev => prev.map(upload =>
        upload.uuid === uuid
          ? { ...upload, error: 'Failed to assign patient ID. Please try again.' }
          : upload
      ));
    } finally {
      setAssigningPatientId(prev => ({ ...prev, [uuid]: false }));
    }
  };

  const removeUpload = (index: number) => {
    setUploads(prev => prev.filter((_, i) => i !== index));
  };

  const clearCompleted = () => {
    setUploads(prev => prev.filter(upload => 
      upload.status !== 'completed' && upload.status !== 'error'
      // Keep requires_input since those need user attention
    ));
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg'],
      'text/plain': ['.txt'],
      'text/csv': ['.csv'],
      'application/json': ['.json'],
      'text/xml': ['.xml'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
    },
    multiple: true,
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  const getStatusIcon = (status: UploadProgress['status'] | 'requires_input') => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-600" />;
      case 'processing':
        return <Loader className="w-5 h-5 text-blue-600 animate-spin" />;
      case 'requires_input':
        return <AlertTriangle className="w-5 h-5 text-yellow-600" />;
      default:
        return <Loader className="w-5 h-5 text-yellow-600 animate-spin" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">{t.upload.title}</h2>
        <p className="text-gray-600">
          {t.upload.subtitle} {patientId}
        </p>
      </div>

      {/* Upload Settings */}
      <div className="card">
        <h3 className="text-lg font-medium text-gray-900 mb-4">{t.upload.settings}</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label htmlFor="docType" className="block text-sm font-medium text-gray-700 mb-1">
              {t.upload.form.type}
            </label>
            <select
              id="docType"
              value={defaultDocType}
              disabled={true}
              className="input-field bg-gray-100 cursor-not-allowed"
            >
              {documentTypes.map(type => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">
              {t.upload.form.autoDetectDescription}
            </p>
          </div>
          <div>
            <label htmlFor="source" className="block text-sm font-medium text-gray-700 mb-1">
              {t.upload.form.source}
            </label>
            <select
              id="source"
              value={defaultSource}
              disabled={true}
              className="input-field bg-gray-100 cursor-not-allowed"
            >
              {sources.map(source => (
                <option key={source.value} value={source.value}>
                  {source.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">
              {t.upload.form.sourceAutoDetectDescription}
            </p>
          </div>
          <div>
            <label htmlFor="notes" className="block text-sm font-medium text-gray-700 mb-1">
              {t.upload.form.notesOptional}
            </label>
            <input
              id="notes"
              type="text"
              value={defaultNotes}
              onChange={(e) => setDefaultNotes(e.target.value)}
              className="input-field"
              placeholder="Additional notes..."
            />
          </div>
        </div>
      </div>

      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${isDragActive 
            ? 'border-navy-400 bg-navy-50' 
            : 'border-gray-300 hover:border-gray-400 bg-gray-50 hover:bg-gray-100'
          }
        `}
      >
        <input {...getInputProps()} />
        <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <div className="text-lg font-medium text-gray-900 mb-2">
          {isDragActive ? 'Drop files here' : 'Upload medical documents'}
        </div>
        <p className="text-gray-600 mb-4">
          Drag and drop files here, or click to select files
        </p>
        <div className="space-y-2">
          <p className="text-sm text-gray-500">
            Supports PDF, images, text files, CSV, JSON, XML, DOCX, and PPTX (max 50MB each)
          </p>
          <p className="text-sm text-blue-600 bg-blue-50 px-3 py-2 rounded-lg">
            {t.upload.form.replacementNotice}
          </p>
        </div>
      </div>

      {/* Upload Progress */}
      {uploads.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">Upload Progress</h3>
            <button
              onClick={clearCompleted}
              className="btn-secondary text-sm"
            >
              Clear Completed
            </button>
          </div>
          
          <div className="space-y-3">
            {uploads.map((upload, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    <FileText className="w-5 h-5 text-gray-500" />
                    <span className="font-medium text-gray-900">{upload.filename}</span>
                    {getStatusIcon(upload.status)}
                  </div>
                  <button
                    onClick={() => removeUpload(index)}
                    className="p-1 text-gray-400 hover:text-gray-600"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                
                {upload.status === 'uploading' && (
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-navy-700 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${upload.progress}%` }}
                    />
                  </div>
                )}
                
                <div className="flex items-center justify-between mt-2 text-sm">
                  <span className={`
                    capitalize font-medium
                    ${upload.status === 'completed' ? 'text-green-600' : 
                      upload.status === 'error' ? 'text-red-600' :
                      (upload.status as any) === 'requires_input' ? 'text-yellow-600' :
                      'text-blue-600'}
                  `}>
                    {upload.status === 'processing' ? 'Processing document...' : 
                     (upload.status as any) === 'requires_input' ? 'Requires patient ID' :
                     upload.status}
                  </span>
                  {upload.status === 'uploading' && (
                    <span className="text-gray-500">{upload.progress}%</span>
                  )}
                </div>
                
                {/* Manual Patient ID Input for requires_input status */}
                {(upload.status as any) === 'requires_input' && upload.uuid && (
                  <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <div className="flex items-start mb-2">
                      <AlertTriangle className="w-4 h-4 text-yellow-600 mt-0.5 mr-2 flex-shrink-0" />
                      <div>
                        <p className="text-sm font-medium text-yellow-800">
                          Patient ID Not Found
                        </p>
                        <p className="text-xs text-yellow-700 mt-1">
                          Could not extract patient identifier (NumdosGR) from this document.
                          Please enter the patient ID manually.
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-2 mt-2">
                      <input
                        type="text"
                        placeholder="Enter Patient ID (e.g., 123456788AC)"
                        className="flex-1 px-3 py-1.5 text-sm border border-yellow-300 rounded focus:ring-1 focus:ring-yellow-500 focus:border-yellow-500"
                        value={manualPatientIds[upload.uuid] || ''}
                        onChange={(e) => setManualPatientIds(prev => ({
                          ...prev,
                          [upload.uuid!]: e.target.value
                        }))}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && manualPatientIds[upload.uuid!]?.trim()) {
                            handleAssignPatientId(upload.uuid!);
                          }
                        }}
                        disabled={assigningPatientId[upload.uuid]}
                      />
                      <button
                        onClick={() => handleAssignPatientId(upload.uuid!)}
                        disabled={!manualPatientIds[upload.uuid]?.trim() || assigningPatientId[upload.uuid]}
                        className="px-4 py-1.5 text-sm font-medium bg-yellow-600 text-white rounded hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                      >
                        {assigningPatientId[upload.uuid] ? (
                          <>
                            <Loader className="w-3 h-3 mr-1 animate-spin" />
                            Assigning...
                          </>
                        ) : (
                          'Assign'
                        )}
                      </button>
                    </div>
                  </div>
                )}
                
                {upload.error && (
                  <div className="mt-2 text-sm text-red-600">{upload.error}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
} 