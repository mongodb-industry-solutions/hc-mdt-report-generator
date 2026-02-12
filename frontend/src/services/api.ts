import axios, { AxiosInstance, AxiosProgressEvent } from 'axios';
import { 
  PatientDocument, 
  PaginatedDocuments, 
  Report, 
  PaginatedReports, 
  UploadFileData,
  LLMModel,
  NERConfig,
  EntityDef,
  EntityTemplate,
  TemplatesData,
  GroundTruth,
  GroundTruthEntity,
  Evaluation,
  EvaluationSummary,
  GTUploadProgress,
  EvaluationProgress
} from '../types';

// Storage keys
const API_URL_STORAGE_KEY = 'claritygr_api_url';
const LLM_MODEL_STORAGE_KEY = 'claritygr_llm_model';
const LLM_API_KEY_STORAGE_KEY = 'claritygr_llm_api_key';
// Provider-specific API key prefix
const LLM_PROVIDER_API_KEY_PREFIX = 'claritygr_llm_api_key_';

// Get API URL - uses Next.js API proxy pattern
function getApiBaseURL(): string {
  // Only access localStorage on client-side (not during SSR)
  if (typeof window !== 'undefined') {
    // Check if we have a stored URL first (allows user override via settings)
    const storedUrl = localStorage.getItem(API_URL_STORAGE_KEY);
    if (storedUrl) {
      return storedUrl;
    }
  }

  // Use Next.js API proxy route - this will be proxied to backend via BACKEND_URL
  const proxyUrl = '/api/internal';
  
  // Only store in localStorage on client-side
  if (typeof window !== 'undefined') {
    localStorage.setItem(API_URL_STORAGE_KEY, proxyUrl);
  }
  
  return proxyUrl;
}

class ApiService {
  api: AxiosInstance; // Changed to public for other services to use

