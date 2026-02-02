export interface Translations {
  // Navigation and general
  navigation: {
    documents: string;
    reports: string;
    settings: string;
    observability: string;
  };
  
  // Header and branding
  header: {
    institution: string;
    title: string;
    subtitle: string;
    patient: string;
    generatedOn: string;
    warningBanner: string;
  };
  
  // Patient selector
  patient: {
    selector: {
      label: string;
      placeholder: string;
    };
  };
  
  // Documents section
  documents: {
    title: string;
    subtitle: string;
    documentsFor: string;
    upload: string;
    fetchFromEhr: string;
    refresh: string;
    uploadModal: {
      title: string;
      close: string;
    };
    status: {
      done: string;
      processing: string;
      failed: string;
      queued: string;
    };
    empty: {
      title: string;
      description: string;
    };
    info: {
      type: string;
      source: string;
      category: string;
      entities: string;
      extracted: string;
      created: string;
      processed: string;
      ago: string;
      extractedEntities: string;
      uploadedAgo: string;
      processedAgo: string;
    };
    preview: {
      title: string;
      patientId: string;
      type: string;
      status: string;
      download: string;
      loading: string;
      error: string;
      retry: string;
      search: string;
      tabs: {
        content: string;
        ocr: string;
        data: string;
      };
      errors: {
        loadFailed: string;
      };
    };
  };
  
  // File upload
  upload: {
    title: string;
    subtitle: string;
    settings: string;
    dropzone: {
      title: string;
      subtitle: string;
      browse: string;
    };
          form: {
        type: string;
        source: string;
        notes: string;
        notesOptional: string;
        upload: string;
        autoDetect: string;
        autoDetectDescription: string;
        sourceAutoDetect: string;
        sourceAutoDetectDescription: string;
        replacementNotice: string;
      };
    types: {
      consultation: string;
      lab: string;
      labReport: string;
      imaging: string;
      pathology: string;
      discharge: string;
      other: string;
      diagnosis: string;
      treatmentPlan: string;
      medicalHistory: string;
      prescription: string;
      referral: string;
      operationReport: string;
    };
    sources: {
      hospital: string;
      clinic: string;
      lab: string;
      laboratory: string;
      external: string;
      patient: string;
      gp: string;
      specialist: string;
      pharmacy: string;
    };
    progress: {
      uploading: string;
      processing: string;
      completed: string;
      error: string;
    };
  };
  
  // Reports section
  reports: {
    title: string;
    subtitle: string;
    generate: string;
    generateNew: string;
    reportsFor: string;
    empty: {
      title: string;
      description: string;
    };
    status: {
      completed: string;
      processing: string;
      failed: string;
    };
    info: {
      generatedAgo: string;
      entities: string;
      extracted: string;
      documents: string;
      processed: string;
      size: string;
      version: string;
      words: string;
      download: string;
      view: string;
      done: string;
    };
    generation: {
      title: string;
      progress: string;
      estimatedTime: string;
    };
  };
  
  // Report generation dialog
  reportGeneration: {
    title: string;
    subtitle: string;
    settings: {
      title: string;
      processing: {
        title: string;
        firstMatch: string;
        multipleMatch: string;
        aggregateAll: string;
      };
      entities: {
        title: string;
        all: string;
        custom: string;
      };
    };
    generate: string;
    cancel: string;
  };
  
  // Report viewer
  reportViewer: {
    title: string;
    summary: {
      title: string;
      foundEntities: string;
      notFound: string;
      categories: string;
    };
    entityTypes: {
      unique: string;
      multiple: string;
      aggregate: string;
    };
    categories: {
      nom: string;
      rappelClinique: string;
      caracteristiques: string;
      motifPresentation: string;
      proposition: string;
    };
    notFound: {
      badge: string;
      message: string;
      description: string;
      separator: string;
    };
    noEntities: string;
    metadata: {
      source: string;
      section: string;
      page: string;
    };
    actions: {
      close: string;
      download: string;
      view: string;
    };
  };
  
  // Settings
  settings: {
    title: string;
    apiUrl: {
      title: string;
      description: string;
      placeholder: string;
    };
    language: {
      title: string;
      description: string;
      english: string;
      french: string;
    };
    save: string;
    cancel: string;
  };
  
  // Common actions
  actions: {
    save: string;
    cancel: string;
    delete: string;
    edit: string;
    view: string;
    download: string;
    upload: string;
    refresh: string;
    close: string;
    showMore: string;
    showLess: string;
  };
  
  // Common messages
  messages: {
    loading: string;
    error: string;
    success: string;
    noData: string;
    loadingPatientData: string;
  };
  
  // Time and dates
  time: {
    ago: string;
    now: string;
    minutes: string;
    hours: string;
    days: string;
  };

  // Disclaimer
  disclaimer: {
    modalShort: {
      headline: string;
      body: string[];
      checkbox: string;
    };
    modal: {
      title: string;
      subtitle: string;
      mainWarning: string;
      aiNotification: {
        title: string;
        description: string;
      };
      clinicalUseProhibited: {
        title: string;
        items: string[];
      };
      healthcareProfessionals: {
        title: string;
        description: string;
        items: string[];
      };
      complianceStatus: {
        title: string;
        euAiAct: string;
        medicalDevice: string;
        dataProtection: string;
      };
      dataNotice: {
        title: string;
        description: string;
      };
      acknowledgment: {
        title: string;
        items: string[];
      };
      footer: {
        title: string;
        contact: string;
      };
      buttons: {
        exit: string;
        continue: string;
      };
    };
    report: {
      title: string;
      subtitle: string;
    };
  };

  // Observability
  observability: {
    title: string;
    refresh: string;
    filters: {
      startTime: string;
      endTime: string;
      llm: string;
      docsHash: string;
      all: string;
    };
    table: {
      timeUtc: string;
      patientId: string;
      llm: string;
      foundEntities: string;
      elapsed: string;
      docsHash: string;
      entitiesPerBatch: string;
      aggBatch: string;
      maxSize: string;
      accuracy: string;
      evaluate: string;
      loading: string;
      noData: string;
    };
    evaluation: {
      view: string;
      evaluate: string;
      uploadGT: string;
      viewResults: string;
      runEvaluationExisting: string;
      uploadGroundTruthEvaluate: string;
      runningTitle: string;
      runningDescription: string;
    };
  };
}

