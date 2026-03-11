import React, { useState, useEffect } from 'react';
import { X, FileText, Download, ExternalLink, AlertCircle } from 'lucide-react';
import { useI18n } from '../i18n/context';

interface GTViewerProps {
  patientId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function GTViewer({ patientId, isOpen, onClose }: GTViewerProps) {
  const { t } = useI18n();
  const [pdfUrl, setPdfUrl] = useState<string>('');
  const [pdfExists, setPdfExists] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [showInfoBanner, setShowInfoBanner] = useState<boolean>(true);

  useEffect(() => {
    if (isOpen && patientId) {
      checkAndLoadPDF();
      setShowInfoBanner(true); // Reset banner when opening
    }
  }, [isOpen, patientId]);

  // Auto-hide info banner after 10 seconds
  useEffect(() => {
    if (showInfoBanner && isOpen) {
      const timer = setTimeout(() => {
        setShowInfoBanner(false);
      }, 10000);
      
      return () => clearTimeout(timer);
    }
  }, [showInfoBanner, isOpen]);

  const checkAndLoadPDF = async () => {
    setLoading(true);
    
    try {
      const gtFileName = `GT_${patientId}.pdf`;
      const gtUrl = `/gt/${gtFileName}`;
      
      // Check if PDF exists by making a HEAD request
      const response = await fetch(gtUrl, { method: 'HEAD' });
      
      if (response.ok) {
        setPdfUrl(gtUrl);
        setPdfExists(true);
      } else {
        setPdfExists(false);
      }
    } catch (error) {
      console.error('Error checking GT PDF:', error);
      setPdfExists(false);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (pdfUrl) {
      const link = document.createElement('a');
      link.href = pdfUrl;
      link.download = `GT_${patientId}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const handleOpenInNewTab = () => {
    if (pdfUrl) {
      window.open(pdfUrl, '_blank');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 z-50">
      <div className="bg-white w-full h-full flex flex-col">
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white shrink-0">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600" />
            <h2 className="text-lg font-semibold text-gray-900">
              Ground Truth Viewer - Patient {patientId}
            </h2>
          </div>
          
          <div className="flex items-center gap-2">
            {pdfExists && (
              <>
                <button
                  onClick={handleDownload}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded transition-colors"
                  title="Download PDF"
                >
                  <Download className="w-4 h-4" />
                  Download
                </button>
                
                <button
                  onClick={handleOpenInNewTab}
                  className="flex items-center gap-1 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded transition-colors"
                  title="Open in new tab"
                >
                  <ExternalLink className="w-4 h-4" />
                  New Tab
                </button>
              </>
            )}
            
            <button
              onClick={onClose}
              className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Info Banner */}
        {showInfoBanner && (
          <div className="bg-gradient-to-r from-amber-100 to-orange-100 border-b border-amber-200 px-4 py-3 relative">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
                <p className="text-sm text-amber-800 font-medium">
                  <strong>Demo Notice:</strong> This Ground Truth Document has been generated specifically for this use case and for demonstration purposes only. 
                  It should not be used for actual medical decisions or patient care.
                </p>
              </div>
              <button
                onClick={() => setShowInfoBanner(false)}
                className="p-1 text-amber-600 hover:text-amber-800 rounded transition-colors flex-shrink-0 ml-4"
                title="Dismiss notice"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            
            {/* Auto-hide progress indicator */}
            <div 
              className="absolute bottom-0 left-0 h-1 bg-amber-300 rounded-full"
              style={{
                width: '100%',
                animation: 'shrinkWidth 10s linear forwards'
              }}
            ></div>
            
            <style jsx>{`
              @keyframes shrinkWidth {
                from { width: 100%; }
                to { width: 0%; }
              }
            `}</style>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-hidden bg-gray-100 min-h-0">
          {loading ? (
            <div className="flex items-center justify-center h-full bg-white">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Loading GT document...</p>
              </div>
            </div>
          ) : !pdfExists ? (
            <div className="flex items-center justify-center h-full bg-white">
              <div className="text-center max-w-md">
                <AlertCircle className="w-16 h-16 text-yellow-500 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Ground Truth Document Not Found
                </h3>
                <p className="text-gray-600 mb-4">
                  No ground truth PDF found for patient <strong>{patientId}</strong>.
                </p>
                <p className="text-sm text-gray-500">
                  Expected file: <code>GT_{patientId}.pdf</code>
                </p>
              </div>
            </div>
          ) : (
            <div className="w-full h-full flex flex-col">
              {/* PDF Viewer using browser's built-in PDF viewer */}
              <iframe
                src={pdfUrl}
                className="w-full flex-1 border-0"
                title={`Ground Truth PDF for Patient ${patientId}`}
                onError={() => {
                  console.error('Error loading PDF in iframe');
                  setPdfExists(false);
                }}
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-2 border-t border-gray-200 bg-gray-50 text-xs text-gray-500 text-center shrink-0">
          GT Viewer • {pdfExists ? `Viewing GT_${patientId}.pdf` : 'Document not available'} • Press ESC to close
        </div>
      </div>
    </div>
  );
}

export default GTViewer;