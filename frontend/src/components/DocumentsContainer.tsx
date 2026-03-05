import React, { useState, useEffect } from 'react';
import { FileText, Clock, FolderOpen, ArrowRight, CheckCircle2, Inbox, Archive } from 'lucide-react';
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
      label: 'Processed',
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
