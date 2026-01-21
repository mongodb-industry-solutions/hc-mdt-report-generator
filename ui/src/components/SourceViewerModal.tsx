import React, { useState, useEffect } from 'react';
import { X, Download, Eye, Loader, AlertCircle, FileText, File } from 'lucide-react';
import { PatientDocument } from '../types';

interface SourceViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  patientId: string;
  filename: string;
}

export default function SourceViewerModal({ 
  isOpen, 
  onClose, 
  patientId, 
  filename 
}: SourceViewerModalProps) {
  const [document, setDocument] = useState<PatientDocument | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && filename) {
      loadDocument();
    }
    
    // Cleanup URL when modal closes
    return () => {
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [isOpen, filename, patientId]);

  const loadDocument = async () => {
    setIsLoading(true);
    setError(null);
    setDocument(null);
    
    try {
      const { apiService } = await import('../services/api');
      const doc = await apiService.getDocumentByFilename(patientId, filename);
      setDocument(doc);
      
      // If it's a PDF and has base64 content, create blob URL
      if (isPDF(filename) && doc.file_content) {
        try {
          const binaryString = atob(doc.file_content);
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          const blob = new Blob([bytes], { type: 'application/pdf' });
          const url = URL.createObjectURL(blob);
          setPdfUrl(url);
        } catch (err) {
          console.error('Error creating PDF blob:', err);
          setError('Error loading PDF preview');
        }
      }
    } catch (err) {
      console.error('Error loading document:', err);
      setError('Failed to load document');
    } finally {
      setIsLoading(false);
    }
  };

  const isPDF = (filename: string): boolean => {
    return filename.toLowerCase().endsWith('.pdf');
  };

  const getFileExtension = (filename: string): string => {
    return filename.split('.').pop()?.toLowerCase() || '';
  };

  const isJSON = (filename: string): boolean => {
    return filename.toLowerCase().endsWith('.json');
  };

  const isXML = (filename: string): boolean => {
    const ext = filename.toLowerCase();
    return ext.endsWith('.xml') || ext.endsWith('.cda');
  };

  const formatJSON = (text: string): string => {
    try {
      const parsed = JSON.parse(text);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return text; // Return original if parsing fails
    }
  };

  const formatXMLForDisplay = (xmlText: string): string => {
    try {
      // Simple XML formatting that preserves actual content
      let formatted = xmlText;
      
      // First, let's handle CDATA sections by extracting and formatting their content
      formatted = formatted.replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, (match, content) => {
        // Clean up HTML inside CDATA but preserve the text content
        let cleanContent = content
          .replace(/<br\s*\/?>/gi, '\n')
          .replace(/<\/p>/gi, '\n')
          .replace(/<p[^>]*>/gi, '\n')
          .replace(/<b>(.*?)<\/b>/gi, '**$1**')
          .replace(/<strong>(.*?)<\/strong>/gi, '**$1**')
          .replace(/<i>(.*?)<\/i>/gi, '_$1_')
          .replace(/<em>(.*?)<\/em>/gi, '_$1_')
          .replace(/<h[1-6][^>]*>(.*?)<\/h[1-6]>/gi, '\n### $1\n')
          .replace(/&nbsp;/g, ' ')
          .replace(/&amp;/g, '&')
          .replace(/&lt;/g, '<')
          .replace(/&gt;/g, '>')
          .replace(/&quot;/g, '"')
          .replace(/<[^>]*>/g, '') // Remove remaining HTML tags
          .replace(/\s+/g, ' ') // Normalize whitespace
          .trim();
        
        return `\n--- Document Content ---\n${cleanContent}\n--- End Content ---\n`;
      });
      
      // Add some basic XML formatting for readability
      formatted = formatted
        .replace(/></g, '>\n<') // Add line breaks between tags
        .replace(/^\s*</gm, '<') // Remove leading whitespace before tags
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0)
        .join('\n');
      
      // Add indentation for better readability
      const lines = formatted.split('\n');
      let indentLevel = 0;
      const indentedLines = [];
      
      for (const line of lines) {
        if (line.startsWith('</')) {
          indentLevel = Math.max(0, indentLevel - 1);
        }
        
        if (line.includes('--- Document Content ---') || line.includes('--- End Content ---')) {
          indentedLines.push(line); // Don't indent content markers
        } else if (line.startsWith('<') && !line.startsWith('<!')) {
          indentedLines.push('  '.repeat(indentLevel) + line);
          if (!line.includes('</') && !line.endsWith('/>')) {
            indentLevel++;
          }
        } else {
          // This is text content, preserve it
          indentedLines.push(line);
        }
      }
      
      return indentedLines.join('\n');
    } catch (error) {
      console.warn('XML formatting failed, returning original:', error);
      return xmlText; // Return original if formatting fails
    }
  };

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <Loader className="h-8 w-8 animate-spin text-medical-600" />
          <p className="text-gray-600">Loading document...</p>
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex flex-col items-center justify-center h-64 space-y-4 text-center">
          <AlertCircle className="h-12 w-12 text-red-500" />
          <div>
            <p className="text-red-600 font-medium">Error</p>
            <p className="text-gray-600 text-sm mt-1">{error}</p>
          </div>
          <button
            onClick={loadDocument}
            className="px-4 py-2 bg-medical-600 text-white rounded-md hover:bg-medical-700 transition-colors"
          >
            Retry
          </button>
        </div>
      );
    }

    if (!document) {
      return (
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <FileText className="h-12 w-12 text-gray-400" />
          <p className="text-gray-500">No document found</p>
        </div>
      );
    }

    // PDF Preview
    if (isPDF(filename) && pdfUrl) {
      return (
        <iframe
          src={pdfUrl}
          className="w-full h-full border border-gray-300 rounded-md"
          title={`PDF Preview: ${filename}`}
        />
      );
    }

    // Text Content (for non-PDF files or PDFs without file_content)
    let textContent = document.file_content ? 
      (isPDF(filename) ? 'PDF content not available for text preview' : 
       document.ocr_text || 'Text content not available') :
      document.ocr_text || 'Content not available';

    // Special handling for XML files
    if (isXML(filename) && textContent !== 'Content not available' && textContent !== 'Text content not available') {
      textContent = formatXMLForDisplay(textContent);
    }

    // Apply JSON formatting
    if (isJSON(filename) && textContent !== 'Content not available' && textContent !== 'Text content not available') {
      textContent = formatJSON(textContent);
    }

    // Determine syntax highlighting class
    const getSyntaxClass = () => {
      if (isJSON(filename)) return 'language-json';
      return '';
    };

    return (
      <div className="w-full h-full bg-gray-50 border border-gray-300 rounded-md overflow-hidden">
        <div className="w-full h-full overflow-auto p-4">
          <pre className={`text-sm text-gray-800 whitespace-pre-wrap break-words font-mono ${getSyntaxClass()}`}>
            {textContent}
          </pre>
        </div>
      </div>
    );
  };

  if (!isOpen) return null;

  const fileExt = getFileExtension(filename).toUpperCase();
  const Icon = isPDF(filename) ? FileText : File;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <Icon className="h-5 w-5 text-medical-600" />
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Source Document Viewer
              </h2>
              <p className="text-sm text-gray-500">{filename}</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {document && (
              <>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                  isJSON(filename) ? 'bg-green-100 text-green-800' :
                  isXML(filename) ? 'bg-purple-100 text-purple-800' :
                  isPDF(filename) ? 'bg-red-100 text-red-800' :
                  'bg-blue-100 text-blue-800'
                }`}>
                  {fileExt}
                </span>
                <span className="px-3 py-1 bg-gray-100 text-gray-800 rounded-full text-xs">
                  {document.type}
                </span>
                {(isJSON(filename) || isXML(filename)) && (
                  <span className="px-3 py-1 bg-indigo-100 text-indigo-800 rounded-full text-xs font-medium">
                    Formatted
                  </span>
                )}
              </>
            )}
            <button
              onClick={onClose}
              className="flex items-center justify-center w-8 h-8 rounded-md hover:bg-gray-100 transition-colors"
            >
              <X className="h-5 w-5 text-gray-500" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 p-4 min-h-0">
          {renderContent()}
        </div>

        {/* Footer */}
        {document && (
          <div className="p-4 border-t border-gray-200 bg-gray-50">
            <div className="flex items-center justify-between text-sm text-gray-600">
              <div className="flex items-center space-x-6">
                <div>
                  <span className="font-medium">Patient:</span> {document.patient_id}
                </div>
                <div>
                  <span className="font-medium">Type:</span> {document.type}
                </div>
                {document.source && (
                  <div>
                    <span className="font-medium">Source:</span> {document.source}
                  </div>
                )}
              </div>
              <div>
                <span className="font-medium">Uploaded:</span>{' '}
                {new Date(document.created_at).toLocaleDateString('fr-FR')}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 