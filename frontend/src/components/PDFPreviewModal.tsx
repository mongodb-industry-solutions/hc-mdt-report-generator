import React, { useState, useEffect } from 'react';
import { X, Download, Eye, Loader, AlertCircle } from 'lucide-react';
import { Report } from '../types';

interface PDFPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  report: Report;
  onDownload: () => void;
}

export default function PDFPreviewModal({ 
  isOpen, 
  onClose, 
  report, 
  onDownload 
}: PDFPreviewModalProps) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generationProgress, setGenerationProgress] = useState<{
    progress: number;
    currentStep: string;
  }>({ progress: 0, currentStep: '' });

  useEffect(() => {
    if (isOpen && !pdfUrl) {
      generatePreview();
    }
    
    // Cleanup URL when modal closes
    return () => {
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [isOpen]);

  const generatePreview = async () => {
    setIsGenerating(true);
    setError(null);
    setGenerationProgress({ progress: 0, currentStep: 'Initializing...' });
    
    try {
      const { generateMedicalReportPDF } = await import('../services/pdfGenerator');
      
      // Create progress callback
      const progressCallback = (progress: number, step: string) => {
        setGenerationProgress({ progress, currentStep: step });
      };
      
      const pdfBlob = await generateMedicalReportPDF(report, progressCallback);
      const url = URL.createObjectURL(pdfBlob);
      setPdfUrl(url);
      
      setGenerationProgress({ progress: 100, currentStep: 'Preview ready!' });
    } catch (err) {
      console.error('Error generating PDF preview:', err);
      setError('Erreur lors de la génération de l\'aperçu PDF');
    } finally {
      setIsGenerating(false);
      // Reset progress after a short delay
      setTimeout(() => {
        setGenerationProgress({ progress: 0, currentStep: '' });
      }, 1000);
    }
  };

  const handleDownload = () => {
    onDownload();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <Eye className="h-5 w-5 text-navy-700" />
            <h2 className="text-lg font-semibold text-gray-900">
              PDF Report Preview
            </h2>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={handleDownload}
              disabled={!pdfUrl || isGenerating}
              className="flex items-center space-x-2 px-4 py-2 bg-navy-700 text-white rounded-md hover:bg-navy-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Download className="h-4 w-4" />
              <span>Download PDF</span>
            </button>
            <button
              onClick={onClose}
              className="flex items-center justify-center w-8 h-8 rounded-md hover:bg-gray-100 transition-colors"
            >
              <X className="h-5 w-5 text-gray-500" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 flex items-center justify-center p-4">
          {isGenerating ? (
            <div className="flex flex-col items-center space-y-6 w-full max-w-md">
              <Loader className="h-8 w-8 animate-spin text-navy-700" />
              <div className="w-full space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">{generationProgress.currentStep || 'Génération de l\'aperçu PDF...'}</span>
                  <span className="font-medium text-navy-700">{Math.round(generationProgress.progress)}%</span>
                </div>
                
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className="bg-navy-700 h-3 rounded-full transition-all duration-500 ease-out"
                    style={{ width: `${Math.min(generationProgress.progress, 100)}%` }}
                  />
                </div>
                
                <div className="text-xs text-gray-500 text-center">
                  <span className="bg-blue-100 px-2 py-1 rounded text-blue-700">
                    Creating comprehensive summaries with AI
                  </span>
                </div>
              </div>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center space-y-4 text-center">
              <AlertCircle className="h-12 w-12 text-red-500" />
              <div>
                <p className="text-red-600 font-medium">Erreur</p>
                <p className="text-gray-600 text-sm mt-1">{error}</p>
              </div>
              <button
                onClick={generatePreview}
                className="px-4 py-2 bg-navy-700 text-white rounded-md hover:bg-navy-800 transition-colors"
              >
                Réessayer
              </button>
            </div>
          ) : pdfUrl ? (
            <iframe
              src={pdfUrl}
              className="w-full h-full border border-gray-300 rounded-md"
              title="PDF report preview"
            />
          ) : null}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <div>
              <span className="font-medium">Report:</span> {report.title}
            </div>
            <div>
              <span className="font-medium">Patient:</span> {report.patient_id}
            </div>
            <div>
              <span className="font-medium">Créé le:</span>{' '}
              {new Date(report.created_at).toLocaleDateString('fr-FR')}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 