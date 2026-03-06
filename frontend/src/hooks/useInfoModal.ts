import { useState, useCallback, useEffect } from 'react';
import { FileText, BarChart3, Eye, Upload, Stethoscope, Activity, TrendingUp, Database, Users, UserPlus, Pencil } from 'lucide-react';
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
  const [buttonPosition, setButtonPosition] = useState<{ x: number; y: number } | null>(null);

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
      // For patient selection, show from center (no info button exists)
      if (tabId === 'patientSelection') {
        setButtonPosition(null);
        setIsOpen(true);
      } else {
        // For other tabs, try to get the info button position
        // Use a small delay to ensure the button is rendered
        const timer = setTimeout(() => {
          // Find all InfoButtons by their unique class pattern
          // InfoButtons have classes like "inline-flex items-center justify-center" and contain Info icon
          const infoButtons = Array.from(document.querySelectorAll('button')).filter(btn => 
            btn.className.includes('inline-flex') && 
            btn.className.includes('items-center') &&
            btn.className.includes('justify-center') &&
            btn.querySelector('.lucide-info')
          );
          
          // Tab order: documents (0), reports (1), observability (2)
          const tabOrder = ['documents', 'reports', 'observability'];
          const tabIndex = tabOrder.indexOf(tabId);
          
          if (tabIndex >= 0 && infoButtons[tabIndex]) {
            const targetButton = infoButtons[tabIndex];
            const rect = targetButton.getBoundingClientRect();
            const buttonCenter = {
              x: rect.left + rect.width / 2,
              y: rect.top + rect.height / 2
            };
            setButtonPosition(buttonCenter);
          } else {
            // Fallback to center if button not found
            setButtonPosition(null);
          }
          
          setIsOpen(true);
        }, 100);

        return () => clearTimeout(timer);
      }
    }
  }, [isActive, hasBeenVisited, isOpen, tabId]);

  const showModal = useCallback((position?: { x: number; y: number }) => {
    // Prevent triggering if already open
    if (isOpen) return;
    
    if (position) {
      setButtonPosition(position);
    }
    setIsOpen(true);
  }, [isOpen]);

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
    hideModal,
    buttonPosition
  };
}

