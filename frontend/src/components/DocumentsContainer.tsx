import React, { useState, useEffect } from 'react';
import { FileText, Clock, FolderOpen, ArrowRight, CheckCircle2, Inbox, Archive, ChevronRight } from 'lucide-react';
import { PatientDocument } from '../types';
import DocumentsList from './DocumentsList';
import UnprocessedDocumentsList from './UnprocessedDocumentsList';
import { apiService } from '../services/api';
import { useI18n } from '../i18n/context';

interface DocumentsContainerProps {
  documents: PatientDocument[];
  onRefresh: () => void;
  patientId: string;
  onDocumentUploaded: (document: PatientDocument) => void;
  onDocumentStatusUpdate: (updatedDocument: PatientDocument) => void;
  onPatientIdChange?: (newPatientId: string) => void;
}

type DocumentTab = 'processed' | 'unprocessed';

export default function DocumentsContainer({
  documents,
  onRefresh,
  patientId,
  onDocumentUploaded,
  onDocumentStatusUpdate,
  onPatientIdChange
}: DocumentsContainerProps) {
  const { t } = useI18n();
  // Default to unprocessed tab - this is the first step in the workflow
  const [activeTab, setActiveTab] = useState<DocumentTab>('unprocessed');
  const [unprocessedCount, setUnprocessedCount] = useState<number>(0);
  const [showStructureDiagram, setShowStructureDiagram] = useState<boolean>(false);
  const [showRawExample, setShowRawExample] = useState<boolean>(false);

  // Fetch unprocessed count
  useEffect(() => {
    const fetchUnprocessedCount = async () => {
      // Guard against empty patient ID
      if (!patientId) {
        setUnprocessedCount(0);
        return;
      }
      
      try {
        const count = await apiService.getUnprocessedDocumentCount(patientId);
        setUnprocessedCount(count);
      } catch (error) {
        console.error('Failed to fetch unprocessed count:', error);
        setUnprocessedCount(0);
      }
    };

    fetchUnprocessedCount();
  }, [patientId]);

  // Handler when processing completes - refresh both lists and redirect to processed tab
  const handleProcessingComplete = () => {
    // Refresh processed documents list
    onRefresh();
    
    // Update unprocessed count
    apiService.getUnprocessedDocumentCount(patientId)
      .then(count => {
        setUnprocessedCount(count);
        // Redirect to processed tab after processing
        setActiveTab('processed');
      })
      .catch(console.error);
  };

  const tabs = [
    {
      id: 'unprocessed' as DocumentTab,
      label: 'Incoming',
      sublabel: 'Documents to process',
      icon: Inbox,
      count: unprocessedCount,
      color: 'amber'
    },
    {
      id: 'processed' as DocumentTab,
      label: 'Pre-processed',
      sublabel: 'Ready for reports',
      icon: Archive,
      count: documents.length,
      color: 'green'
    }
  ];

  return (
    <div className="space-y-6 overflow-x-hidden w-full">
      {/* Professional Tab Navigation */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="flex">
          {tabs.map((tab, index) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex-1 relative flex items-center justify-center gap-3 px-6 py-4 
                  transition-all duration-200 border-b-2
                  ${isActive 
                    ? 'bg-gray-50 border-blue-600' 
                    : 'border-transparent hover:bg-gray-50'
                  }
                `}
              >
                {/* Icon container */}
                <div className={`
                  w-10 h-10 rounded-lg flex items-center justify-center transition-colors
                  ${isActive 
                    ? 'bg-blue-100 text-blue-600' 
                    : 'bg-gray-100 text-gray-500'
                  }
                `}>
                  <Icon className="w-5 h-5" />
                </div>
                
                {/* Text */}
                <div className="text-left">
                  <div className={`font-semibold text-sm ${isActive ? 'text-gray-900' : 'text-gray-600'}`}>
                    {tab.label}
                  </div>
                  <div className="text-xs text-gray-500">{tab.sublabel}</div>
                </div>
                
                {/* Count badge */}
                {tab.count > 0 && (
                  <span className={`
                    ml-2 px-2.5 py-0.5 rounded-full text-xs font-bold
                    ${tab.id === 'unprocessed' 
                      ? 'bg-amber-100 text-amber-700' 
                      : 'bg-green-100 text-green-700'
                    }
                  `}>
                    {tab.count}
                  </span>
                )}
                
                {/* Active indicator arrow */}
                {isActive && (
                  <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2">
                    <div className="w-3 h-3 bg-gray-50 border-r border-b border-gray-200 rotate-45" />
                  </div>
                )}
              </button>
            );
          })}
        </div>
        
        {/* Data Structure Description */}
        <div className="bg-blue-50 border-t border-blue-200 px-6 py-4">
          <div className="flex items-start space-x-4">
            <div className="flex-shrink-0">
              <FileText className="w-5 h-5 text-blue-600 mt-0.5" />
            </div>
            <div className="flex-1">
              {activeTab === 'unprocessed' ? (
                <>
                  <h3 className="font-medium text-blue-900 text-sm mb-2">Raw Document Format</h3>
                  <p className="text-blue-800 text-sm mb-3">
                    Incoming documents contain <strong>unstructured plain text data</strong> extracted from medical documents. 
                    This data lacks formatting and organizational structure, requiring processing to identify and categorize 
                    medical entities such as patient information, diagnoses, and treatment details.
                  </p>
                  
                  {/* Collapsible visual representation of unstructured data */}
                  <div className="bg-white border border-blue-200 rounded-lg p-4">
                    <button
                      onClick={() => setShowRawExample(!showRawExample)}
                      className="w-full flex items-center justify-between text-sm font-semibold text-blue-800 hover:text-blue-900 transition-colors"
                    >
                      <span>Data Structure Example</span>
                      <ChevronRight className={`w-4 h-4 transition-transform duration-200 ${showRawExample ? 'transform rotate-90' : ''}`} />
                    </button>
                    
                    {showRawExample && (
                      <div className="mt-4">
                        <div className="text-xs text-gray-600 leading-relaxed">
                          <div className="bg-gray-50 p-3 rounded font-mono text-xs border border-gray-200">
                            <div className="text-gray-700 mb-1">📄 Raw Medical Text:</div>
                            <div className="text-gray-500 leading-relaxed">
                              "Patient Jean Dupont age 65 consultation cardiology diagnosed with hypertension diabetes 
                              medication Lisinopril laboratory results blood pressure 140/90 glucose elevated 
                              appointment scheduled follow-up treatment plan dietary changes..."
                            </div>
                          </div>
                          <div className="mt-3 flex items-center text-gray-500">
                            <div className="w-4 h-4 text-red-500 mr-2">💭</div>
                            <span className="text-xs">No structure • All mixed together • Hard to parse</span>
                          </div>
                        </div>
                        <div className="mt-2 text-xs text-red-600 flex items-center space-x-1">
                          <span>⚠️</span>
                          <span>Requires NLP processing to extract entities</span>
                        </div>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <h3 className="font-medium text-blue-900 text-sm mb-2">Structured Document Format</h3>
                  <p className="text-blue-800 text-sm mb-3">
                    Pre-processed documents contain <strong>structured data with organized sections and metadata</strong> after NLP processing. Medical entities have been identified, categorized, and formatted for analysis, 
                    making them ready for report generation and clinical review.
                  </p>
                  
                  {/* Professional collapsible diagram of structured document entities */}
                  <div className="bg-white border border-blue-200 rounded-lg p-4">
                    <button
                      onClick={() => setShowStructureDiagram(!showStructureDiagram)}
                      className="w-full flex items-center justify-between text-sm font-semibold text-blue-800 hover:text-blue-900 transition-colors"
                    >
                      <span>Document Entity Structure</span>
                      <ChevronRight className={`w-4 h-4 transition-transform duration-200 ${showStructureDiagram ? 'transform rotate-90' : ''}`} />
                    </button>
                    
                    {showStructureDiagram && (
                      <div className="mt-4">
                        {/* Entity structure column layout */}
                        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                          
                          {/* Main document header */}
                          <div className="text-center mb-4">
                            <div className="inline-flex items-center space-x-2 bg-white border border-slate-300 rounded-md px-3 py-1.5 shadow-sm">
                              <div className="w-4 h-4 bg-slate-600 rounded-sm flex items-center justify-center">
                                <svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                                </svg>
                              </div>
                              <span className="font-medium text-slate-800 text-sm">Document Entity</span>
                            </div>
                          </div>
                          
                          {/* Structured column layout for entity fields */}
                          <div className="space-y-2">
                            
                            {/* Text field */}
                            <div className="bg-white border border-gray-300 rounded-md p-2.5 shadow-sm hover:shadow-md transition-shadow duration-200">
                              <div className="flex items-center mb-2">
                                <div className="w-3 h-3 bg-slate-500 rounded-sm mr-2 flex items-center justify-center">
                                  <div className="w-1.5 h-1.5 bg-white rounded-sm"></div>
                                </div>
                                <span className="font-medium text-slate-700 text-sm">text</span>
                                <div className="ml-auto text-xs text-slate-600 font-medium bg-slate-100 px-2 py-0.5 rounded">Raw Content</div>
                              </div>
                              <div className="text-xs text-gray-600 leading-relaxed bg-gray-50 p-2 rounded border-l-2 border-slate-400 pl-3">
                                "Patient Jean Dupont, 65 ans, consultation cardiologie..."
                              </div>
                            </div>
                            
                            {/* Content field */}
                            <div className="bg-white border border-gray-300 rounded-md p-2.5 shadow-sm hover:shadow-md transition-shadow duration-200">
                              <div className="flex items-center mb-2">
                                <div className="w-3 h-3 bg-slate-500 rounded-sm mr-2 flex items-center justify-center">
                                  <div className="w-1.5 h-1.5 bg-white rounded-sm"></div>
                                </div>
                                <span className="font-medium text-slate-700 text-sm">content</span>
                                <div className="ml-auto text-xs text-slate-600 font-medium bg-slate-100 px-2 py-0.5 rounded">Structured Data</div>
                              </div>
                              <div className="text-xs text-gray-600 leading-relaxed bg-gray-50 p-2 rounded border-l-2 border-slate-400 pl-3">
                                "Organized medical entities after NLP processing..."
                              </div>
                            </div>
                            
                            {/* Document type field */}
                            <div className="bg-white border border-gray-300 rounded-md p-2.5 shadow-sm hover:shadow-md transition-shadow duration-200">
                              <div className="flex items-center mb-2">
                                <div className="w-3 h-3 bg-slate-500 rounded-sm mr-2 flex items-center justify-center">
                                  <div className="w-1.5 h-1.5 bg-white rounded-sm"></div>
                                </div>
                                <span className="font-medium text-slate-700 text-sm">document_type</span>
                                <div className="ml-auto text-xs text-slate-600 font-medium bg-slate-100 px-2 py-0.5 rounded">Type Classification</div>
                              </div>
                              <div className="text-xs text-gray-600 leading-relaxed bg-gray-50 p-2 rounded border-l-2 border-slate-400 pl-3">
                                "consultation_report"
                              </div>
                            </div>
                            
                            {/* Extraction method field */}
                            <div className="bg-white border border-gray-300 rounded-md p-2.5 shadow-sm hover:shadow-md transition-shadow duration-200">
                              <div className="flex items-center mb-2">
                                <div className="w-3 h-3 bg-slate-500 rounded-sm mr-2 flex items-center justify-center">
                                  <div className="w-1.5 h-1.5 bg-white rounded-sm"></div>
                                </div>
                                <span className="font-medium text-slate-700 text-sm">extraction_method</span>
                                <div className="ml-auto text-xs text-slate-600 font-medium bg-slate-100 px-2 py-0.5 rounded">Processing Method</div>
                              </div>
                              <div className="text-xs text-gray-600 leading-relaxed bg-gray-50 p-2 rounded border-l-2 border-slate-400 pl-3">
                                "pdf_text_extraction"
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        <div className="mt-3 text-sm text-gray-700 flex items-center space-x-2">
                          <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                          <span>Structured entities ready for medical entity extraction</span>
                        </div>
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'processed' ? (
        <DocumentsList
          documents={documents}
          onRefresh={onRefresh}
          patientId={patientId}
          onDocumentUploaded={onDocumentUploaded}
          onDocumentStatusUpdate={onDocumentStatusUpdate}
          onPatientIdChange={onPatientIdChange}
        />
      ) : (
        <UnprocessedDocumentsList
          patientId={patientId}
          onProcessingComplete={handleProcessingComplete}
          onNavigateToProcessed={() => setActiveTab('processed')}
          onDocumentUploaded={onDocumentUploaded}
          onDocumentStatusUpdate={onDocumentStatusUpdate}
          onPatientIdChange={onPatientIdChange}
        />
      )}
    </div>
  );
}
