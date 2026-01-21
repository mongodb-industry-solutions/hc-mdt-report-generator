import React, { useState, useEffect } from 'react';
import { FileText, User, BarChart3, Settings, X, MessageCircle, Bot, Database, Eye, Users } from 'lucide-react';
import PatientSelector from './components/PatientSelector';
import DocumentsList from './components/DocumentsList';
import ReportsList from './components/ReportsList';
import ReportViewer from './components/ReportViewer';
import SettingsPanel from './components/SettingsPanel';
import Observability from './components/Observability';
import LanguageSwitcher from './components/LanguageSwitcher';
import IntelligentAssistant from './components/IntelligentAssistant';
import PatientsDialog from './components/PatientsDialog';
import DisclaimerModal from './components/DisclaimerModal';
import { I18nProvider, useI18n } from './i18n/context';
import { apiService, getApiBaseURL } from './services/api';
import { PatientDocument, Report, ReportGenerationProgress } from './types';

function AppContent() {
  const { t } = useI18n();
  const [currentView, setCurrentView] = useState<'documents' | 'reports' | 'assistant' | 'observability'>('documents');
  const [showPatientsDialog, setShowPatientsDialog] = useState<boolean>(false);
  // Start with empty patient ID - will be extracted from uploaded documents
  // UUID-first architecture: upload first, patient ID is extracted during processing
  const [patientId, setPatientId] = useState<string>('');
  const [apiBaseUrl, setApiBaseUrl] = useState<string>(getApiBaseURL());
  const [documents, setDocuments] = useState<PatientDocument[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [showReportViewer, setShowReportViewer] = useState<boolean>(false);
  const [showSettings, setShowSettings] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [showDisclaimer, setShowDisclaimer] = useState<boolean>(true);
  const [disclaimerAccepted, setDisclaimerAccepted] = useState<boolean>(false);
  
  // Report generation state - moved here to persist across tab switches
  const [isGeneratingReport, setIsGeneratingReport] = useState<boolean>(false);
  const [reportGenerationProgress, setReportGenerationProgress] = useState<ReportGenerationProgress | null>(null);

  // Debug: Track generation state across tab switches
  useEffect(() => {
    if (isGeneratingReport) {
      console.log('🎯 App-level generation state: GENERATING - Progress:', reportGenerationProgress?.progress + '%' || 'null');
    }
  }, [isGeneratingReport, reportGenerationProgress]);

  // Update API base URL when it changes
  useEffect(() => {
    apiService.updateBaseURL(apiBaseUrl);
  }, [apiBaseUrl]);

  // Load data when patient ID changes (only if we have a valid patient ID)
  useEffect(() => {
    if (patientId && patientId.trim()) {
      // Close report viewer when switching patients for privacy/security
      setShowReportViewer(false);
      setSelectedReport(null);
      
      loadPatientData();
    } else {
      // Clear data when no patient ID
      setDocuments([]);
      setReports([]);
    }
  }, [patientId]);

  // Auto-refresh reports when switching to reports tab + first-time settings popup
  useEffect(() => {
    if (currentView === 'reports' && patientId) {
      // Refresh only the reports data when switching to reports tab
      refreshReports();

      // Show Settings on first visit to Reports in this browser tab
      try {
        const openedKey = 'claritygr:settings_opened';
        if (!sessionStorage.getItem(openedKey)) {
          setShowSettings(true);
          sessionStorage.setItem(openedKey, 'true');
        }
      } catch (e) {
        // Ignore sessionStorage errors (e.g., privacy mode)
      }
    }
  }, [currentView, patientId]);

  // Mark settings as opened in this browser tab whenever it is shown
  useEffect(() => {
    if (showSettings) {
      try {
        sessionStorage.setItem('claritygr:settings_opened', 'true');
      } catch (e) {
        // Ignore sessionStorage errors
      }
    }
  }, [showSettings]);

  const loadPatientData = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Load documents and reports in parallel
      const [documentsResponse, reportsResponse] = await Promise.all([
        apiService.getPatientDocuments(patientId),
        apiService.getPatientReports(patientId)
      ]);
      
      setDocuments(documentsResponse.items);
      
      // Sort reports by created_at in descending order (most recent first)
      const sortedReports = reportsResponse.items.sort((a, b) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      setReports(sortedReports);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load patient data');
      console.error('Error loading patient data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDocumentUploaded = (document: PatientDocument) => {
    setDocuments(prev => [document, ...prev]);
  };

  const handleDocumentStatusUpdate = (updatedDocument: PatientDocument) => {
    setDocuments(prev => prev.map(doc => 
      doc.uuid === updatedDocument.uuid ? updatedDocument : doc
    ));
  };

  const handleReportGenerated = (report: Report) => {
    setReports(prev => {
      // Check if report already exists
      const existingIndex = prev.findIndex(r => r.uuid === report.uuid);
      
      let updatedReports;
      if (existingIndex >= 0) {
        // Update existing report
        updatedReports = [...prev];
        updatedReports[existingIndex] = report;
      } else {
        // Add new report
        updatedReports = [report, ...prev];
      }
      
      // Re-sort to maintain order (most recent first)
      return updatedReports.sort((a, b) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
    });
  };

  const handleViewReport = (report: Report) => {
    setSelectedReport(report);
    setShowReportViewer(true);
  };

  const handleRefreshDocuments = () => {
    loadPatientData();
  };

  const refreshReports = async () => {
    if (!patientId || !patientId.trim()) {
      setReports([]);
      return;
    }
    
    try {
      const reportsResponse = await apiService.getPatientReports(patientId);
      // Sort reports by created_at in descending order (most recent first)
      const sortedReports = reportsResponse.items.sort((a, b) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      setReports(sortedReports);
    } catch (err) {
      console.error('Error refreshing reports:', err);
    }
  };

  const handleDisclaimerAccept = () => {
    setDisclaimerAccepted(true);
    setShowDisclaimer(false);
  };

  const handleDisclaimerReject = () => {
    // Close the browser tab/window or redirect away
    window.close();
    // Fallback: redirect to a safe page if window.close() doesn't work
    setTimeout(() => {
      window.location.href = 'about:blank';
    }, 100);
  };

  // Report generation handlers
  const handleReportGenerationStart = () => {
    setIsGeneratingReport(true);
    setReportGenerationProgress(null);
  };

  const handleReportGenerationProgress = (progress: ReportGenerationProgress) => {
    setReportGenerationProgress(progress);
  };

  const handleReportGenerationComplete = () => {
    setIsGeneratingReport(false);
    setReportGenerationProgress(null);
  };

  const handleReportGenerationError = () => {
    setIsGeneratingReport(false);
    setReportGenerationProgress(null);
  };

  const navigation = [
    { id: 'documents', label: t.navigation.documents, icon: FileText },
    { id: 'reports', label: t.navigation.reports, icon: BarChart3 },
    { id: 'assistant', label: t.navigation.assistant, icon: MessageCircle, preview: true },
    { id: 'observability', label: 'Observabilité', icon: Eye },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {disclaimerAccepted && (
        <>
          {/* Fixed Header */}
          <header className="fixed top-0 left-0 right-0 z-50 bg-white/95 backdrop-blur-sm shadow-sm border-b border-gray-200">
            <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8">
              {/* Institution Banner */}
              <div className="bg-medical-600 text-white px-4 py-2 -mx-4 -mt-0 mb-4">
                <div className="flex items-center justify-between">
                  {/* Warning Message - Left Side */}
                  <div className="bg-amber-50 border border-amber-200 rounded-md px-3 py-1 shadow-sm">
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-amber-500 rounded-full animate-pulse"></div>
                      <span className="text-sm font-bold text-amber-800">{t.header.warningBanner}</span>
                    </div>
                  </div>
                  
                  {/* Institution Name - Center */}
                  <div className="absolute left-1/2 transform -translate-x-1/2">
                    <h2 className="text-lg font-semibold">{t.header.institution}</h2>
                  </div>
                  
                  {/* Spacer for balance - Right Side */}
                  <div className="w-24"></div>
                </div>
              </div>
              
              <div className="flex justify-between items-center py-4">
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2">
                    <div className="w-8 h-8 bg-medical-600 rounded-lg flex items-center justify-center">
                      <User className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <h1 className="text-xl font-bold text-gray-900">
                        {t.header.title}
                      </h1>
                      <p className="text-sm text-gray-500">{t.header.subtitle}</p>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center space-x-4">
                  {/* Smart Header Collapse - Dynamic content based on view */}
                  <div className="header-transition">
                    {currentView === 'assistant' ? (
                      /* Assistant Mode - Global Context */
                      <div className="header-context-indicator">
                        <div className="flex items-center space-x-2">
                          <Bot className="w-5 h-5 text-medical-600" />
                          <div className="flex flex-col">
                            <span className="text-sm font-medium text-medical-700">
                              Assistant Intelligent
                            </span>
                            <span className="text-xs text-medical-600">
                              Analyse globale • Base de connaissances
                            </span>
                          </div>
                        </div>
                        <div className="hidden sm:flex items-center space-x-2 pl-3 border-l border-medical-200">
                          <Database className="w-4 h-4 text-medical-500" />
                          <span className="text-xs text-medical-600 font-medium">
                            {t.assistant.allPatients}
                          </span>
                        </div>
                      </div>
                    ) : (
                      /* Patient Mode - Patient-specific context */
                      <div className="header-patient-mode">
                        <PatientSelector
                          patientId={patientId}
                          onPatientIdChange={setPatientId}
                          onOpenPatients={() => setShowPatientsDialog(true)}
                        />
                      </div>
                    )}
                  </div>
                  
                  <LanguageSwitcher />
                  <button
                    onClick={() => setShowSettings(true)}
                    className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                    title={t.settings.title}
                  >
                    <Settings className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Navigation - now part of fixed header */}
              <div className="border-t border-gray-200 bg-gray-50 -mx-4 px-4 py-3">
                <nav className="flex space-x-1">
                  {navigation.map((item) => {
                    const Icon = item.icon;
                    return (
                      <button
                        key={item.id}
                        onClick={() => setCurrentView(item.id as 'documents' | 'reports' | 'assistant' | 'observability')}
                        className={`
                          flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-colors
                          ${currentView === item.id
                            ? 'bg-medical-100 text-medical-700 border border-medical-200'
                            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                          }
                        `}
                      >
                        <Icon className="w-4 h-4" />
                        <span>{item.label}</span>
                        {item.preview && (
                          <span className="preview-badge ml-2">
                            {t.assistant.previewBadge}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </nav>
              </div>
            </div>
          </header>

          {/* Header Spacer - ensures content starts below fixed header */}
          <div className="h-64 lg:h-60"></div>
          
          {/* Main Content */}
          <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {error && (
              <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <X className="h-5 w-5 text-red-400" />
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-800">{t.messages.error}</h3>
                    <div className="mt-2 text-sm text-red-700">{error}</div>
                  </div>
                </div>
              </div>
            )}

            {currentView === 'assistant' ? (
              /* Assistant full-width layout */
              <IntelligentAssistant />
            ) : (
              /* Standard documents/reports layout */
              <div className="flex flex-col lg:flex-row gap-6">
                {/* Main Content */}
                <div className="flex-1">
                  {/* Content */}
                  {isLoading ? (
                    <div className="card">
                      <div className="flex items-center justify-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-medical-600"></div>
                        <span className="ml-3 text-gray-600">{t.messages.loadingPatientData}</span>
                      </div>
                    </div>
                  ) : (
                    <>
                      {currentView === 'documents' && (
                        <DocumentsList
                          documents={documents}
                          onRefresh={handleRefreshDocuments}
                          patientId={patientId}
                          onDocumentUploaded={handleDocumentUploaded}
                          onDocumentStatusUpdate={handleDocumentStatusUpdate}
                          onPatientIdChange={setPatientId}
                        />
                      )}

                      {currentView === 'reports' && (
                        <ReportsList
                          reports={reports}
                          patientId={patientId}
                          onReportGenerated={handleReportGenerated}
                          onViewReport={handleViewReport}
                          isGenerating={isGeneratingReport}
                          generationProgress={reportGenerationProgress}
                          onGenerationStart={handleReportGenerationStart}
                          onGenerationProgress={handleReportGenerationProgress}
                          onGenerationComplete={handleReportGenerationComplete}
                          onGenerationError={handleReportGenerationError}
                          onRefreshReports={refreshReports}
                        />
                      )}

                      {currentView === 'observability' && (
                        <Observability />
                      )}
                    </>
                  )}
                </div>

                {/* Report Viewer Sidebar */}
                {showReportViewer && selectedReport && (
                  <div className="lg:w-1/2 xl:w-1/2 2xl:w-1/2">
                    <ReportViewer
                      report={selectedReport}
                      onClose={() => setShowReportViewer(false)}
                    />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Settings Modal */}
          {showSettings && (
            <SettingsPanel
              apiBaseUrl={apiBaseUrl}
              onApiBaseUrlChange={setApiBaseUrl}
              onClose={() => setShowSettings(false)}
            />
          )}

          {showPatientsDialog && (
            <PatientsDialog
              isOpen={showPatientsDialog}
              onClose={() => setShowPatientsDialog(false)}
              onSelect={(pid) => setPatientId(pid)}
            />
          )}
        </>
      )}

      {/* Disclaimer Modal */}
      <DisclaimerModal
        isOpen={showDisclaimer}
        onAccept={handleDisclaimerAccept}
        onReject={handleDisclaimerReject}
      />
    </div>
  );
}

function App() {
  return (
    <I18nProvider>
      <AppContent />
    </I18nProvider>
  );
}

export default App; 