// Content definitions for each tab
export const tabInfoContent: Record<string, InfoModalContent> = {
  patientSelection: {
    title: "Welcome to the AI-Powered Medical Report Generator",
    subtitle: "Your AI Assistant to turn unstructured medical sources into comprehensive reports",
    sections: [

      {
        title: "What is this platform?",
        icon: Eye,
        description: "This platform is designed to help medical professionals quickly generate comprehensive reports from unstructured medical documents. By using advanced AI as an ally, it extracts key information and organizes it into structured formats for easy review and analysis.",
      },

      {title: "What you can do here",
        icon: Upload,
        numbered: true,
        points: [
          "Explore different types of unstructured medical sources",
          "Select documents to process and supervise the processing pipeline",
          "Define medical entities and relationships for accurate information extraction",
          "Generate comprehensive MDT reports according to your needs", 
          "Compare generated reports with Ground Truth documents to ensure accuracy and completeness"
          
    ] },

      {
        title: "Getting Started",
        icon: UserPlus,
        description: "Start by selecting an existing patient from the list. Then:",
        points: [
          "Explore unprocessed available documents in the Documents tab",
          "Generate comprehensive reports in the Reports tab",
          "Monitor system performance and processing metrics in the Observability tab"
        ]
      },
      // {
      //   title: "Key Features",
      //   icon: Activity,
      //   description: "This platform has a lot to offer! Here are some of the key features to help you get the most out of it:",
      //   points: [
      //     "Customizable report templates to fit your specific needs. Easily adjust the structure and content of generated reports to match your requirements.",
      //     "AI-powered entity extraction that identifies key medical information such as diagnoses, medications, procedures, and more.",
      //     "Different LLM models to choose from, allowing you to select the one that best fits your use case and preferences.",
      //     "Ground Truth comparison to validate the accuracy and completeness of generated reports against original source documents."
      //   ]
      // }
    ],
    tips: [
      "Select a patient to get started and explore the platform's capabilities",
      "Use the info buttons in each tab to learn more about specific features and workflows",
      "Configure your report templates to tailor the output according to your needs",
      "Check the fully detailed PDF reports and test them against yous Ground Truth documents"
    ]
  },
  documents: {
    title: "Documents Management",
    subtitle: "Select, process, and manage patient medical documents",
    sections: [
      {
        title: "What you can do here",
        icon: FileText,
        description: "This section will allow you to manage the patient's medical documents easily. You can explore unprocessed documents, initiate the processing pipeline and review the results before you create new reports.",

      },
      {
        title: "Document Processing Pipeline",
        icon: Activity,
        numbered: true,
        description: "The document processing pipeline is used to extract structured information from unstructured medical documents:",
        points: [
          "Unstructured documents for the patient are listed in the 'Incoming Documents' tab.",
          "The selected documents are pre-processed to convert them into semi-structured data formats.",
          "Once processed, the extracted information is available in the 'Processed Documents' tab.",
        ]
      },
      // {
      //   title: "Key Features",
      //   icon: Stethoscope,
      //   points: [
      //     "Select specific documents to process or re-process as needed",
      //     "Real-time monitoring of processing status and progress",
      //     "Review extracted information before generating reports",
      //     "Supports a wide range of document types and formats for comprehensive coverage"
      //   ]
      // }
    ],

  },
  reports: {
    title: "Medical Reports & Analytics",
    subtitle: "Generate comprehensive medical reports and analyze patient data",
    sections: [
      {
        title: "What is an MDT Report?",
        icon: BarChart3,
        description: "An MDT (Multidisciplinary Team) report is a comprehensive summary of a patient's medical history, diagnoses, treatments, and outcomes. It is designed to facilitate communication and collaboration among healthcare professionals by providing a structured overview of the patient's case.",
      },

      {
        title: "Customizable Report Templates",
        icon: Pencil,
        description: "This MDT reports can be customized to your team's needs creating your own medical entity templates. Define the description, filters and extraction rules for each medical entity",
      },

      // {
      //   title: "What you can do here",
      //   icon: FileText,
      //   points: [
      //     "Create your own medical entity templates to customize the structure and content of generated reports",
      //     "Create comprehensive MDT reports tailored to your specific needs and preferences",
      //     "Download generated reports in PDF format for easy sharing and review",
      //   ]
      // },
      {
        title: "How to create a report",
        icon: Users,
        numbered: true,
        points: [
          "Start by defining your medical entity template and set it to  'Active'. This will allow you to customize the entities in your generated reports.",
          "Once you have your templates set up, click on 'Generate Report'. The platform will use the processed documents and your defined templates to create a comprehensive MDT report using AI.",
          "After the report is generated, you can review it directly in the platform or download it as a PDF for easy sharing with your medical team."
        ]}
    ],
      tips: [
        "Check which template is active before generating a report to ensure it includes the entities you need",
        "Use the PDF download option to share reports with your team or for offline review",
        "Customize your templates to tailor the generated reports according to your specific requirements",
      ]},
  observability: {
    title: "System Observability & Monitoring",
    subtitle: "Monitor platform performance, track processing metrics, and view report details.",
    sections: [
      {
        title: "What you can do here",
        icon: FileText,
        description: "Keep an eye on the performance of the document processing pipeline and report generation:",
        points: [
          "Review all the details of the generated reports",
          "Select Ground Truth documents to compare with the generated reports and validate their accuracy and completeness",
          "Allow AI to analyze the differences between the generated report and the Ground Truth document to identify potential gaps or missing information in the generated report"
        ]
      },
      {
        title: "Analytics & Insights",
        icon: TrendingUp,
        points: [
          "F1 Score",
          "LLM Performance Metrics",
          "Matched entities and relationships",
          "Comparison between extracted information and Ground Truth documents"
        ]
      }
    ],
  }
};