export const translations: Translations = {
  navigation: {
    documents: 'Documents',
    reports: 'Reports',
    settings: 'Settings',
    observability: 'Observability',
  },
  header: {
    institution: 'MongoDB Healthcare',
    title: 'AI Medical Document Processing',
    subtitle: 'MDT Report Generation',
    patient: 'Patient',
    generatedOn: 'Generated on',
    warningBanner: '',
  },
  patient: {
    selector: {
      label: 'Select Patient',
      placeholder: 'Enter patient ID',
    },
  },
  documents: {
    title: 'Patient Documents',
    subtitle: 'document for patient',
    documentsFor: 'documents for patient',
    upload: 'Upload Document',
    fetchFromEhr: 'Fetch from EHR',
    refresh: 'Refresh',
    uploadModal: {
      title: 'Upload Document',
      close: 'Close',
    },
    status: {
      done: 'Processed',
      processing: 'Processing',
      failed: 'Failed',
      queued: 'Queued',
    },
    empty: {
      title: 'No documents found',
      description: 'Upload some documents to get started with document processing.',
    },
    info: {
      type: 'Type',
      source: 'Source',
      category: 'Category',
      entities: 'Entities',
      extracted: 'extracted',
      created: 'Created',
      processed: 'Processed',
      ago: 'ago',
      extractedEntities: 'entities extracted',
      uploadedAgo: 'uploaded',
      processedAgo: 'processed',
    },
    preview: {
      title: 'Document Preview',
      patientId: 'Patient ID',
      type: 'Type',
      status: 'Status',
      download: 'Download',
      loading: 'Loading document...',
      error: 'Error',
      retry: 'Retry',
      search: 'Search...',
      tabs: {
        content: 'Content',
        ocr: 'OCR Text',
        data: 'Extracted Data',
      },
      errors: {
        loadFailed: 'Failed to load document content',
      },
    },
  },
  upload: {
    title: 'Upload Documents',
    subtitle: 'Upload medical documents for patient',
    settings: 'Upload Settings',
    dropzone: {
      title: 'Drag and drop files here',
      subtitle: 'or click to browse files',
      browse: 'Browse Files',
    },
    form: {
      type: 'Document Type',
      source: 'Source',
      notes: 'Notes (Optional)',
      notesOptional: 'Notes (Optional)',
      upload: 'Upload Document',
      autoDetect: 'Other (Auto-detect during processing)',
      autoDetectDescription: 'Document type will be automatically detected during processing',
      sourceAutoDetect: 'Auto-detect source',
      sourceAutoDetectDescription: 'Document source will be automatically detected',
      replacementNotice: '📄 Note: Uploading a file with the same name will replace the existing document',
    },
    types: {
      consultation: 'Consultation Report',
      lab: 'Laboratory Results',
      labReport: 'Lab Report',
      imaging: 'Imaging Report',
      pathology: 'Pathology Report',
      discharge: 'Discharge Summary',
      other: 'Other',
      diagnosis: 'Diagnosis',
      treatmentPlan: 'Treatment Plan',
      medicalHistory: 'Medical History',
      prescription: 'Prescription',
      referral: 'Referral',
      operationReport: 'Operation Report',
    },
    sources: {
      hospital: 'Hospital',
      clinic: 'Clinic',
      lab: 'Laboratory',
      laboratory: 'Laboratory',
      external: 'External Provider',
      patient: 'Patient',
      gp: 'General Practitioner',
      specialist: 'Specialist',
      pharmacy: 'Pharmacy',
    },
    progress: {
      uploading: 'Uploading',
      processing: 'Processing',
      completed: 'Completed',
      error: 'Error',
    },
  },
  reports: {
    title: 'MDT Reports',
    subtitle: 'report for patient',
    generate: 'Generate New Report',
    generateNew: 'Generate New Report',
    reportsFor: 'reports for patient',
    empty: {
      title: 'No reports available',
      description: 'Generate your first MDT report from the uploaded documents.',
    },
    status: {
      completed: 'Completed',
      processing: 'Processing',
      failed: 'Failed',
    },
    info: {
      generatedAgo: 'generated',
      entities: 'Entities',
      extracted: 'extracted',
      documents: 'Documents',
      processed: 'processed',
      size: 'Size',
      version: 'Version',
      words: 'words',
      download: 'Download',
      view: 'View',
      done: 'Done',
    },
    generation: {
      title: 'Generating MDT Report',
      progress: 'Progress',
      estimatedTime: 'Estimated time remaining',
    },
  },
  reportGeneration: {
    title: 'Generate MDT Report',
    subtitle: 'Configure report generation settings',
    settings: {
      title: 'Generation Settings',
      processing: {
        title: 'Processing Types',
        firstMatch: 'First Match (fastest)',
        multipleMatch: 'Multiple Matches (comprehensive)',
        aggregateAll: 'Aggregate All (detailed)',
      },
      entities: {
        title: 'Entity Selection',
        all: 'All available entities',
        custom: 'Custom selection',
      },
    },
    generate: 'Generate Report',
    cancel: 'Cancel',
  },
  reportViewer: {
    title: 'Report Viewer',
    summary: {
      title: 'Entity Categories Summary',
      foundEntities: 'Found Entities',
      notFound: 'Not Found',
      categories: 'Categories Found',
    },
    entityTypes: {
      unique: 'UNIQUE',
      multiple: 'MULTIPLE',
      aggregate: 'AGGREGATE',
    },
    categories: {
      nom: 'Patient Identity',
      rappelClinique: 'Clinical Summary',
      caracteristiques: 'Patient & Tumor Characteristics',
      motifPresentation: 'Presentation Reason',
      proposition: 'MDT Recommendations',
    },
    notFound: {
      badge: 'Not Found',
      message: 'No data found in processed documents',
      description: 'This entity was expected but not found in any of the processed documents. Consider adding this information manually or reviewing the source documents.',
      separator: 'Expected but not found',
    },
    noEntities: 'No entities found for this category.',
    metadata: {
      source: 'Source',
      section: 'Section',
      page: 'Page',
    },
    actions: {
      close: 'Close',
      download: 'Download PDF',
      view: 'View',
    },
  },
  settings: {
    title: 'Settings',
    apiUrl: {
      title: 'API Base URL',
      description: 'Configure the backend API endpoint',
      placeholder: 'Enter API URL',
    },
    language: {
      title: 'Language',
      description: 'Choose interface language',
      english: 'English',
      french: 'Français',
    },
    save: 'Save Changes',
    cancel: 'Cancel',
  },
  actions: {
    save: 'Save',
    cancel: 'Cancel',
    delete: 'Delete',
    edit: 'Edit',
    view: 'View',
    download: 'Download',
    upload: 'Upload',
    refresh: 'Refresh',
    close: 'Close',
    showMore: 'Show more',
    showLess: 'Show less',
  },
  messages: {
    loading: 'Loading...',
    error: 'Error',
    success: 'Success',
    noData: 'No data available',
    loadingPatientData: 'Loading patient data...',
  },
  time: {
    ago: 'ago',
    now: 'now',
    minutes: 'minutes',
    hours: 'hours',
    days: 'days',
  },
  observability: {
    title: 'Observability',
    refresh: 'Refresh',
    filters: {
      startTime: 'Start (UTC)',
      endTime: 'End (UTC)',
      llm: 'LLM',
      docsHash: 'Docs hash',
      all: 'All',
    },
    table: {
      timeUtc: 'Time (UTC)',
      patientId: 'Patient ID',
      llm: 'LLM',
      foundEntities: 'Found Entities',
      elapsed: 'Elapsed',
      docsHash: 'Docs Hash',
      entitiesPerBatch: 'Ent/b',
      aggBatch: 'Agg/b',
      maxSize: 'MaxSz',
      accuracy: 'Acc',
      evaluate: 'Evaluate',
      loading: 'Loading…',
      noData: 'No data',
    },
    evaluation: {
      view: 'View',
      evaluate: 'Evaluate',
      uploadGT: 'Upload GT',
      viewResults: 'View evaluation results',
      runEvaluationExisting: 'Run evaluation with existing GT',
      uploadGroundTruthEvaluate: 'Upload ground truth and evaluate',
      runningTitle: 'Running Evaluation...',
      runningDescription: 'Comparing entities and calculating scores...',
    },
  },
  disclaimer: {
    modalShort: {
      headline: 'PROOF OF CONCEPT — NOT FOR CLINICAL USE',
      body: [
        'This tool is a demonstration only. Do not use for clinical decisions.',
        'Do not enter any real patient data.'
      ],
      checkbox: 'I have read and understand.'
    },
    modal: {
      title: 'PROOF OF CONCEPT - NOT FOR CLINICAL USE',
      subtitle: 'IMPORTANT MEDICAL DISCLAIMER',
      mainWarning: 'This application is a PROOF OF CONCEPT ONLY and is NOT approved, certified, or compliant with the EU AI Act or medical device regulations.',
      aiNotification: {
        title: '🤖 AI SYSTEM NOTIFICATION (EU AI Act Requirement)',
        description: 'You are interacting with an artificial intelligence system. This chatbot uses large language models and is not a human healthcare professional.',
      },
      clinicalUseProhibited: {
        title: '⛔ CLINICAL USE PROHIBITED',
        items: [
          'NOT for use with real patients or clinical decision-making',
          'NOT a substitute for professional medical judgment',
          'NOT validated for diagnostic or therapeutic purposes',
          'NOT compliant with medical device or AI Act requirements',
        ],
      },
      healthcareProfessionals: {
        title: '👨‍⚕️ FOR HEALTHCARE PROFESSIONALS ONLY',
        description: 'This demonstration is intended solely for:',
        items: [
          'Educational and evaluation purposes',
          'Technology assessment by qualified healthcare professionals',
          'Internal testing and development feedback',
        ],
      },
      complianceStatus: {
        title: '⚖️ COMPLIANCE STATUS',
        euAiAct: 'EU AI Act: NOT COMPLIANT - Pending full regulatory assessment',
        medicalDevice: 'Medical Device Regulation (MDR): NOT CERTIFIED',
        dataProtection: 'Data Protection: Demonstration purposes only',
      },
      dataNotice: {
        title: '🔒 DATA NOTICE',
        description: 'This demonstration may process data for testing purposes only. Do not input real patient data or confidential medical information.',
      },
      acknowledgment: {
        title: 'Before accessing this proof of concept, please confirm:',
        items: [
          'I understand this is NOT for clinical use',
          'I am a healthcare professional using this for evaluation purposes only',
          'I will not input real patient data or use this for patient care',
          'I acknowledge this is an AI system and not a human healthcare professional',
        ],
      },
      footer: {
        title: 'FOR DEMONSTRATION AND EVALUATION PURPOSES ONLY',
        contact: 'Contact your system administrator for compliance timeline and questions',
      },
      buttons: {
        exit: 'Exit',
        continue: 'Continue',
      },
    },
    report: {
      title: '═══ PROOF OF CONCEPT REPORT ═══',
      subtitle: 'NOT FOR CLINICAL USE',
    },
  },
}; 