import { LLMModel } from '../types';
import llmConfig from '../config/llm_config.json';
import { apiService } from './api';

class LLMService {
  private models: LLMModel[];
  private isLoaded: boolean = false;
  
  constructor() {
    // Initialize with default models from config file and add type assertion
    this.models = llmConfig.models as LLMModel[];
  }
  
  // Load models from API
  async loadModelsFromAPI(): Promise<boolean> {
    try {
      const response = await apiService.api.get('/settings/llm-models');
      if (response.data && response.data.models) {
        const modelsFromApi = response.data.models as LLMModel[];
        // Backend should already filter, but keep a safeguard here
        this.models = modelsFromApi.filter(m => m.enabled !== false);
        this.isLoaded = true;
        return true;
      }
      return false;
    } catch (error) {
      console.error('Failed to load models from API:', error);
      // Fallback to local config
      return false;
    }
  }

  // Get all available LLM models
  getAllModels(): LLMModel[] {
    // Ensure only enabled models are returned
    return this.models.filter(m => m.enabled !== false);
  }

  // Get the current selected model
  getCurrentModel(): LLMModel {
    let currentModelId = apiService.getCurrentLLMModelId();
    
    // No need to map IDs anymore - backend handles it
    // Just log the current model ID
    console.log(`Current model ID: ${currentModelId}`)
    
    const model = this.models.find(model => model.id === currentModelId);
    
    // Return the found model or the first default model
    return model || this.models.find(model => model.isDefault) || this.models[0];
  }

  // Get model by ID
  getModelById(modelId: string): LLMModel | undefined {
    return this.models.find(model => model.id === modelId);
  }
  
  // Get model by unique value (id|name)
  getModelByUniqueValue(uniqueValue: string): LLMModel | undefined {
    if (!uniqueValue.includes('|')) {
      // Fallback to regular ID search for backward compatibility
      return this.getModelById(uniqueValue);
    }
    
    const [id, name] = uniqueValue.split('|');
    return this.models.find(model => model.id === id && model.name === name);
  }

  // Update the current model
  async updateCurrentModel(modelId: string, apiKey?: string, selectedModel?: LLMModel): Promise<boolean> {
    const model = this.getModelById(modelId);
    
    // Use provided model or find it by ID
    const modelToUse = selectedModel || model;
    
    // Ensure the model exists
    if (!modelToUse) {
      console.error(`Model with ID ${modelId} not found`);
      return false;
    }
    
    // If API key is required but not provided, use stored key or return false
    if (modelToUse.apiKeyRequired && !apiKey) {
      apiKey = apiService.getLLMApiKey();
      
      if (!apiKey) {
        console.error(`API key required for model ${modelToUse.name} but not provided`);
        return false;
      }
    }
    
    // Pass base_url if available in the selected model
    const base_url = modelToUse.base_url;
    
    // Update the model via API service
    return await apiService.updateLLMModel(modelId, apiKey, base_url);
  }

  // Group models by provider
  getModelsByProvider(): Record<string, LLMModel[]> {
    const grouped: Record<string, LLMModel[]> = {};
    
    this.models.filter(model => model.enabled !== false).forEach(model => {
      if (!grouped[model.provider]) {
        grouped[model.provider] = [];
      }
      
      grouped[model.provider].push(model);
    });
    
    return grouped;
  }

  // Add a new LLM model via backend and refresh local cache
  async addModel(newModel: LLMModel): Promise<LLMModel[]> {
    const response = await apiService.api.post('/settings/llm-models', { model: newModel });
    const models = response.data.models as LLMModel[];
    this.models = models;
    return this.getAllModels();
  }

  // Edit an existing LLM model by id+name and refresh local cache
  async editModel(matchId: string, matchName: string, updated: LLMModel): Promise<LLMModel[]> {
    const response = await apiService.api.put('/settings/llm-models', {
      match_id: matchId,
      match_name: matchName,
      updated,
    });
    const models = response.data.models as LLMModel[];
    this.models = models;
    return this.getAllModels();
  }
}

export const llmService = new LLMService();
export default LLMService;
