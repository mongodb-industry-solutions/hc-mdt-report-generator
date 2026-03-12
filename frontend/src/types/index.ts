export interface PatientDocument {
  uuid: string;
  patient_id: string | null;  // Can be null for UUID-first uploads until extraction
  type: string;
  source?: string;
  status: 'queued' | 'processing' | 'done' | 'failed' | 'completed' | 'processed' | 'error' | 'requires_manual_input';
  patient_id_changed?: boolean;
  original_patient_id?: string;
  notes?: string;
  filename?: string;
  file_path?: string;
  file_content?: string; // Base64 encoded file content
  created_at: string;
  updated_at: string;
  processing_started_at?: string;
  processing_completed_at?: string;
  errors: string[];
  parsed_document_uuid?: string;
  
  // OCR Results
  ocr_text?: string;
  character_count?: number;
  word_count?: number;
  ocr_completed_at?: string;
  ocr_metadata?: Record<string, any>;
  
  // Document Categorization Results
  document_category?: string;
  document_type?: string;
  categorization_completed_at?: string;
  
  // Structured Data Extraction Results
  extracted_data?: Record<string, any>;
  extraction_metadata?: Record<string, any>;
  extraction_status?: string;
  extraction_completed_at?: string;
}

export interface PaginatedDocuments {
  total: number;
  page: number;
  page_size: number;
  items: PatientDocument[];
}

export interface ReportEntity {
  entity_name: string;
  value?: string | string[];
  values?: Array<{
    value: string;
    metadata: {
      filename: string;
      created_at: string;
      section_id: string;
      page_id: number;
    };
  }>;
  aggregated_value?: string;
  processing_type: 'first_match' | 'multiple_match' | 'aggregate_all_matches';
  metadata?: {
    filename: string;
    created_at: string;
    section_id: string;
    page_id: number;
    // For aggregate entities
    source_count?: number;
    sources?: Array<{
      filename: string;
      created_at: string;
      section_id: string;
      page_id: number;
      // Source document details from filtered reports
      CR_DATE?: string;
      LIBNATCR?: string;
      TITLE?: string;
      date?: string;
      libnatcr?: string;
      title?: string;
      display_name?: string;
    }>;
    // Documents in use - list of Documents in use for extraction
    documents_mobilises?: Array<{
      date: string;
      libnatcr: string;
      title: string;
      filename: string;
    }>;
    // Fallback tracking when source filters don't find entity
    used_fallback?: boolean;
    fallback_docs_count?: number;
    documents_mobilises_original_filter?: Array<{
      date: string;
      libnatcr: string;
      title: string;
      filename: string;
    }>;
  };
}

export interface ReportContent {
  first_match: {
    found_entities: ReportEntity[];
    not_found_entities: Array<{ entity_name: string }>;
  };
  multiple_match: {
    found_entities: ReportEntity[];
    not_found_entities: Array<{ entity_name: string }>;
  };
  aggregate_all_matches: {
    found_entities: ReportEntity[];
    not_found_entities: Array<{ entity_name: string }>;
  };
  ner_results?: {
    entities: ReportEntity[];
    raw_results_by_type?: {
      first_match?: {
        found_entities: ReportEntity[];
        not_found_entities: Array<{ entity_name: string }>;
      };
      multiple_match?: {
        found_entities: ReportEntity[];
        not_found_entities: Array<{ entity_name: string }>;
      };
      aggregate_all_matches?: {
        found_entities: ReportEntity[];
        not_found_entities: Array<{ entity_name: string }>;
      };
    };
    summary: {
      total_entities: number;
      by_processing_type: Record<string, number>;
    };
  };
  summary?: {
    total_documents: number;
    text_documents_processed: number;
    entities_extracted: number;
    document_types: string[];
    date_range: {
      earliest: string;
      latest: string;
    };
  };
}