  constructor(baseURL: string = getApiBaseURL()) {
    // Log the API URL being used for debugging
    console.log('🌐 API Base URL:', baseURL);
    this.api = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  // Update base URL and persist to localStorage
  updateBaseURL(url: string) {
    this.api.defaults.baseURL = url;
    if (typeof window !== 'undefined') {
      localStorage.setItem(API_URL_STORAGE_KEY, url);
    }
    console.log('🌐 API Base URL updated to:', url);
  }
  
  // Get the current LLM model ID
  getCurrentLLMModelId(): string {
    if (typeof window === 'undefined') return 'mistral-small-latest';
    const storedModelId = localStorage.getItem(LLM_MODEL_STORAGE_KEY);
    return storedModelId || 'mistral-small-latest'; // Default if not set
  }
  
  // Update LLM model and persist to localStorage
  async updateLLMModel(modelId: string, apiKey?: string, baseUrl?: string): Promise<boolean> {
    try {
      // Model ID mapping is now handled by the backend
      const mappedModelId = modelId;
      
      // Save model ID to local storage
      if (typeof window !== 'undefined') {
        localStorage.setItem(LLM_MODEL_STORAGE_KEY, mappedModelId);
      }
      
      // If API key is provided, save it using the model-specific storage
      if (apiKey) {
        this.storeLLMApiKey(apiKey, modelId);
        console.log('🔑 API key cached for model:', modelId);
      } else {
        // Try to get the API key from localStorage for this specific model
        apiKey = this.getLLMApiKey(modelId);
      }
      
      // If base URL is provided for OpenAI models, save it
      if (baseUrl && modelId === 'gpt-oss-20b' && typeof window !== 'undefined') {
        localStorage.setItem('claritygr_gpt_open_url', baseUrl);
        console.log('🌐 GPT Open base URL cached:', baseUrl);
      }
      
      // Ensure we're sending a non-empty API key if available
      const keyToSend = apiKey || '';
      
      // Send model change to backend with base URL if applicable
      const response = await this.api.post('/settings/llm-model', {
        model_id: mappedModelId,
        api_key: keyToSend,
        base_url: baseUrl
      });
      
      console.log('🤖 LLM Model updated to:', modelId);
      
      // Also update the MISTRAL_API_KEY directly in settings if this is a Mistral model
      if (modelId.startsWith('mistral-') && apiKey) {
        console.log('🔑 Setting MISTRAL_API_KEY directly');
        try {
          await this.api.post('/settings/set-env-var', {
            key: 'MISTRAL_API_KEY',
            value: apiKey
          });
        } catch (err) {
          console.warn('Failed to directly set MISTRAL_API_KEY, but continuing anyway', err);
        }
      }
      
      return response.data.success || false;
    } catch (error) {
      console.error('Failed to update LLM model:', error);
      return false;
    }
  }
  
  // Get API key for specific LLM model or provider
  getLLMApiKey(modelId?: string): string {
    if (typeof window === 'undefined') return '';
    
    // If a model ID is provided, try to get its specific key first
    if (modelId) {
      // Try model-specific key
      const modelKey = localStorage.getItem(`${LLM_PROVIDER_API_KEY_PREFIX}${modelId}`);
      if (modelKey) return modelKey;
      
      // If model key doesn't exist, try provider key
      const provider = modelId.split('-')[0]; // Extract provider from model ID
      if (provider) {
        const providerKey = localStorage.getItem(`${LLM_PROVIDER_API_KEY_PREFIX}${provider}`);
        if (providerKey) return providerKey;
      }
    }
    
    // Fall back to the general key
    return localStorage.getItem(LLM_API_KEY_STORAGE_KEY) || 
           localStorage.getItem('claritygr_llm_api_key') || '';
  }
  
  // Store API key for a specific model or provider
  storeLLMApiKey(apiKey: string, modelId: string): void {
    if (typeof window === 'undefined') return;
    
    // Always store the key by model ID
    localStorage.setItem(`${LLM_PROVIDER_API_KEY_PREFIX}${modelId}`, apiKey);
    
    // Also extract provider and store by provider
    const provider = modelId.split('-')[0];
    if (provider) {
      localStorage.setItem(`${LLM_PROVIDER_API_KEY_PREFIX}${provider}`, apiKey);
    }
    
    // For backward compatibility, also store in general key
    localStorage.setItem(LLM_API_KEY_STORAGE_KEY, apiKey);
  }
  
  // Get the current GPT Open base URL
  getGptOpenBaseUrl(): string {
    if (typeof window === 'undefined') return 'http://35.88.139.67:8080';
    return localStorage.getItem('claritygr_gpt_open_url') || 'http://35.88.139.67:8080';
  }

  // Patient Documents API
  async getPatients(): Promise<{ items: string[]; total: number; }> {
    const response = await this.api.get(`/patients`);
    return response.data;
  }

  async getPatientDocuments(
    patientId: string, 
    page: number = 1, 
    pageSize: number = 10
  ): Promise<PaginatedDocuments> {
    const response = await this.api.get(
      `/patients/${patientId}/documents?page=${page}&page_size=${pageSize}`
    );
    return response.data;
  }

  async deleteDocument(patientId: string, documentUuid: string): Promise<void> {
    await this.api.delete(`/patients/${patientId}/document/${documentUuid}`);
  }

  async getDocument(patientId: string, documentUuid: string): Promise<PatientDocument> {
    const response = await this.api.get(`/patients/${patientId}/document/${documentUuid}`);
    return response.data;
  }

  async getDocumentByFilename(patientId: string, filename: string): Promise<PatientDocument> {
    const response = await this.api.get(`/patients/${patientId}/documents/by-filename/${encodeURIComponent(filename)}`);
    return response.data;
  }

  async uploadDocument(
    patientId: string, 
    fileData: UploadFileData,
    onUploadProgress?: (progressEvent: AxiosProgressEvent) => void
  ): Promise<PatientDocument> {
    // Convert file to base64
    const base64Content = await this.fileToBase64(fileData.file);
    
    const payload = {
      file: base64Content,
      filename: fileData.file.name,
      type: fileData.type,
      source: fileData.source,
      notes: fileData.notes || '',
      status: 'queued'
    };

    const response = await this.api.post(
      `/patients/${patientId}/document`,
      payload,
      {
        onUploadProgress,
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
    return response.data;
  }

  async getDocumentOCR(patientId: string, documentUuid: string): Promise<any> {
    const response = await this.api.get(`/patients/${patientId}/document/${documentUuid}/ocr`);
    return response.data;
  }

  // ==========================================
  // UUID-First Document API (Decoupled from patient_id)
  // ==========================================

  /**
   * Upload a document WITHOUT specifying patient_id.
   * Patient ID will be extracted during processing (NumdosGR).
   * Use getDocumentByUuid() to poll for status and extracted patient_id.
   */
  async uploadDocumentUuidFirst(
    fileData: UploadFileData,
    onUploadProgress?: (progressEvent: AxiosProgressEvent) => void
  ): Promise<PatientDocument> {
    // Convert file to base64
    const base64Content = await this.fileToBase64(fileData.file);
    
    const payload = {
      file: base64Content,
      filename: fileData.file.name,
      type: fileData.type,
      source: fileData.source,
      notes: fileData.notes || '',
      status: 'queued'
    };

    const response = await this.api.post(
      `/patients/documents`,  // UUID-first endpoint
      payload,
      {
        onUploadProgress,
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
    return response.data;
  }

  /**
   * Get document by UUID only - no patient_id needed.
   * Used for polling during processing when patient_id is not yet known.
   */
  async getDocumentByUuid(documentUuid: string): Promise<PatientDocument> {
    const response = await this.api.get(`/patients/documents/${documentUuid}`);
    return response.data;
  }

  /**
   * Manually assign patient_id to a document when automatic extraction fails.
   * Only works when document status is 'requires_manual_input'.
   */
  async assignPatientId(documentUuid: string, patientId: string): Promise<PatientDocument> {
    const response = await this.api.patch(
      `/patients/documents/${documentUuid}/patient-id`,
      { patient_id: patientId }
    );
    return response.data;
  }

  /**
   * List documents filtered by status.
   * Useful for dashboard showing documents needing manual input.
   */
  async listDocumentsByStatus(
    status?: 'queued' | 'processing' | 'done' | 'failed' | 'requires_manual_input',
    limit: number = 50
  ): Promise<PatientDocument[]> {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    params.set('limit', limit.toString());
    
    const response = await this.api.get(`/patients/documents?${params.toString()}`);
    return response.data;
  }

  // Reports API
  async getPatientReports(
    patientId: string, 
    page: number = 1, 
    pageSize: number = 10
  ): Promise<PaginatedReports> {
    const response = await this.api.get(
      `/patients/${patientId}/reports?page=${page}&page_size=${pageSize}`
    );
    return response.data;
  }

  async deleteReport(patientId: string, reportId: string): Promise<void> {
    await this.api.delete(`/patients/${patientId}/reports/${reportId}`);
  }

  async getReport(patientId: string, reportId: string): Promise<Report> {
    const response = await this.api.get(`/patients/${patientId}/reports/${reportId}`);
    return response.data;
  }

  async generateReport(patientId: string, title?: string, reasoningEffort?: 'low'|'medium'|'high', nerConfig?: any): Promise<Report> {
    const payload: any = {};
    if (title) payload.title = title;
    // Reasoning effort removed from UI; backend applies defaults
    
    // Add NER configuration if provided
    if (nerConfig) {
      payload.ner_config = {
        max_entities_per_batch: nerConfig.maxEntitiesPerBatch,
        max_content_size: nerConfig.maxContentSize,
        chunk_overlapping: nerConfig.chunkOverlapping
      };
    }
    // Always fail fast on errors (no partial results)
    payload.ner_config = { ...(payload.ner_config || {}), continue_on_batch_errors: false };
    
    const response = await this.api.post(`/patients/${patientId}/reports`, payload);
    return response.data;
  }

  async generateReportWithProgress(
    patientId: string, 
    title?: string,
    onProgress?: (data: any) => void,
    reasoningEffort?: 'low'|'medium'|'high',
    nerConfig?: any
  ): Promise<void> {
    const payload: any = {};
    if (title) payload.title = title;
    // Reasoning effort removed from UI; backend applies defaults
    
    // Add NER configuration if provided
    if (nerConfig) {
      payload.ner_config = {
        max_entities_per_batch: nerConfig.maxEntitiesPerBatch,
        max_content_size: nerConfig.maxContentSize,
        chunk_overlapping: nerConfig.chunkOverlapping
      };
    }
    // Always fail fast on errors (no partial results)
    payload.ner_config = { ...(payload.ner_config || {}), continue_on_batch_errors: false };

    const response = await fetch(`${this.api.defaults.baseURL}/patients/${patientId}/reports/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    // Check response status before processing
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    if (!response.body) {
      throw new Error('No response body');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let hasReceivedData = false;
    let lastError: any = null;

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              hasReceivedData = true;
              
              // Check for error status in the data
              if (data.status === 'FAILED') {
                lastError = {
                  message: data.message || 'Report generation failed',
                  error: data.error,
                  error_type: data.error_type,
                  details: data
                };
              }
              
              if (onProgress) {
                onProgress(data);
              }
            } catch (e) {
              console.warn('Failed to parse SSE data:', line);
            }
          }
        }
      }
      
      // If we received a FAILED status, throw the error
      if (lastError) {
        const error = new Error(lastError.message);
        (error as any).details = lastError;
        throw error;
      }
      
      // If we didn't receive any data, something went wrong
      if (!hasReceivedData) {
        throw new Error('No data received from server');
      }
      
    } finally {
      reader.releaseLock();
    }
  }

  async jsonFilterCheck(
    patientId: string,
    jsonDateFrom?: string,
    jsonAutoFilter?: boolean
  ): Promise<{ total_json_documents: number; matched_json_documents: number; first_json: { items_before: number; items_after: number; bytes_before?: number; bytes_after?: number; reduction_percent: number; filter_date?: string | null; }; }> {
    const payload: any = {};
    if (jsonDateFrom) {
      const normalized = jsonDateFrom.includes('-') ? jsonDateFrom.replace(/-/g, '') : jsonDateFrom;
      payload.json_date_from = normalized;
    }
    if (typeof jsonAutoFilter === 'boolean') {
      payload.json_auto_filter = jsonAutoFilter;
    }
    const response = await this.api.post(`/patients/${patientId}/reports/json-filter-check`, payload);
    return response.data;
  }

  // Utility methods
  private async fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => {
        const result = reader.result as string;
        // Remove the data:mime/type;base64, prefix
        const base64 = result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = error => reject(error);
    });
  }

  // Download helpers
  downloadAsJSON(data: any, filename: string) {
    const jsonStr = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    this.downloadBlob(blob, filename);
  }

  async downloadAsPDF(data: any, filename: string) {
    try {
      // Import the PDF generator dynamically to avoid loading issues
      const { generateMedicalReportPDF } = await import('./pdfGenerator');
      const pdfBlob = await generateMedicalReportPDF(data);
      this.downloadBlob(pdfBlob, filename);
    } catch (error) {
      console.error('Error generating PDF:', error);
      // Fallback to JSON download if PDF generation fails
      this.downloadAsJSON(data, filename.replace('.pdf', '.json'));
    }
  }

  private downloadBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // NER Configuration Methods
  async getNERConfig(): Promise<NERConfig> {
    try {
      const response = await this.api.get('/settings/ner-config');
      return response.data.config;
    } catch (error) {
      console.error('Error getting NER configuration:', error);
      throw error;
    }
  }

  // Observability API
  async getGenerations(params?: { start?: string; end?: string; model_llm?: string; filenames_hash?: string; patient_id?: string; }): Promise<{ items: any[]; total: number; }> {
    const query = new URLSearchParams();
    if (params?.start) query.set('start', params.start);
    if (params?.end) query.set('end', params.end);
    if (params?.model_llm) query.set('model_llm', params.model_llm);
    if (params?.filenames_hash) query.set('filenames_hash', params.filenames_hash);
    if (params?.patient_id) query.set('patient_id', params.patient_id);
    const response = await this.api.get(`/observability/generations${query.toString() ? `?${query.toString()}` : ''}`);
    return response.data;
  }

  async getGenerationsFilters(): Promise<{ llms: string[]; hashes: string[]; }> {
    const response = await this.api.get('/observability/generations/filters');
    return response.data;
  }

  // Master Delete (Danger Zone)
  async masterDeleteAll(phrase: string): Promise<{ success: boolean; deleted: { reports: number; documents: number; } }> {
    const response = await this.api.post('/settings/master-delete', { phrase });
    return response.data;
  }

  // Evaluation API
  async getPendingEvaluations(): Promise<{ total: number; items: Array<{ uuid: string; timestamp_utc: string; model_llm: string; filenames_hash: string; patient_id: string; }>; }> {
    const response = await this.api.get('/evaluate/pending');
    return response.data;
  }

  async runEvaluationsWithProgress(onProgress?: (data: any) => void): Promise<void> {
    const response = await fetch(`${this.api.defaults.baseURL}/evaluate/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    if (!response.body) throw new Error('No response body');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              onProgress && onProgress(data);
            } catch {}
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
  
  async updateNERConfig(config: Partial<NERConfig>): Promise<NERConfig> {
    try {
      const response = await this.api.post('/settings/ner-config', config);
      return response.data.config;
    } catch (error) {
      console.error('Error updating NER configuration:', error);
      throw error;
    }
  }

  // Entity Config API
  async getEntityConfig(): Promise<{ source: string; config: any; }> {
    const response = await this.api.get('/entity-config');
    return { source: response.data.source, config: response.data.config };
  }

  async putEntityConfig(config: any): Promise<{ validation: any; }> {
    const response = await this.api.put('/entity-config', config);
    return { validation: response.data.validation };
  }

  async resetEntityConfigFromFile(): Promise<{ validation: any; }> {
    const response = await this.api.post('/entity-config/reset');
    return { validation: response.data.validation };
  }

  async validateEntityConfig(): Promise<{ source: string; validation: any; }> {
    const response = await this.api.get('/entity-config/validate');
    return { source: response.data.source, validation: response.data.validation };
  }

  // Template Management API
  async getAllTemplates(): Promise<{ data: TemplatesData; }> {
    const response = await this.api.get('/entity-config/templates');
    return { data: response.data.data };
  }

  async getActiveTemplate(): Promise<{ template: EntityTemplate; source: string; }> {
    const response = await this.api.get('/entity-config/templates/active');
    return { template: response.data.template, source: response.data.source };
  }

  async getTemplateById(templateId: string): Promise<{ template: EntityTemplate; }> {
    const response = await this.api.get(`/entity-config/templates/${templateId}`);
    return { template: response.data.template };
  }

  async createTemplate(name: string, description: string = '', entities: EntityDef[] = []): Promise<{ template_id: string; validation: any; }> {
    const response = await this.api.post('/entity-config/templates', {
      name,
      description,
      entities
    });
    return { template_id: response.data.template_id, validation: response.data.validation };
  }

  async updateTemplate(templateId: string, updates: Partial<EntityTemplate>): Promise<{ success: boolean; }> {
    const response = await this.api.put(`/entity-config/templates/${templateId}`, updates);
    return { success: response.data.success };
  }

  async deleteTemplate(templateId: string): Promise<{ success: boolean; }> {
    const response = await this.api.delete(`/entity-config/templates/${templateId}`);
    return { success: response.data.success };
  }

  async activateTemplate(templateId: string): Promise<{ active_template_id: string; }> {
    const response = await this.api.post(`/entity-config/templates/${templateId}/activate`);
    return { active_template_id: response.data.active_template_id };
  }

  async duplicateTemplate(templateId: string, newName: string): Promise<{ template_id: string; }> {
    const response = await this.api.post(`/entity-config/templates/${templateId}/duplicate`, {
      new_name: newName
    });
    return { template_id: response.data.template_id };
  }

  async migrateToTemplates(): Promise<{ result: string; }> {
    const response = await this.api.post('/entity-config/templates/migrate');
    return { result: response.data.result };
  }

  // ==========================================
  // Ground Truth & Evaluation API
  // ==========================================

  /**
   * Upload ground truth PDF and extract entities with progress updates
   */
  async uploadGroundTruth(
    patientId: string,
    reportUuid: string,
    file: File,
    ocrEngine: 'bedrock' | 'easyocr' | 'mistral' = 'bedrock',
    onProgress?: (data: GTUploadProgress) => void
  ): Promise<GTUploadProgress | null> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('ocr_engine', ocrEngine);
    // LLM provider is determined by backend from LLM_PROVIDER env var

    const response = await fetch(
      `${this.api.defaults.baseURL}/patients/${patientId}/reports/${reportUuid}/ground-truth`,
      {
        method: 'POST',
        body: formData,
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    if (!response.body) throw new Error('No response body');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let lastData: GTUploadProgress | null = null;

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6)) as GTUploadProgress;
              lastData = data;
              onProgress?.(data);
            } catch {}
          }
        }
      }
    } finally {
      reader.releaseLock();
    }

    return lastData;
  }

