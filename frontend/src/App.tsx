import React, { useState, useEffect } from 'react';
import { FileText, User, BarChart3, Settings, X, Eye, Users, Menu, ChevronLeft } from 'lucide-react';
import PatientSelector from './components/PatientSelector';
import PatientSelectionView from './components/PatientSelectionView';
import DocumentsContainer from './components/DocumentsContainer';
import ReportsList from './components/ReportsList';
import ReportViewer from './components/ReportViewer';
import SettingsPanel from './components/SettingsPanel';
import Observability from './components/Observability';
import GTUploadDialog from './components/GTUploadDialog';
import GTVerifyDialog from './components/GTVerifyDialog';
import EvaluationResultsDialog from './components/EvaluationResultsDialog';
import LanguageSwitcher from './components/LanguageSwitcher';
import PatientsDialog from './components/PatientsDialog';
import DisclaimerModal from './components/DisclaimerModal';
import MongoDBHealthcareLogo from './components/CobrandedLogo';
import InfoModal from './components/InfoModal';
import InfoButton from './components/InfoButton';
import { I18nProvider, useI18n } from './i18n/context';
import { apiService, getApiBaseURL } from './services/api';
import { PatientDocument, Report, ReportGenerationProgress, GroundTruthEntity } from './types';
import { useInfoModal, tabInfoContent } from './hooks/useInfoModal';

