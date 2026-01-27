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

export const translations: Record<'en' | 'fr', Translations> = {
  en: {
    navigation: {
      documents: 'Documents',
      reports: 'Reports',
      settings: 'Settings',
      observability: 'Observability',
    },
    header: {
      institution: 'Institut Gustave Roussy',
      title: 'AI Medical Document Processing',
      subtitle: 'MDT Report Generation',
      patient: 'Patient',
      generatedOn: 'Generated on',
      warningBanner: '⚠️ PROOF OF CONCEPT - NOT FOR CLINICAL USE ⚠️',
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
  },
  fr: {
    navigation: {
      documents: 'Documents',
      reports: 'Rapports',
      settings: 'Paramètres',
      observability: 'Observabilité',
    },
    header: {
      institution: 'Institut Gustave Roussy',
      title: 'Traitement IA de Documents Médicaux',
      subtitle: 'Génération de Rapports RCP',
      patient: 'Patient',
      generatedOn: 'Généré le',
      warningBanner: '⚠️ PREUVE DE CONCEPT - PAS D\'USAGE CLINIQUE ⚠️',
    },
    patient: {
      selector: {
        label: 'Sélectionner un Patient',
        placeholder: 'Saisir ID patient',
      },
    },
    documents: {
      title: 'Documents du Patient',
      subtitle: 'document pour le patient',
      documentsFor: 'documents pour le patient',
      upload: 'Téléverser Document',
      fetchFromEhr: 'Récupérer depuis DPI',
      refresh: 'Actualiser',
      uploadModal: {
        title: 'Téléverser Document',
        close: 'Fermer',
      },
      status: {
        done: 'Traité',
        processing: 'En cours',
        failed: 'Échec',
        queued: 'En attente',
      },
      empty: {
        title: 'Aucun document trouvé',
        description: 'Téléversez des documents pour commencer le traitement.',
      },
      info: {
        type: 'Type',
        source: 'Source',
        category: 'Catégorie',
        entities: 'Entités',
        extracted: 'extraites',
        created: 'Créé',
        processed: 'Traité',
        ago: 'il y a',
        extractedEntities: 'entités extraites',
        uploadedAgo: 'téléversé',
        processedAgo: 'traité',
      },
    },
    upload: {
      title: 'Téléverser Documents',
      subtitle: 'Téléverser des documents médicaux pour le patient',
      settings: 'Paramètres de Téléversement',
      dropzone: {
        title: 'Glissez-déposez vos fichiers ici',
        subtitle: 'ou cliquez pour parcourir',
        browse: 'Parcourir Fichiers',
      },
      form: {
        type: 'Type de Document',
        source: 'Source',
        notes: 'Notes (Optionnel)',
        notesOptional: 'Notes (Optionnel)',
        upload: 'Téléverser Document',
        autoDetect: 'Autre (Détection automatique pendant le traitement)',
        autoDetectDescription: 'Le type de document sera automatiquement détecté pendant le traitement',
        sourceAutoDetect: 'Détection automatique de la source',
        sourceAutoDetectDescription: 'La source du document sera automatiquement détectée',
        replacementNotice: '📄 Note : Téléverser un fichier avec le même nom remplacera le document existant',
      },
      types: {
        consultation: 'Rapport de Consultation',
        lab: 'Résultats de Laboratoire',
        labReport: 'Rapport de Laboratoire',
        imaging: 'Rapport d\'Imagerie',
        pathology: 'Rapport d\'Anatomopathologie',
        discharge: 'Résumé de Sortie',
        other: 'Autre',
        diagnosis: 'Diagnostic',
        treatmentPlan: 'Plan de Traitement',
        medicalHistory: 'Historique Médical',
        prescription: 'Prescription',
        referral: 'Orientation',
        operationReport: 'Rapport d\'Opération',
      },
      sources: {
        hospital: 'Hôpital',
        clinic: 'Clinique',
        lab: 'Laboratoire',
        laboratory: 'Laboratoire',
        external: 'Prestataire Externe',
        patient: 'Patient',
        gp: 'Médecin Généraliste',
        specialist: 'Spécialiste',
        pharmacy: 'Pharmacie',
      },
      progress: {
        uploading: 'Téléversement',
        processing: 'Traitement',
        completed: 'Terminé',
        error: 'Erreur',
      },
    },
    reports: {
      title: 'Rapports RCP',
      subtitle: 'rapport pour le patient',
      generate: 'Générer Nouveau Rapport',
      generateNew: 'Générer Nouveau Rapport',
      reportsFor: 'rapports pour le patient',
      empty: {
        title: 'Aucun rapport disponible',
        description: 'Générez votre premier rapport RCP à partir des documents téléversés.',
      },
      status: {
        completed: 'Terminé',
        processing: 'En cours',
        failed: 'Échec',
      },
      info: {
        generatedAgo: 'généré',
        entities: 'Entités',
        extracted: 'extraites',
        documents: 'Documents',
        processed: 'traités',
        size: 'Taille',
        version: 'Version',
        words: 'mots',
        download: 'Télécharger',
        view: 'Voir',
        done: 'Terminé',
      },
      generation: {
        title: 'Génération du Rapport RCP',
        progress: 'Progression',
        estimatedTime: 'Temps restant estimé',
      },
    },
    reportGeneration: {
      title: 'Générer Rapport RCP',
      subtitle: 'Configurer les paramètres de génération',
      settings: {
        title: 'Paramètres de Génération',
        processing: {
          title: 'Types de Traitement',
          firstMatch: 'Première Correspondance (rapide)',
          multipleMatch: 'Correspondances Multiples (complet)',
          aggregateAll: 'Agréger Tout (détaillé)',
        },
        entities: {
          title: 'Sélection d\'Entités',
          all: 'Toutes les entités disponibles',
          custom: 'Sélection personnalisée',
        },
      },
      generate: 'Générer Rapport',
      cancel: 'Annuler',
    },
    reportViewer: {
      title: 'Visualiseur de Rapport',
      summary: {
        title: 'Résumé des Catégories d\'Entités',
        foundEntities: 'Entités Trouvées',
        notFound: 'Non Trouvées',
        categories: 'Catégories Trouvées',
      },
      entityTypes: {
        unique: 'UNIQUE',
        multiple: 'MULTIPLE',
        aggregate: 'AGRÉGÉ',
      },
      categories: {
        nom: 'Identité Patient',
        rappelClinique: 'Résumé Clinique',
        caracteristiques: 'Caractéristiques Patient & Tumorales',
        motifPresentation: 'Motif de Présentation',
        proposition: 'Recommandations RCP',
      },
      notFound: {
        badge: 'Non Trouvé',
        message: 'Aucune donnée trouvée dans les documents traités',
        description: 'Cette entité était attendue mais n\'a pas été trouvée dans les documents traités. Considérez ajouter cette information manuellement ou revoir les documents source.',
        separator: 'Attendu mais non trouvé',
      },
      noEntities: 'Aucune entité trouvée pour cette catégorie.',
      metadata: {
        source: 'Source',
        section: 'Section',
        page: 'Page',
      },
      actions: {
        close: 'Fermer',
        download: 'Télécharger PDF',
        view: 'Voir',
      },
    },
    settings: {
      title: 'Paramètres',
      apiUrl: {
        title: 'URL de Base API',
        description: 'Configurer l\'endpoint de l\'API backend',
        placeholder: 'Saisir URL API',
      },
      language: {
        title: 'Langue',
        description: 'Choisir la langue de l\'interface',
        english: 'English',
        french: 'Français',
      },
      save: 'Enregistrer',
      cancel: 'Annuler',
    },
    actions: {
      save: 'Enregistrer',
      cancel: 'Annuler',
      delete: 'Supprimer',
      edit: 'Modifier',
      view: 'Voir',
      download: 'Télécharger',
      upload: 'Téléverser',
      refresh: 'Actualiser',
      close: 'Fermer',
      showMore: 'Voir plus',
      showLess: 'Voir moins',
    },
    messages: {
      loading: 'Chargement...',
      error: 'Erreur',
      success: 'Succès',
      noData: 'Aucune donnée disponible',
      loadingPatientData: 'Chargement des données patient...',
    },
    time: {
      ago: 'il y a',
      now: 'maintenant',
      minutes: 'minutes',
      hours: 'heures',
      days: 'jours',
    },
    observability: {
      title: 'Observabilité',
      refresh: 'Actualiser',
      filters: {
        startTime: 'Début (UTC)',
        endTime: 'Fin (UTC)',
        llm: 'LLM',
        docsHash: 'Hash docs',
        all: 'Tous',
      },
      table: {
        timeUtc: 'Heure (UTC)',
        patientId: 'ID Patient',
        llm: 'LLM',
        foundEntities: 'Entités trouvées',
        elapsed: 'Durée',
        docsHash: 'Hash docs',
        entitiesPerBatch: 'Ent/lot',
        aggBatch: 'Agrég/lot',
        maxSize: 'Taille max',
        accuracy: 'Précision',
        evaluate: 'Évaluer',
        loading: 'Chargement…',
        noData: 'Aucune donnée',
      },
      evaluation: {
        view: 'Voir',
        evaluate: 'Évaluer',
        uploadGT: 'Téléverser GT',
        viewResults: 'Voir les résultats d\'évaluation',
        runEvaluationExisting: 'Lancer l\'évaluation avec GT existant',
        uploadGroundTruthEvaluate: 'Téléverser la vérité terrain et évaluer',
        runningTitle: 'Évaluation en cours...',
        runningDescription: 'Comparaison des entités et calcul des scores...',
      },
    },
    disclaimer: {
      modalShort: {
        headline: 'PREUVE DE CONCEPT — PAS D’USAGE CLINIQUE',
        body: [
          "N'utilisez pas les résultats de cette solution",
          "comme données médicales car elle n'a pas été certifiée."
        ],
        checkbox: 'Je confirme avoir lu et compris.'
      },
      modal: {
        title: 'PREUVE DE CONCEPT - PAS D\'USAGE CLINIQUE',
        subtitle: 'AVERTISSEMENT MÉDICAL IMPORTANT',
        mainWarning: 'Cette application est une PREUVE DE CONCEPT UNIQUEMENT et n\'est PAS approuvée, certifiée ou conforme à l\'AI Act européen ou aux réglementations des dispositifs médicaux.',
        aiNotification: {
          title: '🤖 NOTIFICATION SYSTÈME IA (Exigence AI Act UE)',
          description: 'Vous interagissez avec un système d\'intelligence artificielle. Ce chatbot utilise de grands modèles de langage et n\'est pas un professionnel de santé humain.',
        },
        clinicalUseProhibited: {
          title: '⛔ USAGE CLINIQUE INTERDIT',
          items: [
            'PAS d\'utilisation avec de vrais patients ou pour la prise de décision clinique',
            'PAS un substitut au jugement médical professionnel',
            'PAS validé à des fins diagnostiques ou thérapeutiques',
            'PAS conforme aux exigences des dispositifs médicaux ou de l\'AI Act',
          ],
        },
        healthcareProfessionals: {
          title: '👨‍⚕️ POUR PROFESSIONNELS DE SANTÉ UNIQUEMENT',
          description: 'Cette démonstration est destinée exclusivement à :',
          items: [
            'Fins éducatives et d\'évaluation',
            'Évaluation technologique par des professionnels de santé qualifiés',
            'Tests internes et retours de développement',
          ],
        },
        complianceStatus: {
          title: '⚖️ STATUT DE CONFORMITÉ',
          euAiAct: 'AI Act UE : NON CONFORME - Évaluation réglementaire complète en attente',
          medicalDevice: 'Règlement Dispositifs Médicaux (RDM) : NON CERTIFIÉ',
          dataProtection: 'Protection des données : Fins de démonstration uniquement',
        },
        dataNotice: {
          title: '🔒 AVIS DONNÉES',
          description: 'Cette démonstration peut traiter des données à des fins de test uniquement. N\'entrez pas de données patients réelles ou d\'informations médicales confidentielles.',
        },
        acknowledgment: {
          title: 'Avant d\'accéder à cette preuve de concept, veuillez confirmer :',
          items: [
            'Je comprends que ce n\'est PAS pour usage clinique',
            'Je suis un professionnel de santé utilisant ceci à des fins d\'évaluation uniquement',
            'Je n\'entrerai pas de données patients réelles ni ne l\'utiliserai pour les soins aux patients',
            'Je reconnais que c\'est un système IA et non un professionnel de santé humain',
          ],
        },
        footer: {
          title: 'À DES FINS DE DÉMONSTRATION ET D\'ÉVALUATION UNIQUEMENT',
          contact: 'Contactez votre administrateur système pour le calendrier de conformité et les questions',
        },
        buttons: {
          exit: 'Quitter',
          continue: 'Continuer',
        },
      },
              report: {
          title: '═══ RAPPORT PREUVE DE CONCEPT ═══',
          subtitle: 'PAS POUR USAGE CLINIQUE',
        },
    },
  },
}; 