export interface Report {
  uuid: string;
  patient_id: string;
  status: 'PROCESSING' | 'COMPLETED' | 'FAILED';
  title: string;
  filename: string;
  file_type: string;
  file_size: number;
  created_at: string;
  character_count: number;
  word_count: number;
  elapsed_seconds?: number;  // Processing time in seconds
  author?: string;
  subject?: string;
  keywords: string[];
  elements: any[];
  content?: ReportContent;
  metadata?: {
    generated_at: string;
    total_documents_processed: number;
    report_version: string;
    processing_method: string;
    statistics?: Record<string, any>;
  };
}

export interface PaginatedReports {
  total: number;
  page: number;
  page_size: number;
  items: Report[];
}

export interface UploadFileData {
  file: File;
  type: string;
  source: string;
  notes?: string;
}

export interface UploadProgress {
  filename: string;
  progress: number;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error' | 'requires_input';
  error?: string;
  uuid?: string;
  message?: string;  // Additional status message (e.g., "Patient ID not found")
}

export interface ReportGenerationProgress {
  status: string;
  progress: number;
  message: string;
  current_step: string;
  entities_extracted?: number;
  documents_found?: number;
  text_documents_processed?: number;
  report_uuid?: string; // UUID of the completed report
  
  // Detailed NER progress tracking
  documents_progress?: {
    current_document: number;
    total_documents: number;
    current_filename: string;
  };
  
  processing_type_progress?: {
    current_type: string; // "first_match", "multiple_match", "aggregate_all_matches"
    types_completed: number;
    total_types: number;
  };
  
  batch_progress?: {
    current_batch: number;
    total_batches: number;
    entities_in_batch: number;
  };
  
  entity_extraction?: {
    entities_found: number;
    entities_processed: number;
    total_entities: number;
    api_calls_made: number;
  };
  
  // Timing estimates
  estimated_completion?: string;
  time_elapsed?: number;
  
  // Stage-specific details
  stage_detail?: string; // More specific info about current stage
}



export interface LLMModel {
  id: string;
  name: string;
  provider: string;
  apiKeyRequired: boolean;
  description: string;
  isDefault: boolean;
  endpointType: 'api' | 'local';
  base_url?: string;
  enabled?: boolean;
  instance?: string;
}

export interface NERConfig {
  max_entities_per_batch: number;
  max_content_size: number;
  chunk_overlapping: number;
  max_concurrent_requests: number;
  aggregation_batch_size: number;
} 

// Section configuration for template-based report organization
export interface SectionConfig {
  id: string;
  name: string;
  description?: string;
  color: string;
  order: number;
}

// Source filter configuration for targeted entity extraction
export interface SourceFilter {
  libnatcr: string;           // Required: Report type (e.g., "CR Radio", "RCP", "CR Anatomopathologie")
  title_keyword?: string;     // Optional: Keyword(s) in TITLE field (pipe-separated for OR: "NUCLEAIRE|PET")
  content_keyword?: string;   // Optional: Keyword(s) in TEXTE field (pipe-separated for OR)
  depth?: number;             // 0 = all matching (default), 1 = most recent, 2 = two most recent, etc.
  focus_section?: string;     // Optional: Focus on specific section (e.g., "conclusion")
}

// Entity configuration types
export interface EntityDef {
  name: string;
  section_id?: string;               // NEW: Reference to section ID (optional for backward compatibility)
  definition?: string;
  extraction_instructions?: string;
  type?: string;
  valid_values?: string[];
  processing_type?: 'first_match' | 'multiple_match' | 'aggregate_all_matches' | string;
  aggregation_instructions?: string;
  
  // Source filtering for targeted extraction from structured JSON data
  source_filters?: SourceFilter[];       // Primary filters (OR logic between filters)
  fallback_filters?: SourceFilter[];     // Fallback filters if primary yields no results
  
  // Fallback to all documents when filters yield no results
  fallback_to_all?: boolean;             // If true, retry with all docs when filters fail
  fallback_depth?: number;               // 0 = all docs (default), 1 = most recent, etc.
}

export interface EntityConfig {
  entities: EntityDef[];
}

// Template management types
export interface EntityTemplate {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  entities: EntityDef[];
  sections: SectionConfig[];         // NEW: Section definitions for this template
  admin_template?: boolean;
}

