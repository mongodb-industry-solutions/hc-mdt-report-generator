import React, { useState, useEffect } from 'react';
import { X, Download, Eye, Loader, AlertCircle, FileText, Search, ZoomIn, ZoomOut, BookOpen } from 'lucide-react';
import { PatientDocument } from '../types';
import { useI18n } from '../i18n/context';

interface DocumentPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  document: PatientDocument;
  patientId: string;
}

export default function DocumentPreviewModal({ 
  isOpen, 
  onClose, 
  document,
  patientId 
}: DocumentPreviewModalProps) {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<'content' | 'ocr' | 'data'>('content');
  const [searchTerm, setSearchTerm] = useState('');
  const [zoom, setZoom] = useState(100);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [documentContent, setDocumentContent] = useState<string | null>(null);

  // Load document content when modal opens
  useEffect(() => {
    if (isOpen && document) {
      loadDocumentContent();
    }
    return () => {
      setDocumentContent(null);
      setError(null);
    };
  }, [isOpen, document]);

  const loadDocumentContent = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      let content = '';
      
      // Priority 1: OCR text (most likely to be readable)
      if (document.ocr_text && document.ocr_text.trim()) {
        content = document.ocr_text;
        console.log('Using OCR text content');
      }
      // Priority 2: Try to decode file_content if it looks like text
      else if (document.file_content) {
        try {
          // Try to decode as base64 first
          const decoded = atob(document.file_content);
          // Check if it's readable text (not binary)
          if (decoded.length > 0 && /^[\x20-\x7E\s]+$/.test(decoded.substring(0, 1000))) {
            content = decoded;
            console.log('Using decoded file content');
          } else {
            // If not readable, treat file_content as plain text
            content = document.file_content;
            console.log('Using file content as plain text');
          }
        } catch {
          // If base64 decode fails, use as plain text
          content = document.file_content;
          console.log('Using file content as plain text (base64 decode failed)');
        }
      }
      // Priority 3: Show extracted data as JSON if available
      else if (document.extracted_data && Object.keys(document.extracted_data).length > 0) {
        content = 'EXTRACTED MEDICAL DATA:\n\n' + JSON.stringify(document.extracted_data, null, 2);
        console.log('Using extracted data as JSON');
      }
      // Priority 4: Try API fetch as last resort
      else {
        console.log('No local content available, trying API fetch...');
        const { apiService } = await import('../services/api');
        const fullDocument = await apiService.getDocument(patientId, document.uuid);
        
        if (fullDocument.ocr_text) {
          content = fullDocument.ocr_text;
          console.log('Got OCR text from API');
        } else if (fullDocument.file_content) {
          try {
            const decoded = atob(fullDocument.file_content);
            content = decoded;
            console.log('Got and decoded file content from API');
          } catch {
            content = fullDocument.file_content;
            console.log('Got file content from API (no decode)');
          }
        } else if (fullDocument.extracted_data) {
          content = 'EXTRACTED MEDICAL DATA:\n\n' + JSON.stringify(fullDocument.extracted_data, null, 2);
          console.log('Got extracted data from API');
        }
      }
      
      if (content && content.trim()) {
        setDocumentContent(content);
        console.log(`Loaded content: ${content.length} characters`);
      } else {
        setDocumentContent('No readable content found in this document');
        console.log('No content could be extracted');
      }
      
    } catch (err) {
      console.error('Error loading document content:', err);
      
      // Final fallback: show whatever we can find
      let fallbackContent = '';
      if (document.ocr_text) {
        fallbackContent = document.ocr_text;
      } else if (document.extracted_data) {
        fallbackContent = 'EXTRACTED DATA:\n\n' + JSON.stringify(document.extracted_data, null, 2);
      } else {
        fallbackContent = `Document metadata:\nFilename: ${document.filename || 'Unknown'}\nType: ${document.type}\nStatus: ${document.status}\nCreated: ${document.created_at}`;
      }
      
      setDocumentContent(fallbackContent);
      setError(null); // Clear error since we have fallback content
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = async () => {
    try {
      let content = document.file_content || documentContent;
      
      // If we don't have content yet, try to fetch it
      if (!content) {
        const { apiService } = await import('../services/api');
        const fullDocument = await apiService.getDocument(patientId, document.uuid);
        content = fullDocument.file_content || fullDocument.ocr_text || null;
      }
      
      if (!content) {
        alert('No content available for download');
        return;
      }

      let blob: Blob;
      const filename = document.filename || `document-${document.uuid.slice(0, 8)}.txt`;
      
      if (document.file_content) {
        // If it's base64, decode it for download
        try {
          const binaryString = atob(document.file_content);
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          blob = new Blob([bytes], { type: 'application/octet-stream' });
        } catch {
          // If not valid base64, treat as text
          blob = new Blob([document.file_content], { type: 'text/plain' });
        }
      } else {
        blob = new Blob([content], { type: 'text/plain' });
      }

      const url = URL.createObjectURL(blob);
      const link = window.document.createElement('a');
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error downloading document:', err);
      alert('Download failed. Please try again.');
    }
  };

  const getContentForDisplay = () => {
    let content = '';
    
    if (activeTab === 'ocr') {
      content = document.ocr_text || 'No OCR text available';
    } else if (activeTab === 'data') {
      if (document.extracted_data && Object.keys(document.extracted_data).length > 0) {
        content = JSON.stringify(document.extracted_data, null, 2);
      } else {
        content = 'No extracted data available';
      }
    } else {
      // Content tab
      content = documentContent || document.ocr_text || 'No content available';
    }
    
    if (!content || content.trim() === '') {
      return 'No content available for this view';
    }
    
    // Truncate very long content for performance
    const maxLength = 50000;
    let displayContent = content.length > maxLength 
      ? content.substring(0, maxLength) + '\n\n[Content truncated for performance...]'
      : content;
    
    // Simple text highlighting without React elements
    if (searchTerm && searchTerm.trim()) {
      const regex = new RegExp(`(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
      displayContent = displayContent.replace(regex, '<mark style="background-color: #fef08a;">$1</mark>');
    }
    
    return displayContent;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-7xl h-[95vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center space-x-3">
            <Eye className="h-5 w-5 text-blue-600" />
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {document.filename || `Document ${document.uuid.slice(0, 8)}`}
              </h2>
              <p className="text-sm text-gray-500">
                {t.documents.preview.patientId || 'Patient ID'}: {patientId} • 
                {t.documents.preview.type || 'Type'}: {document.type.replace('_', ' ')} • 
                {t.documents.preview.status || 'Status'}: {document.status}
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={handleDownload}
              disabled={!documentContent && !document.file_content}
              className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
            >
              <Download className="h-4 w-4" />
              <span>{t.documents.preview.download || 'Download'}</span>
            </button>
            
            <button
              onClick={onClose}
              className="flex items-center justify-center w-8 h-8 rounded-md hover:bg-gray-100 transition-colors"
            >
              <X className="h-5 w-5 text-gray-500" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50">
          <div className="flex space-x-1">
            <button
              onClick={() => setActiveTab('content')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'content'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              <FileText className="h-4 w-4 inline mr-1" />
              {t.documents.preview.tabs.content || 'Content'}
            </button>
            
            {document.ocr_text && (
              <button
                onClick={() => setActiveTab('ocr')}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  activeTab === 'ocr'
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <BookOpen className="h-4 w-4 inline mr-1" />
                {t.documents.preview.tabs.ocr || 'OCR Text'}
              </button>
            )}
            
            {/* Always show data tab */}
            <button
              onClick={() => setActiveTab('data')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                activeTab === 'data'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              <Search className="h-4 w-4 inline mr-1" />
              {t.documents.preview.tabs.data || 'Raw Data'}
            </button>
          </div>

          {/* Search and Zoom Controls */}
          {(activeTab === 'content' || activeTab === 'ocr') && (
            <div className="flex items-center space-x-3">
              <div className="relative">
                <Search className="h-4 w-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder={t.documents.preview.search || 'Search...'}
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 pr-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => setZoom(Math.max(50, zoom - 10))}
                  className="p-1.5 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
                  title="Zoom out"
                >
                  <ZoomOut className="h-4 w-4" />
                </button>
                <span className="text-sm text-gray-600 min-w-[3rem] text-center">{zoom}%</span>
                <button
                  onClick={() => setZoom(Math.min(200, zoom + 10))}
                  className="p-1.5 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
                  title="Zoom in"
                >
                  <ZoomIn className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-hidden">
          {isLoading ? (
            <div className="h-full flex items-center justify-center">
              <div className="flex flex-col items-center space-y-4">
                <Loader className="h-8 w-8 animate-spin text-blue-600" />
                <p className="text-gray-600">{t.documents.preview.loading || 'Loading document...'}</p>
              </div>
            </div>
          ) : error ? (
            <div className="h-full flex items-center justify-center">
              <div className="flex flex-col items-center space-y-4 text-center">
                <AlertCircle className="h-12 w-12 text-red-500" />
                <div>
                  <p className="text-red-600 font-medium">{t.documents.preview.error || 'Error'}</p>
                  <p className="text-gray-600 text-sm mt-1">{error}</p>
                </div>
                <button
                  onClick={loadDocumentContent}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  {t.documents.preview.retry || 'Retry'}
                </button>
              </div>
            </div>
          ) : (
            <div className="h-full overflow-auto p-4" style={{ fontSize: `${zoom}%` }}>
              {activeTab === 'content' && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <pre 
                    className="whitespace-pre-wrap font-mono text-sm text-gray-800 leading-relaxed"
                    dangerouslySetInnerHTML={{ 
                      __html: getContentForDisplay()
                    }}
                  />
                </div>
              )}
              
              {activeTab === 'ocr' && (
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="mb-4">
                    <h3 className="text-sm font-medium text-blue-800 mb-1">OCR Extracted Text</h3>
                    <p className="text-xs text-blue-600">
                      {document.character_count || 0} characters, {document.word_count || 0} words
                    </p>
                  </div>
                  <pre 
                    className="whitespace-pre-wrap font-mono text-sm text-gray-800 leading-relaxed"
                    dangerouslySetInnerHTML={{ 
                      __html: getContentForDisplay()
                    }}
                  />
                </div>
              )}
              
              {activeTab === 'data' && (
                <div className="space-y-4">
                  <div className="bg-green-50 rounded-lg p-4">
                    <h3 className="text-sm font-medium text-green-800 mb-3">Document Raw Data</h3>
                    {document.extracted_data && Object.keys(document.extracted_data).length > 0 ? (
                      <div className="space-y-3">
                        <h4 className="text-sm font-semibold text-green-700">Extracted Medical Entities:</h4>
                        <pre className="text-xs text-gray-800 bg-white p-3 rounded border overflow-auto max-h-96">
                          {JSON.stringify(document.extracted_data, null, 2)}
                        </pre>
                      </div>
                    ) : (
                      <div className="text-center py-6">
                        <Search className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                        <p className="text-gray-600 mb-2">No extracted medical entities</p>
                        <p className="text-sm text-gray-500">Document may need processing to extract entities</p>
                      </div>
                    )}
                    
                    {/* Show all available document properties */}
                    <div className="mt-4 pt-4 border-t border-green-200">
                      <h4 className="text-sm font-semibold text-green-700 mb-2">Document Metadata:</h4>
                      <pre className="text-xs text-gray-700 bg-white p-3 rounded border">
{`UUID: ${document.uuid}
Filename: ${document.filename || 'Not specified'}
Type: ${document.type}
Status: ${document.status}
Source: ${document.source || 'Not specified'}
Created: ${new Date(document.created_at).toLocaleString()}
Updated: ${new Date(document.updated_at).toLocaleString()}
Character Count: ${document.character_count || 'Not available'}
Word Count: ${document.word_count || 'Not available'}
Document Category: ${document.document_category || 'Not categorized'}
Extraction Status: ${document.extraction_status || 'Not processed'}`}
                      </pre>
                    </div>
                    
                    {/* Show available text content summary */}
                    <div className="mt-4 pt-4 border-t border-green-200">
                      <h4 className="text-sm font-semibold text-green-700 mb-2">Available Content:</h4>
                      <div className="space-y-2 text-sm">
                        <div className={`flex items-center space-x-2 ${document.ocr_text ? 'text-green-600' : 'text-gray-500'}`}>
                          <span className={`w-2 h-2 rounded-full ${document.ocr_text ? 'bg-green-500' : 'bg-gray-300'}`}></span>
                          <span>OCR Text: {document.ocr_text ? `${document.ocr_text.length} characters` : 'Not available'}</span>
                        </div>
                        <div className={`flex items-center space-x-2 ${document.file_content ? 'text-green-600' : 'text-gray-500'}`}>
                          <span className={`w-2 h-2 rounded-full ${document.file_content ? 'bg-green-500' : 'bg-gray-300'}`}></span>
                          <span>File Content: {document.file_content ? `${document.file_content.length} characters` : 'Not available'}</span>
                        </div>
                        <div className={`flex items-center space-x-2 ${document.extracted_data && Object.keys(document.extracted_data).length > 0 ? 'text-green-600' : 'text-gray-500'}`}>
                          <span className={`w-2 h-2 rounded-full ${document.extracted_data && Object.keys(document.extracted_data).length > 0 ? 'bg-green-500' : 'bg-gray-300'}`}></span>
                          <span>Extracted Entities: {document.extracted_data ? Object.keys(document.extracted_data).length : 0}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between text-xs text-gray-600">
            <div className="flex space-x-6">
              <span><strong>UUID:</strong> {document.uuid}</span>
              <span><strong>Created:</strong> {new Date(document.created_at).toLocaleString()}</span>
              {document.processing_completed_at && (
                <span><strong>Processed:</strong> {new Date(document.processing_completed_at).toLocaleString()}</span>
              )}
            </div>
            <div>
              {document.document_category && (
                <span><strong>Category:</strong> {document.document_category}</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}