  /**
   * Update ground truth entities after user verification
   */
  async updateGroundTruthEntities(
    patientId: string,
    reportUuid: string,
    entities: Array<{ entity_name: string; value: string | null }>
  ): Promise<{ status: string; entity_count: number; message: string }> {
    const response = await this.api.put(
      `/patients/${patientId}/reports/${reportUuid}/ground-truth`,
      { entities }
    );
    return response.data;
  }

  /**
   * Get ground truth data for a report
   */
  async getGroundTruth(
    patientId: string,
    reportUuid: string
  ): Promise<{
    status: 'found' | 'not_found';
    message?: string;
    ground_truth?: {
      uploaded_at: string;
      ocr_engine: string;
      page_count: number;
      entity_count: number;
      entities: GroundTruthEntity[];
    };
  }> {
    const response = await this.api.get(
      `/patients/${patientId}/reports/${reportUuid}/ground-truth`
    );
    return response.data;
  }

  /**
   * Get ground truth PDF for preview
   */
  getGroundTruthPdfUrl(patientId: string, reportUuid: string): string {
    return `${this.api.defaults.baseURL}/patients/${patientId}/reports/${reportUuid}/ground-truth/pdf`;
  }

  /**
   * Run evaluation comparing generated entities against ground truth
   */
  async runEvaluation(
    patientId: string,
    reportUuid: string,
    onProgress?: (data: EvaluationProgress) => void
  ): Promise<EvaluationProgress | null> {
    // LLM provider is determined by backend from LLM_PROVIDER env var
    const response = await fetch(
      `${this.api.defaults.baseURL}/patients/${patientId}/reports/${reportUuid}/evaluate`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    if (!response.body) throw new Error('No response body');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let lastData: EvaluationProgress | null = null;

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6)) as EvaluationProgress;
              lastData = data;
              onProgress?.(data);
            } catch {}
          }
        }
      }
    } finally {
      reader.releaseLock();
    }

    return lastData;
  }

  /**
   * Get evaluation results for a report
   */
  async getEvaluation(
    patientId: string,
    reportUuid: string
  ): Promise<{
    status: 'not_evaluated' | 'PENDING' | 'COMPLETED' | 'FAILED';
    message?: string;
    evaluated_at?: string;
    llm_model?: string;
    summary?: EvaluationSummary;
    details?: Array<{
      entity_name: string;
      gold_value: string | null;
      pred_value: string | null;
      exact_match: boolean;
      llm_score: number;
      notes?: string;
    }>;
    worst_entities?: Array<{ name: string; f1: number }>;
    ground_truth_info?: {
      uploaded_at: string;
      ocr_engine: string;
      entity_count: number;
    };
  }> {
    const response = await this.api.get(
      `/patients/${patientId}/reports/${reportUuid}/evaluation`
    );
    return response.data;
  }
}

export const apiService = new ApiService();
export { getApiBaseURL };
export default ApiService; 