export interface TemplatesData {
  active_template_id: string | null;
  templates: EntityTemplate[];
}

// Ground Truth & Evaluation Types
export interface GroundTruthEntity {
  entity_name: string;
  value: string | null;
  source: 'extracted' | 'manual';
  confidence: number;
}

export interface GroundTruthPDF {
  filename: string;
  file_content: string; // Base64
  pages: number;
  file_size: number;
}

export interface GroundTruth {
  uploaded_at: string;
  ocr_engine: 'bedrock' | 'easyocr';
  original_pdf?: GroundTruthPDF;
  ocr_text?: string;
  entities: GroundTruthEntity[];
}

export interface ExactMatchMetrics {
  precision: number;
  recall: number;
  f1: number;
}

export interface EvaluationSummary {
  exact_match: ExactMatchMetrics;
  llm_semantic_score: number;
  oov_rate: number;
  entity_count: number;
  matched_count: number;
  missing_count: number;
  extra_count: number;
}

export interface EvaluationEntityDetail {
  entity_name: string;
  gold_value: string | null;
  pred_value: string | null;
  exact_match: boolean;
  llm_score: number;
  notes?: string;
}

export interface WorstEntity {
  name: string;
  f1: number;
}

export interface Evaluation {
  status: 'PENDING' | 'COMPLETED' | 'FAILED';
  evaluated_at?: string;
  llm_model?: string;
  summary?: EvaluationSummary;
  details: EvaluationEntityDetail[];
  worst_entities: WorstEntity[];
  error?: string;
}

export interface GTUploadProgress {
  status: 'STARTED' | 'UPLOADING' | 'OCR_RUNNING' | 'EXTRACTING_ENTITIES' | 'SAVING' | 'COMPLETED' | 'FAILED';
  progress: number;
  message: string;
  timestamp: string;
  data?: {
    entity_count: number;
    page_count: number;
    ocr_engine: string;
    entities: GroundTruthEntity[];
  };
}

export interface EvaluationProgress {
  status: 'STARTED' | 'LOADING_DATA' | 'COMPARING' | 'LLM_SCORING' | 'SAVING' | 'COMPLETED' | 'FAILED';
  progress: number;
  message: string;
  timestamp: string;
  summary?: EvaluationSummary;
  worst_entities?: WorstEntity[];
}

// ============================================================================
// Unprocessed Documents Types
// ============================================================================

export interface UnprocessedDocument {
  id: string;
  patient_id: string;
  file_name: string;
  file_type: string;
  content_preview?: string;
  content_size?: number;
  created_at?: string;
  document_date?: string;
  source_system?: string;
  metadata?: Record<string, any>;
}

export interface UnprocessedDocumentDetail extends UnprocessedDocument {
  content: string;
}

export interface PaginatedUnprocessedDocuments {
  items: UnprocessedDocument[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface UnprocessedDocumentCounts {
  counts: Array<{ patient_id: string; count: number }>;
  total_documents: number;
  total_patients: number;
}

export interface ProcessDocumentsRequest {
  document_ids: string[];
}

export interface ProcessDocumentsResponse {
  message: string;
  total_requested: number;
  processing_started: number;
  failed_to_start: number;
  processing_jobs: Array<{
    unprocessed_document_id: string;
    new_document_uuid: string;
    filename: string;
    status: string;
  }>;
  errors: Array<{
    document_id: string;
    error: string;
  }>;
}

export interface ProcessingStep {
  id: string;
  name: string;
  order: number;
}

export interface ProcessingStatus {
  document_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'not_found';
  current_step?: string;
  current_step_index?: number;
  total_steps?: number;
  steps?: ProcessingStep[];
  completed_steps?: string[];
  progress?: number;
  new_document_uuid?: string;
  error?: string;
}

export interface BatchProcessingStatusResponse {
  total: number;
  completed: number;
  in_progress: number;
  failed: number;
  pending: number;
  documents: ProcessingStatus[];
}