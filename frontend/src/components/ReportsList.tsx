import React, { useState, useEffect } from 'react';
import { BarChart3, Plus, Eye, Download, Calendar, Clock, CheckCircle, AlertCircle, Loader, X, Trash2, FileText, Settings } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { apiService } from '../services/api';
import { Report, ReportGenerationProgress } from '../types';
import ReportGenerationDialog, { ReportGenerationSettings } from './ReportGenerationDialog';
import TemplateConfiguration from './TemplateConfiguration';
import { useI18n } from '../i18n/context';

interface ReportsListProps {
  reports: Report[];
  patientId: string;
  onReportGenerated: (report: Report) => void;
  onViewReport: (report: Report) => void;
  isGenerating?: boolean;
  generationProgress?: ReportGenerationProgress | null;
  onGenerationStart?: () => void;
  onGenerationProgress?: (progress: ReportGenerationProgress) => void;
  onGenerationComplete?: () => void;
  onGenerationError?: () => void;
  onRefreshReports?: () => void;
}

const getStatusIcon = (status: Report['status']) => {
  switch (status) {
    case 'COMPLETED':
      return <CheckCircle className="w-4 h-4 text-green-600" />;
    case 'FAILED':
      return <AlertCircle className="w-4 h-4 text-red-600" />;
    default:
      return <Loader className="w-4 h-4 text-blue-600 animate-spin" />;
  }
};

const getStatusBadgeClass = (status: Report['status']) => {
  switch (status) {
    case 'COMPLETED':
      return 'status-done';
    case 'FAILED':
      return 'status-failed';
    default:
      return 'status-processing';
  }
};

