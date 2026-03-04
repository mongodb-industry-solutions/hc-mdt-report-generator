import { useState, useCallback, useEffect } from 'react';
import { FileText, BarChart3, Eye, Upload, Stethoscope, Activity, TrendingUp, Database, Users, UserPlus } from 'lucide-react';
import { InfoModalContent } from '../components/InfoModal';

// Storage key prefix for tracking visited tabs
const STORAGE_PREFIX = 'claritygr_info_visited_';

// Utility to reset all info modal visited status (for testing)
export const resetInfoModalsVisitedStatus = () => {
  try {
    const keys = ['patientSelection', 'documents', 'reports', 'observability'];
    keys.forEach(key => {
      sessionStorage.removeItem(`${STORAGE_PREFIX}${key}`);
    });
  } catch (e) {
    console.warn('Could not reset sessionStorage:', e);
  }
};

// Hook for managing info modal state per tab
export function useInfoModal(tabId: string, isActive: boolean = false) {
  const storageKey = `${STORAGE_PREFIX}${tabId}`;
  
  const [hasBeenVisited, setHasBeenVisited] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  // Initialize visited status on mount
  useEffect(() => {
    try {
      const visited = sessionStorage.getItem(storageKey) === 'true';
      setHasBeenVisited(visited);
    } catch {
      setHasBeenVisited(false);
    }
  }, [storageKey, tabId]);

  // Effect to show modal when tab becomes active for first time
  useEffect(() => {
    if (isActive && !hasBeenVisited && !isOpen) {
      setIsOpen(true);
    }
  }, [isActive, hasBeenVisited, isOpen, tabId]);

  const showModal = useCallback(() => {
    setIsOpen(true);
  }, []);

  const hideModal = useCallback(() => {
    setIsOpen(false);
    if (!hasBeenVisited) {
      try {
        sessionStorage.setItem(storageKey, 'true');
        setHasBeenVisited(true);
      } catch {
        // Ignore sessionStorage errors
      }
    }
  }, [storageKey, hasBeenVisited]);

  return {
    isOpen,
    hasBeenVisited,
    showModal,
    hideModal
  };
}

// Content definitions for each tab
export const tabInfoContent: Record<string, InfoModalContent> = {
  patientSelection: {
    title: "Welcome to ClarityGR",
    subtitle: "Your AI-powered medical records analysis platform",
    sections: [
      {
        title: "Getting Started",
        icon: UserPlus,
        points: [
          "Select an existing patient from the list below to view their documents and reports",
          "Create a new patient by uploading their first medical document",
          "The platform will automatically extract and organize patient information",
          "Each patient has their own secure workspace for documents and reports"
        ]
      },
      {
        title: "Patient Management",
        icon: Users,
        points: [
          "Search patients by ID using the search bar",
          "View summary information including document and report counts",
          "Last activity timestamps help track recent work",
          "Patient data is organized chronologically for easy access"
        ]
      },
      {
        title: "What Happens Next",
        icon: Activity,
        points: [
          "Upload medical documents to the Documents tab",
          "AI will process and extract medical entities automatically",
          "Generate comprehensive MDT reports in the Reports tab",
          "Monitor system performance in the Observability tab"
        ]
      }
    ],
    tips: [
      "Start by selecting an existing patient or upload a document to create a new patient",
      "Patient IDs are automatically detected from uploaded documents",
      "Use the search function to quickly find specific patients",
      "Each patient's workspace is completely isolated and secure"
    ]
  },
  documents: {
    title: "Documents Management",
    subtitle: "Upload, process, and manage patient medical records",
    sections: [
      {
        title: "What you can do here",
        icon: FileText,
        points: [
          "Upload medical documents in various formats (PDF, DOC, images)",
          "View document processing status and extracted patient information",
          "Monitor document parsing and entity extraction progress",
          "Access source documents and their processed versions"
        ]
      },
      {
        title: "Document Processing Pipeline",
        icon: Activity,
        points: [
          "Documents are automatically processed using AI to extract medical entities",
          "Patient IDs are automatically detected and extracted from uploaded documents",
          "Text normalization ensures consistent format across all document types",
          "Entity extraction identifies key medical information like diagnoses, medications, and procedures"
        ]
      },
      {
        title: "Key Features",
        icon: Stethoscope,
        points: [
          "Drag & drop multiple files for batch processing",
          "Real-time processing status updates",
          "Automatic patient ID detection and assignment",
          "Support for various medical document formats"
        ]
      }
    ],
    tips: [
      "Upload documents with clear patient information for better automatic ID detection",
      "Supported formats include PDF, Word documents, and common image formats",
      "Processing time depends on document complexity and length",
      "Check the processing status to ensure all information was extracted correctly"
    ]
  },
  reports: {
    title: "Medical Reports & Analytics",
    subtitle: "Generate comprehensive medical reports and analyze patient data",
    sections: [
      {
        title: "Report Generation",
        icon: BarChart3,
        points: [
          "Generate comprehensive MDT (Multidisciplinary Team) reports",
          "Create standardized medical summaries from processed documents",
          "Export reports in various formats for sharing with medical teams",
          "Track report generation progress with real-time updates"
        ]
      },
      {
        title: "Medical Intelligence",
        icon: TrendingUp,
        points: [
          "AI-powered analysis of patient medical history",
          "Automatic identification of key medical trends and patterns",
          "Integration of data from multiple document sources",
          "Structured presentation of diagnoses, treatments, and outcomes"
        ]
      },
      {
        title: "Team Collaboration",
        icon: Activity,
        points: [
          "Reports designed for multidisciplinary medical team reviews",
          "Standardized format ensures consistency across cases",
          "Easy sharing and distribution of medical summaries",
          "Version tracking for report updates and revisions"
        ]
      }
    ],
    tips: [
      "Ensure documents are fully processed before generating reports",
      "Reports include all available medical entities from uploaded documents",
      "Generated reports can be exported and shared with medical teams",
      "Check settings to customize report templates and preferences"
    ]
  },
  observability: {
    title: "System Observability & Monitoring",
    subtitle: "Monitor platform performance, track processing metrics, and view system health",
    sections: [
      {
        title: "Performance Monitoring",
        icon: Activity,
        points: [
          "Real-time tracking of document processing performance",
          "Monitor AI model response times and accuracy metrics",
          "View system resource utilization and bottlenecks",
          "Track processing queue status and throughput"
        ]
      },
      {
        title: "Health Diagnostics",
        icon: Database,
        points: [
          "Monitor backend service availability and health",
          "Check database connection status and performance",
          "View API endpoint response times and error rates",
          "Track system dependencies and integrations"
        ]
      },
      {
        title: "Analytics & Insights",
        icon: TrendingUp,
        points: [
          "Usage analytics and processing statistics",
          "Error tracking and debugging information",
          "Performance trends and capacity planning data",
          "Quality metrics for AI model outputs"
        ]
      }
    ],
    tips: [
      "Use this section to troubleshoot processing issues",
      "Monitor system performance during high-volume processing",
      "Check health metrics if documents are processing slowly",
      "Analytics help optimize workflow efficiency"
    ]
  }
};