function AppContent() {
  const { t } = useI18n();
  const [currentView, setCurrentView] = useState<'documents' | 'reports' | 'observability'>('documents');
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
  
  // Sidebar collapse state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);
  
  // Report generation state - moved here to persist across tab switches
  const [isGeneratingReport, setIsGeneratingReport] = useState<boolean>(false);
  const [reportGenerationProgress, setReportGenerationProgress] = useState<ReportGenerationProgress | null>(null);

  // GT and Evaluation modal states
  const [showGTUpload, setShowGTUpload] = useState<boolean>(false);
  const [showGTVerify, setShowGTVerify] = useState<boolean>(false);
  const [showEvalResults, setShowEvalResults] = useState<boolean>(false);
  const [selectedGeneration, setSelectedGeneration] = useState<any>(null);
  const [extractedEntities, setExtractedEntities] = useState<GroundTruthEntity[]>([]);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);

  // Info modal states for each tab
  const documentsInfo = useInfoModal('documents', currentView === 'documents' && !!patientId);
  const reportsInfo = useInfoModal('reports', currentView === 'reports' && !!patientId);
  const observabilityInfo = useInfoModal('observability', currentView === 'observability' && !!patientId);

  // Debug: Track generation state across tab switches
  useEffect(() => {
    if (isGeneratingReport) {
      console.log('🎯 App-level generation state: GENERATING - Progress:', reportGenerationProgress?.progress + '%' || 'null');
    }
  }, [isGeneratingReport, reportGenerationProgress]);

  // Keyboard shortcut for sidebar toggle (Ctrl/Cmd + \\)
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === '\\' && patientId) {
        event.preventDefault();
        setIsSidebarCollapsed(!isSidebarCollapsed);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isSidebarCollapsed, patientId]);

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

  // Auto-refresh reports when switching to reports tab
  useEffect(() => {
    if (currentView === 'reports' && patientId) {
      // Refresh only the reports data when switching to reports tab
      refreshReports();
    }
  }, [currentView, patientId]);

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

  // GT Modal handlers
  const handleShowGTUpload = (generation: any) => {
    setSelectedGeneration(generation);
    setShowGTUpload(true);
  };

  const handleShowGTVerify = (generation: any, entities: GroundTruthEntity[]) => {
    setSelectedGeneration(generation);
    setExtractedEntities(entities);
    setShowGTVerify(true);
  };

  const handleShowEvalResults = (generation: any) => {
    setSelectedGeneration(generation);
    setShowEvalResults(true);
  };

  const handleGTUploadComplete = (entities: GroundTruthEntity[]) => {
    setExtractedEntities(entities);
    setShowGTUpload(false);
    setShowGTVerify(true);
  };

  const handleGTSave = () => {
    // Entities saved, stay on verify dialog
  };

  const handleRunEvaluation = async () => {
    if (!selectedGeneration) return;
    const reportUuid = selectedGeneration.report?.uuid;
    if (!reportUuid) {
      alert('Report UUID not found');
      return;
    }

    setShowGTVerify(false);
    setIsEvaluating(true);

    try {
      await apiService.runEvaluation(
        selectedGeneration.patient_id,
        reportUuid,
        (data) => {
          if (data.status === 'FAILED') {
            alert(`Evaluation failed: ${data.message}`);
            setIsEvaluating(false);
          }
        }
      );
      setIsEvaluating(false);
      setShowEvalResults(true);
      // Note: Observability data refresh would need to be handled separately if needed
    } catch (e: any) {
      console.error('Evaluation failed:', e);
      alert(`Evaluation failed: ${e.message || 'Unknown error'}`);
      setIsEvaluating(false);
    }
  };

  const handleReEvaluate = () => {
    setShowEvalResults(false);
    handleRunEvaluation();
  };

  const handleCloseGTDialogs = () => {
    setShowGTUpload(false);
    setShowGTVerify(false);
    setShowEvalResults(false);
    setSelectedGeneration(null);
    setExtractedEntities([]);
  };

  const navigation = [
    { id: 'documents', label: t.navigation.documents, icon: FileText, infoModal: documentsInfo },
    { id: 'reports', label: t.navigation.reports, icon: BarChart3, infoModal: reportsInfo },
    { id: 'observability', label: t.navigation.observability, icon: Eye, infoModal: observabilityInfo },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-white overflow-x-hidden max-w-[100vw]">
      {disclaimerAccepted && (
        <>
          {/* Fixed Header */}
          <header className="fixed top-0 left-0 right-0 z-50 bg-white/98 backdrop-blur-md shadow-lg border-b border-gray-200">
            {/* Professional Header with Cobranded Logo - Full Width */}
            <div 
              className="text-white px-6 py-8 border-b-2 border-mongodb-green relative"
              style={{
                backgroundImage: `url('/HeaderBackground.png')`,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                backgroundRepeat: 'no-repeat'
              }}
            >
              {/* Overlay for better text readability */}
              <div className="absolute inset-0 bg-black bg-opacity-40"></div>
              <div className="flex items-center justify-between relative z-10">
                {/* Empty div for layout balance */}
                <div className="flex-1"></div>
                
                {/* MongoDB Healthcare Logo - Center */}
                <div className="flex-1 flex justify-center">
                  <div className="transform scale-150">
                    <MongoDBHealthcareLogo size="lg" />
                  </div>
                </div>
                
                {/* Professional Badge - Right Side */}
                <div className="flex-1 flex justify-end">
                  <div className="flex items-center space-x-2 bg-mongodb-green/10 border border-mongodb-green/30 rounded-lg px-4 py-2">
                    <div className="w-2 h-2 bg-mongodb-green rounded-full"></div>
                    <span className="text-sm font-medium text-mongodb-green">Backend Connected</span>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="w-full px-4 sm:px-6 lg:px-8 overflow-hidden">
              <div className="flex justify-between items-center py-6">
                <div className="flex items-center space-x-6">
                  <div className="flex items-center space-x-3">
                    <div className="w-12 h-12 bg-gradient-to-br from-navy-600 to-navy-800 rounded-xl flex items-center justify-center shadow-lg">
                      <User className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h1 className="text-2xl font-bold text-navy-900 tracking-tight">
                        {t.header.title}
                      </h1>
                      <p className="text-sm text-gray-600 font-medium">{t.header.subtitle}</p>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center space-x-4">
                  {/* Patient Mode - Only show when patient is selected */}
                  {patientId && (
                    <div className="header-patient-mode">
                      <PatientSelector
                        patientId={patientId}
                        onPatientIdChange={setPatientId}
                        onOpenPatients={() => setShowPatientsDialog(true)}
                      />
                    </div>
                  )}
                  
                  {/* Back to Patient Selection - Show when patient is selected */}
                  {patientId && (
                    <button
                      onClick={() => {
                        setPatientId('');
                        setCurrentView('documents'); // Reset to documents view
                      }}
                      className="flex items-center space-x-2 px-4 py-2 text-gray-600 hover:text-navy-700 hover:bg-gray-100 rounded-xl transition-all duration-200 shadow-sm border border-gray-200"
                      title="Back to Patient Selection"
                    >
                      <Users className="w-5 h-5" />
                      <span className="hidden lg:block text-sm font-medium">All Patients</span>
                    </button>
                  )}
                  
                  <LanguageSwitcher />
                  <button
                    onClick={() => setShowSettings(true)}
                    className="p-3 text-gray-500 hover:text-navy-700 hover:bg-gray-100 rounded-xl transition-all duration-200 shadow-sm border border-gray-200"
                    title={t.settings.title}
                  >
                    <Settings className="w-5 h-5" />
                  </button>
                </div>
              </div>


            </div>
          </header>

          {/* Header Spacer - ensures content starts below fixed header */}
          <div className="h-64 lg:h-56"></div>
          
          {/* Main Layout */}
          <div className={`flex min-h-screen ${!patientId ? '' : ''}`}>
            {/* Left Sidebar Navigation - Only show when patient is selected */}
            {patientId && (
              <div className={`fixed left-0 top-64 lg:top-56 bottom-0 bg-white/95 backdrop-blur-md shadow-lg border-r border-gray-200 z-40 transition-all duration-300 ${
                isSidebarCollapsed ? 'w-20' : 'w-80'
              }`}>
                {/* Sidebar Header with Title and Toggle */}
                <div className="p-4 border-b border-gray-200 flex items-center justify-between">
                  {!isSidebarCollapsed && (
                    <div className="flex-1">
                      <h2 className="text-lg font-bold text-navy-800 truncate">
                        Patient Workspace
                      </h2>
                      <p className="text-xs text-gray-600 truncate">
                        {patientId}
                      </p>
                    </div>
                  )}
                  
                  <button
                    onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
                    className={`p-2 rounded-lg hover:bg-gray-100 transition-colors text-navy-700 hover:text-navy-900 ${isSidebarCollapsed ? 'mx-auto' : 'ml-2'}`}
                    title={isSidebarCollapsed ? 'Expand Sidebar (Ctrl/⌘ + \\)' : 'Collapse Sidebar (Ctrl/⌘ + \\)'}
                  >
                    {isSidebarCollapsed ? (
                      <Menu className="w-5 h-5" />
                    ) : (
                      <ChevronLeft className="w-5 h-5" />
                    )}
                  </button>
                </div>

                <nav className="p-6 space-y-2">
                  {navigation.map((item) => {
                    const Icon = item.icon;
                    return (
                      <div key={item.id} className="flex items-stretch space-x-1">
                        <button
                          onClick={() => setCurrentView(item.id as 'documents' | 'reports' | 'observability')}
                          className={`
                            ${isSidebarCollapsed ? 'flex-col p-2 space-x-0 space-y-1' : 'flex-row px-4 py-3 space-x-3'}
                            flex-1 flex items-center rounded-xl font-semibold transition-all duration-200 shadow-sm
                            ${currentView === item.id
                              ? 'bg-gradient-to-r from-navy-700 to-navy-800 text-white border border-navy-600 shadow-lg'
                              : 'text-navy-700 hover:text-navy-900 hover:bg-gray-50 hover:shadow-md border border-gray-200/50 bg-white/50'
                            }
                          `}
                          title={isSidebarCollapsed ? item.label : undefined}
                        >
                          <Icon className={`w-5 h-5 ${currentView === item.id ? 'text-mongodb-green' : ''} ${isSidebarCollapsed ? 'mb-1' : ''}`} />
                          {!isSidebarCollapsed && <span className="font-medium">{item.label}</span>}
                        </button>
                        
                        {/* Info Button - only show when sidebar is expanded */}
                        {!isSidebarCollapsed && (
                          <InfoButton
                            onClick={(position) => item.infoModal.showModal(position)}
                            className="flex-shrink-0"
                            isActive={currentView === item.id}
                          />
                        )}
                      </div>
                    );
                  })}
                </nav>
              </div>
            )}

            {/* Main Content Area */}
            <div className={`flex-1 ${patientId ? (isSidebarCollapsed ? 'ml-20' : 'ml-80') : ''} px-4 sm:px-6 lg:px-8 py-8 transition-all duration-300`} style={{ maxWidth: patientId ? (isSidebarCollapsed ? 'calc(100vw - 5rem)' : 'calc(100vw - 20rem)') : '100vw', overflowX: 'hidden' }}>
              {error && (
                <div className="mb-6 bg-red-50/90 border border-red-200 rounded-xl p-6 backdrop-blur-sm shadow-sm">
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

              {/* Standard documents/reports layout */}
              <div className="flex flex-col lg:flex-row gap-6 overflow-hidden w-full">
              {/* Main Content */}
              <div className="flex-1 min-w-0 overflow-hidden">
                  {/* Content */}
                  {!patientId ? (
                    /* Show patient selection when no patient is selected */
                    <PatientSelectionView onSelectPatient={setPatientId} />
                  ) : isLoading ? (
                    <div className="card bg-white/90 backdrop-blur-sm shadow-lg">
                      <div className="flex items-center justify-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-navy-700"></div>
                        <span className="ml-3 text-navy-700 font-medium">{t.messages.loadingPatientData}</span>
                      </div>
                    </div>
                  ) : (
                    <>
                      {currentView === 'documents' && (
                        <DocumentsContainer
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
                        <Observability 
                          patientId={patientId} 
                          onShowGTUpload={handleShowGTUpload}
                          onShowGTVerify={handleShowGTVerify}
                          onShowEvalResults={handleShowEvalResults}
                        />
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        
          {/* Report Viewer Modal */}
          {showReportViewer && selectedReport && (
            <div className="fixed inset-0 z-50 flex items-center justify-center">
              {/* Backdrop */}
              <div 
                className="absolute inset-0 bg-black bg-opacity-50" 
                onClick={() => setShowReportViewer(false)}
              ></div>
              
              {/* Modal Content */}
              <div className="relative w-[50vw] h-[95vh] max-w-none">
                <ReportViewer
                  report={selectedReport}
                  onClose={() => setShowReportViewer(false)}
                />
              </div>
            </div>
          )}
        
          {showSettings && (
            <SettingsPanel
              apiBaseUrl={apiBaseUrl}
              onApiBaseUrlChange={setApiBaseUrl}
              onClose={() => setShowSettings(false)}
            />
          )}

          {/* GT Upload Dialog */}
          {showGTUpload && selectedGeneration && (
            <GTUploadDialog
              isOpen={showGTUpload}
              onClose={handleCloseGTDialogs}
              patientId={selectedGeneration.patient_id}
              reportUuid={selectedGeneration.report?.uuid}
              onComplete={handleGTUploadComplete}
            />
          )}

          {/* GT Verify Dialog */}
          {showGTVerify && selectedGeneration && (
            <GTVerifyDialog
              isOpen={showGTVerify}
              onClose={handleCloseGTDialogs}
              patientId={selectedGeneration.patient_id}
              reportUuid={selectedGeneration.report?.uuid}
              initialEntities={extractedEntities}
              onSave={handleGTSave}
              onRunEvaluation={handleRunEvaluation}
            />
          )}

          {/* Evaluation Results Dialog */}
          {showEvalResults && selectedGeneration && (
            <EvaluationResultsDialog
              isOpen={showEvalResults}
              onClose={handleCloseGTDialogs}
              patientId={selectedGeneration.patient_id}
              reportUuid={selectedGeneration.report?.uuid}
              onReEvaluate={handleReEvaluate}
            />
          )}

          {/* Evaluation Progress Overlay */}
          {isEvaluating && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 text-white">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
                <h3 className="text-xl font-semibold mb-2">Running Evaluation</h3>
                <p className="text-lg">Please wait while we evaluate the entities...</p>
              </div>
            </div>
          )}

          {showPatientsDialog && (
            <PatientsDialog
              isOpen={showPatientsDialog}
              onClose={() => setShowPatientsDialog(false)}
              onSelect={(pid) => setPatientId(pid)}
            />
          )}

          {/* Info Modals for each tab - only show when patient is selected */}
          {patientId && (
            <>
              <InfoModal
                isOpen={documentsInfo.isOpen}
                onClose={documentsInfo.hideModal}
                content={tabInfoContent.documents}
                buttonPosition={documentsInfo.buttonPosition}
              />
              <InfoModal
                isOpen={reportsInfo.isOpen}
                onClose={reportsInfo.hideModal}
                content={tabInfoContent.reports}
                buttonPosition={reportsInfo.buttonPosition}
              />
              <InfoModal
                isOpen={observabilityInfo.isOpen}
                onClose={observabilityInfo.hideModal}
                content={tabInfoContent.observability}
                buttonPosition={observabilityInfo.buttonPosition}
              />
            </>
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