export default function ReportsList({ 
  reports, 
  patientId, 
  onReportGenerated, 
  onViewReport,
  isGenerating = false,
  generationProgress = null,
  onGenerationStart,
  onGenerationProgress,
  onGenerationComplete,
  onGenerationError,
  onRefreshReports
}: ReportsListProps) {
  const { t } = useI18n();
  const [showGenerationDialog, setShowGenerationDialog] = useState(false);
  const [showSuccessMessage, setShowSuccessMessage] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);
  
  // PDF generation progress state
  const [pdfGenerationProgress, setPdfGenerationProgress] = useState<{
    isGenerating: boolean;
    progress: number;
    currentStep: string;
    reportId?: string;
  }>({ isGenerating: false, progress: 0, currentStep: '' });
  
  // Ensure reverse chronological order (newest first)
  const sortedReports = React.useMemo(() => {
    return [...reports].sort((a, b) => 
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }, [reports]);

  React.useEffect(() => {
    console.log('🎯 Progress State:', generationProgress?.progress + '%' || 'null');
  }, [generationProgress]);

  const getStatusText = (status: Report['status']) => {
    switch (status) {
      case 'COMPLETED':
        return t.reports.status.completed;
      case 'FAILED':
        return t.reports.status.failed;
      default:
        return t.reports.status.processing;
    }
  };

  const formatElapsed = (ms: number) => {
    if (!ms || ms < 0) return null;
    const totalSeconds = Math.floor(ms / 1000);
    const h = Math.floor(totalSeconds / 3600);
    const m = Math.floor((totalSeconds % 3600) / 60);
    const s = totalSeconds % 60;
    if (h > 0) return `${h}h ${m}m ${s}s`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  };

  const handleGenerateReport = async (settings: ReportGenerationSettings) => {
    if (isGenerating) return;

    onGenerationStart?.();
    setShowSuccessMessage(false);
    setGenerationError(null);

    let isCompleted = false; // Flag to prevent race condition with late progress updates

    try {
      const reportTitle = settings.customTitle?.trim() || undefined;
      let completedReportUuid: string | null = null;
      
      // Use streaming API for progress updates
      await apiService.generateReportWithProgress(
        patientId,
        reportTitle,
        (progressData: ReportGenerationProgress) => {
          console.log('📊 Progress:', progressData.progress + '%', '-', progressData.status, '-', progressData.message);
          
          // Only update progress if generation hasn't completed yet
          if (!isCompleted) {
            onGenerationProgress?.(progressData);
          }
          
          // Capture the report UUID when generation completes
          if (progressData.status === 'COMPLETED' && (progressData as any).report_uuid) {
            completedReportUuid = (progressData as any).report_uuid;
            isCompleted = true; // Mark as completed to prevent further updates
          }
        },
        undefined,
        settings.nerConfig
      );

      // Ensure completion flag is set after API call finishes
      isCompleted = true;

      // Generation completed, fetch the specific report by UUID
      if (completedReportUuid) {
        try {
          const report = await apiService.getReport(patientId, completedReportUuid);
          onReportGenerated(report);
        } catch (error) {
          console.error('Failed to fetch specific report:', error);
          // Fallback to getting all reports if specific fetch fails
          const reportsResponse = await apiService.getPatientReports(patientId);
          const latestReport = reportsResponse.items[0];
          if (latestReport) {
            onReportGenerated(latestReport);
          }
        }
      } else {
        // Fallback if no UUID was captured
        console.warn('No report UUID captured from completion status, falling back to latest report');
        const reportsResponse = await apiService.getPatientReports(patientId);
        const latestReport = reportsResponse.items[0];
        if (latestReport) {
          onReportGenerated(latestReport);
        }
      }
      
      onGenerationComplete?.();
      setShowSuccessMessage(true);

    } catch (error: any) {
      console.error('Failed to generate report:', error);
      
      // Extract meaningful error message
      let errorMessage = 'Report generation failed. Please try again.';
      
      if (error.details?.error_type === 'unauthorized') {
        errorMessage = 'API authentication failed. Please check your configuration and try again.';
      } else if (error.details?.error_type === 'service_unavailable') {
        errorMessage = 'AI service is currently unavailable. Please check your API key configuration.';
      } else if (error.details?.message) {
        errorMessage = error.details.message;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      setGenerationError(errorMessage);
      onGenerationError?.();
    }
  };

  // Auto-hide success message after 5 seconds
  useEffect(() => {
    if (showSuccessMessage) {
      const timer = setTimeout(() => {
        setShowSuccessMessage(false);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [showSuccessMessage]);

  // Auto-hide error message after 10 seconds
  useEffect(() => {
    if (generationError) {
      const timer = setTimeout(() => {
        setGenerationError(null);
      }, 10000);
      return () => clearTimeout(timer);
    }
  }, [generationError]);



  const handleDownloadPDF = async (report: Report) => {
    try {
      console.log('🔄 Starting PDF download for report:', report.uuid, 'patient:', report.patient_id);
      
      // Set initial progress
      setPdfGenerationProgress({
        isGenerating: true,
        progress: 0,
        currentStep: 'Initializing PDF generation...',
        reportId: report.uuid
      });
      
      // Test simple PDF generation first
      console.log('🧪 Testing simple PDF generation...');
      setPdfGenerationProgress(prev => ({ ...prev, progress: 10, currentStep: 'Testing PDF engine...' }));
      
      const { generateSimpleTestPDF } = await import('../services/testPDF');
      const simplePdfBlob = await generateSimpleTestPDF();
      console.log('✅ Simple PDF generation successful, blob size:', simplePdfBlob.size);
      
      const filename = `${report.filename.replace('.json', '')}.pdf`;
      
      // Import the PDF generator with progress tracking
      console.log('🔄 Generating full medical report PDF...');
      setPdfGenerationProgress(prev => ({ ...prev, progress: 15, currentStep: 'Loading template configuration...' }));
      
      // Get active template for PDF generation
      let activeTemplate = null;
      try {
        const { template } = await apiService.getActiveTemplate();
        activeTemplate = template;
        console.log('✅ Active template loaded for PDF generation');
      } catch (templateError) {
        console.warn('Could not fetch active template for PDF generation:', templateError);
      }
      
      setPdfGenerationProgress(prev => ({ ...prev, progress: 20, currentStep: 'Loading PDF generator...' }));
      
      const { generateMedicalReportPDF } = await import('../services/pdfGenerator');
      
      // Create progress callback for PDF generation
      const progressCallback = (progress: number, step: string) => {
        setPdfGenerationProgress(prev => ({ 
          ...prev, 
          progress: Math.min(20 + (progress * 0.7), 90), // Scale 0-100 to 20-90
          currentStep: step 
        }));
      };
      
      setPdfGenerationProgress(prev => ({ ...prev, progress: 25, currentStep: 'Generating comprehensive summaries...' }));
      const pdfBlob = await generateMedicalReportPDF(report, activeTemplate, progressCallback);
      console.log('✅ Medical PDF generation successful, blob size:', pdfBlob.size);
      
      setPdfGenerationProgress(prev => ({ ...prev, progress: 95, currentStep: 'Preparing download...' }));
      
      // Create download link
      const url = URL.createObjectURL(pdfBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      setPdfGenerationProgress(prev => ({ ...prev, progress: 100, currentStep: 'Download completed!' }));
      
      // Reset progress after a short delay
      setTimeout(() => {
        setPdfGenerationProgress({ isGenerating: false, progress: 0, currentStep: '' });
      }, 2000);
      
      console.log('✅ PDF download completed');
    } catch (error: any) {
      console.error('❌ Error generating PDF:', error);
      console.error('Error stack:', error.stack);
      setPdfGenerationProgress(prev => ({ ...prev, currentStep: `Error: ${error.message}` }));
      
      setTimeout(() => {
        setPdfGenerationProgress({ isGenerating: false, progress: 0, currentStep: '' });
      }, 3000);
      
      alert(`PDF Generation Error: ${error.message}`);
    }
  };

  const getEntitiesCount = (report: Report): number => {
    if (!report.content) return 0;
    
    const isFound = (e: any): boolean => {
      const status = e?.metadata?.status;
      if (status === 'not_found') return false;
      const val = (e.value ?? e.entity_value ?? '').toString().trim();
      const hasValues = Array.isArray(e.values) && e.values.length > 0;
      const hasAgg = typeof e.aggregated_value === 'string' && e.aggregated_value.trim().length > 0;
      return val.length > 0 || hasValues || hasAgg;
    };
    
    // Check for new structure first (ner_results.entities)
    if (Array.isArray(report.content.ner_results?.entities)) {
      return report.content.ner_results.entities.filter(isFound).length;
    }
    
    // Fallback to old structure for backward compatibility
    let total = 0;
    const add = (arr?: any[]) => { if (Array.isArray(arr)) total += arr.filter(isFound).length; };
    add(report.content.first_match?.found_entities);
    add(report.content.multiple_match?.found_entities);
    add(report.content.aggregate_all_matches?.found_entities);
    
    return total;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{t.reports.title}</h2>
          <p className="text-gray-600">
            {reports.length} {t.reports.reportsFor} {patientId}
          </p>
        </div>
        
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowGenerationDialog(true)}
            className="btn-primary flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>{t.reports.generateNew}</span>
          </button>
        </div>
      </div>

      {/* Template Configuration */}
      <TemplateConfiguration />

      {/* Generation Progress */}
      {isGenerating && generationProgress && (
        <div className="card">
          <div className="flex items-center space-x-3 mb-4">
            <Loader className="w-5 h-5 text-navy-700 animate-spin" />
            <h3 className="text-lg font-medium text-gray-900">{t.reports.generation.title}</h3>
          </div>
          
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">{generationProgress.message || 'Generating report...'}</span>
              <span className="font-medium">{generationProgress.progress || 0}%</span>
            </div>
            
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-navy-700 h-2 rounded-full transition-all duration-300"
                style={{ width: `${Math.min(generationProgress.progress || 0, 100)}%` }}
              />
            </div>
            
            <div className="text-xs text-gray-500">
              Step: {generationProgress.current_step?.replace('_', ' ') || 'Processing...'}
              {generationProgress.entities_extracted && (
                <span className="ml-3">
                  Entities extracted: {generationProgress.entities_extracted}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* PDF Generation Progress */}
      {pdfGenerationProgress.isGenerating && (
        <div className="card border-blue-200 bg-blue-50">
          <div className="flex items-center space-x-3 mb-4">
            <Loader className="w-5 h-5 text-blue-600 animate-spin" />
            <h3 className="text-lg font-medium text-blue-900">Generating PDF Report</h3>
          </div>
          
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-blue-700">{pdfGenerationProgress.currentStep}</span>
              <span className="font-medium text-blue-800">{Math.round(pdfGenerationProgress.progress)}%</span>
            </div>
            
            <div className="w-full bg-blue-200 rounded-full h-3">
              <div
                className="bg-blue-600 h-3 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${Math.min(pdfGenerationProgress.progress, 100)}%` }}
              />
            </div>
            
            <div className="text-xs text-blue-600">
              <div className="flex items-center justify-between">
                <span>Creating comprehensive medical summaries with AI...</span>
                <span className="bg-blue-100 px-2 py-1 rounded text-blue-700 font-medium">
                  Processing
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Generation Error */}
      {generationError && (
        <div className="card border-red-200 bg-red-50">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <svg className="w-5 h-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-medium text-red-800">Report Generation Failed</h3>
              <div className="mt-1 text-sm text-red-700">
                {generationError}
              </div>
              <div className="mt-3">
                <button
                  onClick={() => setGenerationError(null)}
                  className="text-sm text-red-600 hover:text-red-500 font-medium"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reports List */}
      {reports.length === 0 ? (
        <div className="card text-center py-12">
          <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">{t.reports.empty.title}</h3>
          <p className="text-gray-500 mb-4">
            {t.reports.empty.description}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {sortedReports.map((report) => (
            <div key={report.uuid} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <BarChart3 className="w-5 h-5 text-gray-500" />
                    <h3 className="text-lg font-medium text-gray-900">
                      {report.title}
                    </h3>
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(report.status)}
                      <span className={getStatusBadgeClass(report.status)}>
                        {getStatusText(report.status)}
                      </span>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm text-gray-600">
                    <div>
                      <span className="font-medium">{t.reports.info.entities}:</span>{' '}
                      {getEntitiesCount(report)} {t.reports.info.extracted}
                    </div>
                    <div>
                      <span className="font-medium">{t.reports.info.documents}:</span>{' '}
                      {report.metadata?.total_documents_processed || 0} {t.reports.info.processed}
                    </div>
                    <div>
                      <span className="font-medium">{t.reports.info.size}:</span>{' '}
                      {(report.file_size / 1024).toFixed(1)} KB
                    </div>
                    <div>
                      <span className="font-medium">{t.reports.info.version}:</span>{' '}
                      {report.metadata?.report_version || 'N/A'}
                    </div>
                  </div>

                  <div className="flex items-center space-x-4 mt-3 text-sm text-gray-500">
                    <div className="flex items-center space-x-1">
                      <Calendar className="w-4 h-4" />
                      <span>{t.reports.info.generatedAgo} {formatDistanceToNow(new Date(report.created_at), { includeSeconds: true, addSuffix: true })}</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <FileText className="w-4 h-4" />
                      <span>{report.word_count.toLocaleString()} {t.reports.info.words}</span>
                    </div>
                    {report.status === 'COMPLETED' && report.elapsed_seconds != null && (
                      <div className="flex items-center space-x-1">
                        <Clock className="w-4 h-4" />
                        <span>
                          {report.elapsed_seconds < 60 
                            ? `${report.elapsed_seconds.toFixed(1)}s`
                            : `${Math.floor(report.elapsed_seconds / 60)}m ${Math.round(report.elapsed_seconds % 60)}s`
                          }
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-2 ml-4">
                  <button
                    onClick={() => onViewReport(report)}
                    className="btn-success flex items-center space-x-1"
                    disabled={report.status !== 'COMPLETED'}
                  >
                    <Eye className="w-4 h-4" />
                    <span>{t.reports.info.view}</span>
                  </button>
                  
                  <button
                    onClick={() => handleDownloadPDF(report)}
                    className="btn-secondary flex items-center space-x-1 disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={report.status !== 'COMPLETED' || (pdfGenerationProgress.isGenerating && pdfGenerationProgress.reportId === report.uuid)}
                  >
                    <Download className="w-4 h-4" />
                    <span>{t.reports.info.download}</span>
                    {pdfGenerationProgress.isGenerating && pdfGenerationProgress.reportId === report.uuid && (
                      <Loader className="w-3 h-3 animate-spin text-blue-500 ml-1" />
                    )}
                  </button>
                  <button
                    onClick={async () => {
                      if (!window.confirm('Delete this report permanently?')) return;
                      await apiService.deleteReport(patientId, report.uuid);
                      onRefreshReports && onRefreshReports();
                    }}
                    title="Delete report"
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

      {/* Success Toast Notification */}
      {showSuccessMessage && (
        <div className="fixed top-4 right-4 z-50 animate-slide-in-right">
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 shadow-lg max-w-sm">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <CheckCircle className="w-5 h-5 text-green-600" />
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-green-800">
                  Report Generated Successfully
                </p>
                <p className="text-xs text-green-600 mt-1">
                  Your MDT report has been created and is ready to view.
                </p>
              </div>
              <div className="ml-4 flex-shrink-0">
                <button
                  onClick={() => setShowSuccessMessage(false)}
                  className="text-green-600 hover:text-green-800 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Report Generation Dialog */}
      {showGenerationDialog && (
        <ReportGenerationDialog
          isOpen={showGenerationDialog}
          onClose={() => setShowGenerationDialog(false)}
          onGenerate={handleGenerateReport}
          isGenerating={isGenerating}
          patientId={patientId}
        />
      )}
    </div>
  );
} 