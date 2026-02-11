import React, { useState, useEffect } from 'react';
import { X, Settings, Server, BrainCircuit, SlidersHorizontal, ListPlus, Pencil, AlertTriangle, Trash2, Check, Plus, Minus, Filter, ChevronDown, ChevronRight, RefreshCw } from 'lucide-react';
import { LLMModel, EntityConfig, EntityDef, EntityTemplate, SourceFilter } from '../types';
import { llmService } from '../services/llmService';
import { apiService } from '../services/api';

interface SettingsPanelProps {
  apiBaseUrl: string;
  onApiBaseUrlChange: (url: string) => void;
  onClose: () => void;
}

export default function SettingsPanel({ apiBaseUrl, onApiBaseUrlChange, onClose }: SettingsPanelProps) {
  // State for LLM model settings
  const [models, setModels] = useState<LLMModel[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<string>('');
  const [apiKey, setApiKey] = useState<string>('');
  const [showApiKey, setShowApiKey] = useState<boolean>(false);
  const [apiKeyRequired, setApiKeyRequired] = useState<boolean>(false);
  const [modelsByProvider, setModelsByProvider] = useState<Record<string, LLMModel[]>>({});
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle');
  // Using hardcoded GPT Open Base URL from settings_controller.py
  // Removed: stop-on-error toggle (always fail-fast now)
  
  // Tabs
  const [activeTab, setActiveTab] = useState<'general' | 'models' | 'entities'>('general');

  // Entity config state
  const [entityConfigText, setEntityConfigText] = useState<string>('');
  const [entityConfigSource, setEntityConfigSource] = useState<string>('');
  const [entityConfigStatus, setEntityConfigStatus] = useState<'idle' | 'loading' | 'validating' | 'saving' | 'success' | 'error'>('idle');
  const [entityConfig, setEntityConfig] = useState<EntityConfig | null>(null);
  const [selectedEntityIndex, setSelectedEntityIndex] = useState<number>(0);
  
  // Template management state
  const [templates, setTemplates] = useState<EntityTemplate[]>([]);
  const [activeTemplateId, setActiveTemplateId] = useState<string | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [showTemplateDialog, setShowTemplateDialog] = useState<'create' | 'rename' | null>(null);
  const [templateFormName, setTemplateFormName] = useState('');
  const [templateFormDescription, setTemplateFormDescription] = useState('');
  
  // Model management form state (Add/Edit)
  const [isEditingExisting, setIsEditingExisting] = useState<boolean>(false);
  const [matchId, setMatchId] = useState<string>('');
  const [matchName, setMatchName] = useState<string>('');
  
  // Ollama sync state
  const [ollamaSyncStatus, setOllamaSyncStatus] = useState<'idle' | 'syncing' | 'success' | 'error'>('idle');
  const [ollamaSyncMessage, setOllamaSyncMessage] = useState<string>('');
  
  const [modelForm, setModelForm] = useState<LLMModel>({
    id: '',
    name: '',
    provider: 'openai',
    apiKeyRequired: false,
    description: '',
    isDefault: false,
    endpointType: 'api',
    base_url: '',
    enabled: true,
    instance: ''
  });
  const [modelSaveStatus, setModelSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle');
  // Master delete modal state
  const [showMasterDelete, setShowMasterDelete] = useState<boolean>(false);
  const [confirmPhrase, setConfirmPhrase] = useState<string>('');
  const [masterDeleteStatus, setMasterDeleteStatus] = useState<'idle' | 'working' | 'done' | 'error'>('idle');
  
  // Load models on component mount
  useEffect(() => {
    const loadModels = async () => {
      // Try to load models from API
      await llmService.loadModelsFromAPI();
      
      // Get models after API load (or fallback to local config)
      const allModels = llmService.getAllModels();
      setModels(allModels);
      
      // Get current model
      const currentModel = llmService.getCurrentModel();
      // Create unique value from id and name
      const uniqueValue = `${currentModel.id}|${currentModel.name}`;
      setSelectedModelId(uniqueValue);
      setApiKeyRequired(currentModel.apiKeyRequired);
      
      // Load the model-specific API key from localStorage
      const cachedApiKey = apiService.getLLMApiKey(currentModel.id);
      setApiKey(cachedApiKey);
      
      // GPT Open base URL is now hardcoded in backend
      
      // Group models by provider
      setModelsByProvider(llmService.getModelsByProvider());
    };
    
    loadModels();
  }, []);

  // Lazy-load entity templates when tab opened first time
  useEffect(() => {
    const loadEntityConfig = async () => {
      if (activeTab !== 'entities') return;
      if (templates.length > 0) return; // already loaded
      
      try {
        setEntityConfigStatus('loading');
        
        // Try to migrate first (will skip if already migrated)
        try {
          await apiService.migrateToTemplates();
        } catch (migrationError) {
          console.log('Migration skipped or already done');
        }
        
        // Load all templates
        const { data } = await apiService.getAllTemplates();
        setTemplates(data.templates);
        setActiveTemplateId(data.active_template_id);
        
        // Select the active template by default
        const activeTemplate = data.templates.find(t => t.id === data.active_template_id);
        if (activeTemplate) {
          setSelectedTemplateId(activeTemplate.id);
          setEntityConfig({ entities: activeTemplate.entities });
        } else if (data.templates.length > 0) {
          // Fallback to first template
          setSelectedTemplateId(data.templates[0].id);
          setEntityConfig({ entities: data.templates[0].entities });
        }
        
        setEntityConfigStatus('idle');
      } catch (e) {
        console.error('Failed to load templates', e);
        setEntityConfigStatus('error');
      }
    };
    loadEntityConfig();
  }, [activeTab, templates.length]);
  
  // Handle model selection change
  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const uniqueValue = e.target.value;
    // Extract actual model ID from the combined value
    const newModelId = uniqueValue.split('|')[0];
    setSelectedModelId(uniqueValue);
    
    // Check if API key is required for this model
    // Pass both parts to find the exact model
    const selectedModel = llmService.getModelByUniqueValue(uniqueValue);
    setApiKeyRequired(selectedModel?.apiKeyRequired || false);
    
    // Using hardcoded base URL from backend
    
    // Load the model-specific API key
    const modelApiKey = apiService.getLLMApiKey(newModelId);
    setApiKey(modelApiKey);
  };
  
  // Helpers for model management tab
  const startAddNewModel = () => {
    setIsEditingExisting(false);
    setMatchId('');
    setMatchName('');
    setModelForm({
      id: '',
      name: '',
      provider: 'openai',
      apiKeyRequired: false,
      description: '',
      isDefault: false,
      endpointType: 'api',
      base_url: '',
      enabled: true,
      instance: ''
    });
  };
  
  const startEditModel = (model: LLMModel) => {
    setIsEditingExisting(true);
    setMatchId(model.id);
    setMatchName(model.name);
    setModelForm({ ...model });
  };
  
  const handleModelFormChange = (field: keyof LLMModel, value: any) => {
    setModelForm(prev => ({ ...prev, [field]: value }));
  };
  
  const saveModel = async () => {
    setModelSaveStatus('saving');
    try {
      let updatedList: LLMModel[] = [];
      if (isEditingExisting) {
        updatedList = await llmService.editModel(matchId, matchName, modelForm);
      } else {
        updatedList = await llmService.addModel(modelForm);
      }
      setModels(updatedList);
      setModelsByProvider(llmService.getModelsByProvider());
      setModelSaveStatus('success');
      setTimeout(() => setModelSaveStatus('idle'), 1200);
    } catch (e) {
      console.error('Error saving model:', e);
      setModelSaveStatus('error');
      setTimeout(() => setModelSaveStatus('idle'), 1600);
    }
  };
  
  // Sync models from Ollama
  const syncOllamaModels = async () => {
    setOllamaSyncStatus('syncing');
    setOllamaSyncMessage('Connecting to Ollama...');
    try {
      const response = await apiService.api.post('/settings/sync-ollama-models');
      const data = response.data;
      
      if (data.success) {
        // Reload models after sync
        await llmService.loadModelsFromAPI();
        const allModels = llmService.getAllModels();
        setModels(allModels);
        setModelsByProvider(llmService.getModelsByProvider());
        
        setOllamaSyncMessage(`✅ Synced ${data.synced_models} models from Ollama`);
        setOllamaSyncStatus('success');
        setTimeout(() => {
          setOllamaSyncStatus('idle');
          setOllamaSyncMessage('');
        }, 3000);
      } else {
        setOllamaSyncMessage(data.error || 'Failed to sync');
        setOllamaSyncStatus('error');
        setTimeout(() => setOllamaSyncStatus('idle'), 4000);
      }
    } catch (e: any) {
      console.error('Error syncing Ollama models:', e);
      setOllamaSyncMessage(e.message || 'Connection failed');
      setOllamaSyncStatus('error');
      setTimeout(() => setOllamaSyncStatus('idle'), 4000);
    }
  };
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    setSaveStatus('saving');
    
    try {
      // Parallel updates for better performance
      const updates = [];
      
      // Update LLM model if selected
      if (selectedModelId) {
        // Extract actual model ID from the combined value
        const modelId = selectedModelId.split('|')[0];
        const selectedModel = llmService.getModelByUniqueValue(selectedModelId);
        
        // API key will be stored by model ID in the update method
        updates.push(llmService.updateCurrentModel(modelId, apiKey, selectedModel));
      }
      
      // Wait for all updates to complete
      const results = await Promise.all(updates);
      const allSuccessful = results.every((result: any) => result !== undefined);
      
      setSaveStatus(allSuccessful ? 'success' : 'error');
      
      // Reset after a delay
      setTimeout(() => {
        setSaveStatus('idle');
        onClose();
      }, 1500);
    } catch (error) {
      console.error('Error updating settings:', error);
      setSaveStatus('error');
    }
  };

  // Template management handlers
  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplateId(templateId);
    const template = templates.find(t => t.id === templateId);
    if (template) {
      setEntityConfig({ entities: template.entities });
      setSelectedEntityIndex(0);
    }
  };

  const handleCreateTemplate = async () => {
    if (!templateFormName.trim()) return;
    
    try {
      setEntityConfigStatus('saving');
      const { template_id } = await apiService.createTemplate(
        templateFormName,
        templateFormDescription,
        [] // Start with empty entities
      );
      
      // Reload templates
      const { data } = await apiService.getAllTemplates();
      setTemplates(data.templates);
      setSelectedTemplateId(template_id);
      
      // Load the new template
      const newTemplate = data.templates.find(t => t.id === template_id);
      if (newTemplate) {
        setEntityConfig({ entities: newTemplate.entities });
      }
      
      setShowTemplateDialog(null);
      setTemplateFormName('');
      setTemplateFormDescription('');
      setEntityConfigStatus('idle');
    } catch (e) {
      console.error('Error creating template:', e);
      setEntityConfigStatus('error');
      setTimeout(() => setEntityConfigStatus('idle'), 1500);
    }
  };

  const handleSaveTemplate = async () => {
    if (!selectedTemplateId) return;
    
    try {
      setEntityConfigStatus('saving');
      await apiService.updateTemplate(selectedTemplateId, {
        entities: entityConfig?.entities || []
      });
      
      // Reload templates
      const { data } = await apiService.getAllTemplates();
      setTemplates(data.templates);
      
      setEntityConfigStatus('success');
      setTimeout(() => setEntityConfigStatus('idle'), 1000);
    } catch (e) {
      console.error('Error saving template:', e);
      setEntityConfigStatus('error');
      setTimeout(() => setEntityConfigStatus('idle'), 1500);
    }
  };

  const handleActivateTemplate = async (templateId: string) => {
    try {
      await apiService.activateTemplate(templateId);
      setActiveTemplateId(templateId);
    } catch (e) {
      console.error('Error activating template:', e);
    }
  };

  const handleDeleteTemplate = async (templateId: string) => {
    if (templateId === activeTemplateId) {
      alert('Cannot delete the active template. Please activate another template first.');
      return;
    }
    
    const template = templates.find(t => t.id === templateId);
    if (!template) return;
    
    if (!confirm(`Are you sure you want to delete the template "${template.name}"? This action cannot be undone.`)) {
      return;
    }
    
    try {
      await apiService.deleteTemplate(templateId);
      
      // Reload templates
      const { data } = await apiService.getAllTemplates();
      setTemplates(data.templates);
      
      // If the deleted template was selected, select another one
      if (selectedTemplateId === templateId) {
        if (data.templates.length > 0) {
          setSelectedTemplateId(data.templates[0].id);
          setEntityConfig({ entities: data.templates[0].entities });
        } else {
          setSelectedTemplateId(null);
          setEntityConfig(null);
        }
      }
    } catch (e: any) {
      console.error('Error deleting template:', e);
      alert(e?.response?.data?.detail || 'Failed to delete template');
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center space-x-2">
            <Settings className="w-5 h-5 text-gray-500" />
            <h2 className="text-lg font-medium text-gray-900">Settings</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="px-6 pt-4 border-b border-gray-200">
          <div className="flex space-x-2">
            <button
              type="button"
              onClick={() => setActiveTab('general')}
              className={`px-3 py-2 text-sm rounded-md ${activeTab === 'general' ? 'bg-gray-900 text-white' : 'text-gray-700 hover:bg-gray-100'}`}
            >
              <span className="inline-flex items-center space-x-2"><SlidersHorizontal className="w-4 h-4" /><span>General</span></span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('models')}
              className={`px-3 py-2 text-sm rounded-md ${activeTab === 'models' ? 'bg-gray-900 text-white' : 'text-gray-700 hover:bg-gray-100'}`}
            >
              <span className="inline-flex items-center space-x-2"><BrainCircuit className="w-4 h-4" /><span>LLM Models</span></span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('entities')}
              className={`px-3 py-2 text-sm rounded-md ${activeTab === 'entities' ? 'bg-gray-900 text-white' : 'text-gray-700 hover:bg-gray-100'}`}
            >
              <span className="inline-flex items-center space-x-2"><ListPlus className="w-4 h-4" /><span>Entities</span></span>
            </button>
          </div>
        </div>

        {/* Content */}
        {activeTab === 'general' && (
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* API URL Setting */}
          <div>
            <label htmlFor="apiUrl" className="flex items-center space-x-2 text-sm font-medium text-gray-700 mb-2">
              <Server className="w-4 h-4" />
              <span>API Base URL</span>
            </label>
            <input
              id="apiUrl"
              type="url"
              value={apiBaseUrl}
              onChange={(e) => onApiBaseUrlChange(e.target.value)}
              className="input-field"
              placeholder="http://localhost:8000"
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              The base URL for the FastAPI backend server
            </p>
          </div>
          
          {/* LLM Model Selection */}
          <div>
            <label htmlFor="llmModel" className="flex items-center space-x-2 text-sm font-medium text-gray-700 mb-2">
              <BrainCircuit className="w-4 h-4" />
              <span>LLM Model</span>
            </label>
            
            {/* Model selection dropdown, grouped by provider */}
            <select
              id="llmModel"
              value={selectedModelId}
              onChange={handleModelChange}
              className="input-field"
            >
              {Object.entries(modelsByProvider).map(([provider, providerModels]) => (
                <optgroup key={provider} label={provider.charAt(0).toUpperCase() + provider.slice(1)}>
                  {providerModels.map(model => {
                    // Create a value that combines id + name for selection uniqueness
                    const uniqueValue = `${model.id}|${model.name}`;
                    return (
                      <option key={uniqueValue} value={uniqueValue}>
                        {model.name}
                      </option>
                    );
                  })}
                </optgroup>
              ))}
            </select>
            
            {/* Show selected model description */}
            {selectedModelId && (
              <p className="mt-1 text-xs text-gray-500">
                {llmService.getModelByUniqueValue(selectedModelId)?.description}
              </p>
            )}
            
            {/* API Key input if required */}
            {apiKeyRequired && (
              <div className="mt-3">
                <label htmlFor="apiKey" className="block text-sm font-medium text-gray-700 mb-1">
                  API Key
                </label>
                <div className="relative">
                  <input
                    id="apiKey"
                    type={showApiKey ? "text" : "password"}
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="input-field pr-24"
                    placeholder="Enter API key for this model"
                  />
                  <button
                    type="button"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 text-xs text-gray-500 hover:text-gray-700 px-2 py-1"
                  >
                    {showApiKey ? "Hide" : "Show"}
                  </button>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  This API key is required for the selected model and will be stored securely.
                </p>
              </div>
            )}
            
            {/* GPT Open base URL now hardcoded in backend */}
          </div>

          
          {/* Connection Status */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-900 mb-2">Connection Status</h3>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-sm text-gray-600">Ready to connect</span>
            </div>
          </div>

          {/* NER Behavior toggle removed; system always fails fast on serious errors */}

          {/* Danger Zone */}
          <div className="border border-red-200 bg-red-50 rounded-lg p-4">
            <div className="flex items-center mb-2">
              <AlertTriangle className="w-5 h-5 text-red-600 mr-2" />
              <h3 className="text-sm font-semibold text-red-800">Danger Zone</h3>
            </div>
            <p className="text-sm text-red-700 mb-3">Permanently delete all MDT reports and uploaded documents from the database.</p>
            <button
              type="button"
              onClick={() => { setShowMasterDelete(true); setConfirmPhrase(''); setMasterDeleteStatus('idle'); }}
              className="inline-flex items-center space-x-2 text-red-700 hover:text-red-900 hover:bg-red-100 border border-red-300 px-3 py-2 rounded-md"
            >
              <Trash2 className="w-4 h-4" />
              <span>Delete ALL data</span>
            </button>
          </div>

          {/* Save Button with Status */}
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary"
              disabled={saveStatus === 'saving'}
            >
              Cancel
            </button>
            <button
              type="submit"
              className={`btn-primary flex items-center ${saveStatus === 'saving' ? 'opacity-75 cursor-wait' : ''}`}
              disabled={saveStatus === 'saving'}
            >
              {saveStatus === 'saving' ? (
                <>
                  <span className="animate-spin h-4 w-4 mr-2 border-2 border-white border-t-transparent rounded-full"></span>
                  Saving...
                </>
              ) : saveStatus === 'success' ? (
                'Settings Saved!'
              ) : saveStatus === 'error' ? (
                'Error Saving'
              ) : (
                'Save Settings'
              )}
            </button>
          </div>
        </form>
        )}

        {activeTab === 'models' && (
          <div className="p-6 space-y-6">
            {/* List + Actions */}
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-900">Manage LLM Models</h3>
              <div className="flex items-center space-x-2">
                <button 
                  type="button" 
                  onClick={syncOllamaModels} 
                  disabled={ollamaSyncStatus === 'syncing'}
                  className={`btn-secondary inline-flex items-center space-x-2 ${ollamaSyncStatus === 'syncing' ? 'opacity-75 cursor-wait' : ''}`}
                  title="Sync available models from Ollama"
                >
                  <RefreshCw className={`w-4 h-4 ${ollamaSyncStatus === 'syncing' ? 'animate-spin' : ''}`} />
                  <span>{ollamaSyncStatus === 'syncing' ? 'Syncing...' : 'Sync Ollama'}</span>
                </button>
                <button type="button" onClick={startAddNewModel} className="btn-secondary inline-flex items-center space-x-2">
                  <ListPlus className="w-4 h-4" />
                  <span>New Model</span>
                </button>
              </div>
            </div>
            
            {/* Ollama sync status message */}
            {ollamaSyncMessage && (
              <div className={`text-sm px-3 py-2 rounded ${
                ollamaSyncStatus === 'success' ? 'bg-green-50 text-green-700' : 
                ollamaSyncStatus === 'error' ? 'bg-red-50 text-red-700' : 
                'bg-blue-50 text-blue-700'
              }`}>
                {ollamaSyncMessage}
              </div>
            )}
            
            {/* Compact list of existing models */}
            <div className="max-h-40 overflow-auto border border-gray-200 rounded-md">
              {models.map((m) => (
                <div key={`${m.id}|${m.name}`} className="flex items-center justify-between px-3 py-2 border-b last:border-b-0">
                  <div>
                    <div className="text-sm text-gray-900">{m.name}</div>
                    <div className="text-xs text-gray-500">{m.provider} • {m.id}</div>
                  </div>
                  <button type="button" className="text-gray-600 hover:text-gray-900 inline-flex items-center space-x-1" onClick={() => startEditModel(m)}>
                    <Pencil className="w-4 h-4" />
                    <span className="text-sm">Edit</span>
                  </button>
                </div>
              ))}
            </div>

            {/* Editor */}
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Model ID</label>
                  <input className="input-field" value={modelForm.id} onChange={(e) => handleModelFormChange('id', e.target.value)} placeholder="e.g. gpt-oss-20b" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                  <input className="input-field" value={modelForm.name} onChange={(e) => handleModelFormChange('name', e.target.value)} placeholder="Display name" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
                  <select className="input-field" value={modelForm.provider} onChange={(e) => handleModelFormChange('provider', e.target.value)}>
                    <option value="openai">openai</option>
                    <option value="mistral api">mistral api</option>
                    <option value="ollama">ollama</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Endpoint Type</label>
                  <select className="input-field" value={modelForm.endpointType} onChange={(e) => handleModelFormChange('endpointType', e.target.value)}>
                    <option value="api">api</option>
                    <option value="local">local</option>
                  </select>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Base URL</label>
                  <input className="input-field" value={modelForm.base_url || ''} onChange={(e) => handleModelFormChange('base_url', e.target.value)} placeholder="http://host:port" />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <input className="input-field" value={modelForm.description || ''} onChange={(e) => handleModelFormChange('description', e.target.value)} placeholder="Short description" />
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <label className="inline-flex items-center space-x-2 text-sm text-gray-700">
                  <input type="checkbox" checked={!!modelForm.apiKeyRequired} onChange={(e) => handleModelFormChange('apiKeyRequired', e.target.checked)} />
                  <span>API Key Required</span>
                </label>
                <label className="inline-flex items-center space-x-2 text-sm text-gray-700">
                  <input type="checkbox" checked={!!modelForm.enabled} onChange={(e) => handleModelFormChange('enabled', e.target.checked)} />
                  <span>Enabled</span>
                </label>
                <label className="inline-flex items-center space-x-2 text-sm text-gray-700">
                  <input type="checkbox" checked={!!modelForm.isDefault} onChange={(e) => handleModelFormChange('isDefault', e.target.checked)} />
                  <span>Default</span>
                </label>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Instance</label>
                  <input className="input-field" value={modelForm.instance || ''} onChange={(e) => handleModelFormChange('instance', e.target.value)} placeholder="e.g. local" />
                </div>
              </div>

              <div className="flex justify-end space-x-2">
                <button type="button" className="btn-secondary" onClick={startAddNewModel}>Reset</button>
                <button type="button" className={`btn-primary ${modelSaveStatus === 'saving' ? 'opacity-75 cursor-wait' : ''}`} disabled={modelSaveStatus === 'saving'} onClick={saveModel}>
                  {modelSaveStatus === 'saving' ? 'Saving...' : isEditingExisting ? 'Save Changes' : 'Add Model'}
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'entities' && (
          <div className="p-6 space-y-4">
            {/* Template Selection Bar */}
            <div className="flex items-center justify-between border-b pb-3 mb-4">
              <div className="flex items-center space-x-3 flex-1">
                <label className="text-sm font-medium text-gray-700">Template:</label>
                <select
                  className="input-field flex-1 max-w-xs"
                  value={selectedTemplateId || ''}
                  onChange={(e) => handleTemplateSelect(e.target.value)}
                  disabled={templates.length === 0}
                >
                  {templates.length === 0 && (
                    <option value="">Loading...</option>
                  )}
                  {templates.map(t => (
                    <option key={t.id} value={t.id}>
                      {t.name} {t.id === activeTemplateId ? '(Active ✓)' : ''}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="btn-secondary inline-flex items-center space-x-1"
                  onClick={() => {
                    setTemplateFormName('');
                    setTemplateFormDescription('');
                    setShowTemplateDialog('create');
                  }}
                >
                  <ListPlus className="w-4 h-4" />
                  <span>New</span>
                </button>
              </div>
              
              {/* Template Actions */}
              {selectedTemplateId && (
                <div className="flex items-center space-x-2 ml-4">
                  {selectedTemplateId !== activeTemplateId && (
                    <button
                      type="button"
                      className="btn-secondary inline-flex items-center space-x-1"
                      onClick={() => handleActivateTemplate(selectedTemplateId)}
                    >
                      Set as Active
                    </button>
                  )}
                  {selectedTemplateId === activeTemplateId && (
                    <div className="btn-secondary inline-flex items-center space-x-1 bg-green-50 text-green-700 border-green-200 cursor-default">
                      <Check className="w-4 h-4" />
                      <span>Active for Extraction</span>
                    </div>
                  )}
                  {templates.length > 1 && selectedTemplateId !== activeTemplateId && (
                    <button
                      type="button"
                      className="text-sm text-red-600 hover:text-red-800 p-2"
                      onClick={() => handleDeleteTemplate(selectedTemplateId)}
                      title="Delete template"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Template Description */}
            {selectedTemplateId && templates.find(t => t.id === selectedTemplateId)?.description && (
              <div className="text-sm text-gray-600 italic bg-gray-50 p-2 rounded">
                {templates.find(t => t.id === selectedTemplateId)?.description}
              </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-1 border border-gray-200 rounded-md max-h-96 overflow-auto">
                {entityConfig?.entities?.map((e, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setSelectedEntityIndex(idx)}
                    className={`w-full text-left px-3 py-2 border-b last:border-b-0 ${selectedEntityIndex === idx ? 'bg-gray-100' : ''}`}
                  >
                    <div className="text-sm text-gray-900 truncate">{e.name || '(unnamed entity)'}</div>
                    <div className="text-xs text-gray-400 truncate">{e.processing_type || '(default)'}</div>
                  </button>
                ))}
                <div className="p-2">
                  <button
                    type="button"
                    className="btn-secondary w-full"
                    onClick={() => {
                      const next: EntityConfig = entityConfig ? { ...entityConfig } : { entities: [] };
                      next.entities = [...(next.entities || []), { name: '', type: 'string', processing_type: 'aggregate_all_matches' } as EntityDef];
                      setEntityConfig(next);
                      setSelectedEntityIndex((next.entities.length - 1));
                      setEntityConfigText(JSON.stringify(next, null, 2));
                    }}
                  >
                    + Add Entity
                  </button>
                </div>
              </div>
              <div className="md:col-span-2">
                {entityConfig && entityConfig.entities && entityConfig.entities[selectedEntityIndex] && (
                  <EntityEditor
                    entity={entityConfig.entities[selectedEntityIndex]}
                    onChange={(updated) => {
                      const next: EntityConfig = { ...(entityConfig as EntityConfig), entities: [...(entityConfig?.entities || [])] };
                      next.entities[selectedEntityIndex] = updated;
                      setEntityConfig(next);
                      setEntityConfigText(JSON.stringify(next, null, 2));
                    }}
                    onDelete={() => {
                      const next: EntityConfig = { ...(entityConfig as EntityConfig), entities: [...(entityConfig?.entities || [])] };
                      next.entities.splice(selectedEntityIndex, 1);
                      setSelectedEntityIndex(0);
                      setEntityConfig(next);
                      setEntityConfigText(JSON.stringify(next, null, 2));
                    }}
                  />
                )}
                <div className="flex justify-end space-x-2 mt-4">
                  <button
                    type="button"
                    className={`btn-primary ${entityConfigStatus === 'saving' ? 'opacity-75 cursor-wait' : ''}`}
                    disabled={entityConfigStatus === 'saving' || entityConfigStatus === 'loading' || !selectedTemplateId}
                    onClick={handleSaveTemplate}
                  >
                    {entityConfigStatus === 'saving' ? 'Saving...' : entityConfigStatus === 'success' ? 'Saved!' : entityConfigStatus === 'error' ? 'Error' : 'Save Template'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
      {showMasterDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
            <div className="flex items-center mb-3">
              <AlertTriangle className="w-5 h-5 text-red-600 mr-2" />
              <h3 className="text-lg font-medium text-gray-900">Confirm Master Delete</h3>
            </div>
            <p className="text-sm text-gray-700 mb-3">This action is irreversible. To confirm, type <span className="font-semibold">delete all</span> below:</p>
            <input
              type="text"
              value={confirmPhrase}
              onChange={(e) => setConfirmPhrase(e.target.value)}
              className="input-field"
              placeholder="delete all"
            />
            <div className="flex justify-end space-x-2 mt-4">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setShowMasterDelete(false)}
                disabled={masterDeleteStatus === 'working'}
              >
                Cancel
              </button>
              <button
                type="button"
                className={`btn-primary ${masterDeleteStatus === 'working' ? 'opacity-75 cursor-wait' : ''}`}
                disabled={confirmPhrase.trim().toLowerCase() !== 'delete all' || masterDeleteStatus === 'working'}
                onClick={async () => {
                  try {
                    setMasterDeleteStatus('working');
                    await apiService.masterDeleteAll(confirmPhrase.trim());
                    setMasterDeleteStatus('done');
                    setTimeout(() => { setShowMasterDelete(false); }, 800);
                  } catch (e) {
                    setMasterDeleteStatus('error');
                    setTimeout(() => setMasterDeleteStatus('idle'), 1200);
                  }
                }}
              >
                {masterDeleteStatus === 'working' ? 'Deleting...' : masterDeleteStatus === 'done' ? 'Deleted' : masterDeleteStatus === 'error' ? 'Error' : 'Delete All'}
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Template Creation/Rename Dialog */}
      {showTemplateDialog === 'create' && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Create New Template</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Template Name *</label>
                <input
                  type="text"
                  className="input-field"
                  value={templateFormName}
                  onChange={(e) => setTemplateFormName(e.target.value)}
                  placeholder="e.g., Pediatric Cancer Template"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description (Optional)</label>
                <textarea
                  className="input-field"
                  value={templateFormDescription}
                  onChange={(e) => setTemplateFormDescription(e.target.value)}
                  placeholder="Brief description of this template"
                  rows={3}
                />
              </div>
            </div>
            <div className="flex justify-end space-x-2 mt-4">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setShowTemplateDialog(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={handleCreateTemplate}
                disabled={!templateFormName.trim()}
              >
                Create Template
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 

// Inline Entity Editor component (kept in same file for minimal footprint)
function EntityEditor({ entity, onChange, onDelete }: { entity: EntityDef; onChange: (e: EntityDef) => void; onDelete: () => void; }) {
  const [showSourceFilters, setShowSourceFilters] = useState(false);
  const [showFallbackFilters, setShowFallbackFilters] = useState(false);
  
  const update = (field: keyof EntityDef, value: any) => onChange({ ...entity, [field]: value });
  
  // Source filter helpers
  const addSourceFilter = (isFallback: boolean = false) => {
    const newFilter: SourceFilter = { libnatcr: '', depth: 0 };
    const key = isFallback ? 'fallback_filters' : 'source_filters';
    const existing = entity[key] || [];
    update(key, [...existing, newFilter]);
  };
  
  const updateSourceFilter = (index: number, field: keyof SourceFilter, value: any, isFallback: boolean = false) => {
    const key = isFallback ? 'fallback_filters' : 'source_filters';
    const filters = [...(entity[key] || [])];
    filters[index] = { ...filters[index], [field]: value };
    update(key, filters);
  };
  
  const removeSourceFilter = (index: number, isFallback: boolean = false) => {
    const key = isFallback ? 'fallback_filters' : 'source_filters';
    const filters = [...(entity[key] || [])];
    filters.splice(index, 1);
    // Always send empty array (not undefined) so MongoDB $set actually clears the filters
    update(key, filters);
  };
  
  // Common LIBNATCR options for French medical reports
  const libnatcrOptions = [
    'CR Anatomopathologie',
    'CR Radio',
    'CR Consultation',
    'CR Opératoire',
    'CR Examen',
    'RCP',
    'Hospitalisation',
    'Urgences'
  ];
  
  return (
    <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-2">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
          <input className="input-field" value={entity.name || ''} onChange={(e) => update('name', e.target.value)} placeholder="Entity name" />
        </div>

        {/* Master delete modal moved to parent scope above */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
          <select className="input-field" value={entity.type || 'string'} onChange={(e) => update('type', e.target.value)}>
            <option value="string">string</option>
            <option value="date">date</option>
            <option value="enum">enum</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Processing Type
            {!entity.processing_type && <span className="text-gray-400 text-xs ml-2">(optional - defaults to aggregate_all_matches)</span>}
          </label>
          <select 
            className={`input-field ${!entity.processing_type ? 'text-gray-400' : ''}`} 
            value={entity.processing_type || ''} 
            onChange={(e) => update('processing_type', e.target.value || undefined)}
          >
            <option value="">— Not set (uses default) —</option>
            <option value="first_match">first_match</option>
            <option value="multiple_match">multiple_match</option>
            <option value="aggregate_all_matches">aggregate_all_matches</option>
          </select>
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Definition</label>
        <input className="input-field" value={entity.definition || ''} onChange={(e) => update('definition', e.target.value)} placeholder="Human-readable definition" />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Extraction Instructions</label>
        <textarea className="input-field" value={entity.extraction_instructions || ''} onChange={(e) => update('extraction_instructions', e.target.value)} />
      </div>
      {/* Only show Aggregation Instructions when processing_type is explicitly set to aggregate_all_matches or multiple_match */}
      { (entity.processing_type === 'aggregate_all_matches' || entity.processing_type === 'multiple_match') && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Aggregation Instructions</label>
          <textarea className="input-field" value={entity.aggregation_instructions || ''} onChange={(e) => update('aggregation_instructions', e.target.value)} placeholder="Optional: How to combine multiple extracted values" />
        </div>
      )}
      { (entity.type || '').toLowerCase() === 'enum' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Valid Values (enum)</label>
          <input className="input-field" value={(entity.valid_values || []).join(', ')} onChange={(e) => update('valid_values', e.target.value.split(',').map(s => s.trim()).filter(Boolean))} placeholder="Comma-separated list" />
        </div>
      )}
      
      {/* Source Filters Section */}
      <div className="border border-gray-200 rounded-lg p-3 bg-gray-50">
        <button
          type="button"
          className="flex items-center space-x-2 text-sm font-medium text-gray-700 w-full"
          onClick={() => setShowSourceFilters(!showSourceFilters)}
        >
          {showSourceFilters ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          <Filter className="w-4 h-4 text-blue-500" />
          <span>Source Filters</span>
          {entity.source_filters && entity.source_filters.length > 0 && (
            <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full text-xs">
              {entity.source_filters.length}
            </span>
          )}
        </button>
        
        {showSourceFilters && (
          <div className="mt-3 space-y-3">
            <p className="text-xs text-gray-500">
              Filter reports by type (LIBNATCR), title keywords, content keywords, and temporal depth.
              Multiple filters use OR logic.
            </p>
            
            {(entity.source_filters || []).map((filter, idx) => (
              <SourceFilterEditor
                key={idx}
                filter={filter}
                libnatcrOptions={libnatcrOptions}
                onChange={(field, value) => updateSourceFilter(idx, field, value, false)}
                onRemove={() => removeSourceFilter(idx, false)}
              />
            ))}
            
            <button
              type="button"
              className="btn-secondary inline-flex items-center space-x-1 text-sm"
              onClick={() => addSourceFilter(false)}
            >
              <Plus className="w-3 h-3" />
              <span>Add Filter</span>
            </button>
          </div>
        )}
      </div>
      
      {/* Fallback Filters Section */}
      <div className="border border-gray-200 rounded-lg p-3 bg-orange-50">
        <button
          type="button"
          className="flex items-center space-x-2 text-sm font-medium text-gray-700 w-full"
          onClick={() => setShowFallbackFilters(!showFallbackFilters)}
        >
          {showFallbackFilters ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          <Filter className="w-4 h-4 text-orange-500" />
          <span>Fallback Filters</span>
          {entity.fallback_filters && entity.fallback_filters.length > 0 && (
            <span className="bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full text-xs">
              {entity.fallback_filters.length}
            </span>
          )}
        </button>
        
        {showFallbackFilters && (
          <div className="mt-3 space-y-3">
            <p className="text-xs text-gray-500">
              Used when primary source filters yield no results. Provides a secondary search strategy.
            </p>
            
            {(entity.fallback_filters || []).map((filter, idx) => (
              <SourceFilterEditor
                key={idx}
                filter={filter}
                libnatcrOptions={libnatcrOptions}
                onChange={(field, value) => updateSourceFilter(idx, field, value, true)}
                onRemove={() => removeSourceFilter(idx, true)}
              />
            ))}
            
            <button
              type="button"
              className="btn-secondary inline-flex items-center space-x-1 text-sm"
              onClick={() => addSourceFilter(true)}
            >
              <Plus className="w-3 h-3" />
              <span>Add Fallback Filter</span>
            </button>
          </div>
        )}
      </div>
      
      {/* Fallback to All Documents Toggle */}
      <div className="border-l-4 border-purple-200 pl-3 bg-purple-50 rounded-r p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id={`fallback-to-all-${entity.name}`}
              checked={entity.fallback_to_all || false}
              onChange={(e) => update('fallback_to_all', e.target.checked)}
              className="h-4 w-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
            />
            <label htmlFor={`fallback-to-all-${entity.name}`} className="text-sm font-medium text-gray-700">
              Fallback to all documents
            </label>
          </div>
        </div>
        <p className="text-xs text-gray-500 mb-2">
          When enabled, if source filters return no results, retry extraction with all documents.
        </p>
        
        {entity.fallback_to_all && (
          <div className="mt-2">
            <label className="block text-xs text-gray-600 mb-1">Fallback Depth (0 = all documents)</label>
            <input
              type="number"
              min="0"
              value={entity.fallback_depth || 0}
              onChange={(e) => update('fallback_depth', parseInt(e.target.value) || 0)}
              className="w-24 px-2 py-1 border border-gray-300 rounded text-sm"
              placeholder="0"
            />
            <p className="text-xs text-gray-400 mt-1">
              0 = all docs, 1 = most recent only, 2 = two most recent, etc.
            </p>
          </div>
        )}
      </div>
      
      <div className="flex justify-between pt-2 border-t">
        <div className="text-xs text-gray-500">Editing entity</div>
        <button type="button" className="text-red-600 hover:text-red-800 text-sm" onClick={onDelete}>Delete</button>
      </div>
      {/* Master delete modal moved to parent component scope */}
    </div>
  );
}

// Source Filter Editor Component
function SourceFilterEditor({
  filter,
  libnatcrOptions,
  onChange,
  onRemove
}: {
  filter: SourceFilter;
  libnatcrOptions: string[];
  onChange: (field: keyof SourceFilter, value: any) => void;
  onRemove: () => void;
}) {
  return (
    <div className="border border-gray-300 rounded-md p-3 bg-white space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-gray-600">Filter Configuration</span>
        <button
          type="button"
          className="text-red-500 hover:text-red-700"
          onClick={onRemove}
          title="Remove filter"
        >
          <Minus className="w-4 h-4" />
        </button>
      </div>
      
      <div className="grid grid-cols-2 gap-2">
        {/* LIBNATCR - Required */}
        <div className="col-span-2">
          <label className="block text-xs text-gray-600 mb-1">Report Type (LIBNATCR) *</label>
          <select
            className="input-field text-sm"
            value={filter.libnatcr || ''}
            onChange={(e) => onChange('libnatcr', e.target.value)}
          >
            <option value="">Select report type...</option>
            {libnatcrOptions.map(opt => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
            <option value="_custom">-- Custom --</option>
          </select>
          {filter.libnatcr === '_custom' && (
            <input
              className="input-field text-sm mt-1"
              placeholder="Enter custom LIBNATCR"
              onChange={(e) => onChange('libnatcr', e.target.value)}
            />
          )}
        </div>
        
        {/* Title Keyword - Optional */}
        <div>
          <label className="block text-xs text-gray-600 mb-1">Title Keyword</label>
          <input
            className="input-field text-sm"
            value={filter.title_keyword || ''}
            onChange={(e) => onChange('title_keyword', e.target.value || undefined)}
            placeholder="e.g., NUCLEAIRE"
          />
          <p className="text-xs text-gray-400 mt-0.5">Use | for OR: A|B</p>
        </div>
        
        {/* Content Keyword - Optional */}
        <div>
          <label className="block text-xs text-gray-600 mb-1">Content Keyword</label>
          <input
            className="input-field text-sm"
            value={filter.content_keyword || ''}
            onChange={(e) => onChange('content_keyword', e.target.value || undefined)}
            placeholder="e.g., PANENDOSCOPIE"
          />
          <p className="text-xs text-gray-400 mt-0.5">Searches in TEXTE</p>
        </div>
        
        {/* Depth - Temporal */}
        <div>
          <label className="block text-xs text-gray-600 mb-1">Depth (Temporal)</label>
          <select
            className="input-field text-sm"
            value={filter.depth ?? 0}
            onChange={(e) => onChange('depth', parseInt(e.target.value))}
          >
            <option value={0}>All matching</option>
            <option value={1}>Newest 1</option>
            <option value={2}>Newest 2</option>
            <option value={3}>Newest 3</option>
            <option value={5}>Newest 5</option>
            <option value={-1}>Oldest 1</option>
            <option value={-2}>Oldest 2</option>
            <option value={-3}>Oldest 3</option>
            <option value={-5}>Oldest 5</option>
          </select>
        </div>
        
        {/* Focus Section - Optional */}
        <div>
          <label className="block text-xs text-gray-600 mb-1">Focus Section</label>
          <input
            className="input-field text-sm"
            value={filter.focus_section || ''}
            onChange={(e) => onChange('focus_section', e.target.value || undefined)}
            placeholder="e.g., conclusion"
          />
          <p className="text-xs text-gray-400 mt-0.5">Extract specific section</p>
        </div>
      </div>
    </div>
  );
}