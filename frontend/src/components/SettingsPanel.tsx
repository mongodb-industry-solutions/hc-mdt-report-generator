import React, { useState, useEffect } from 'react';
import { X, Settings, Server, BrainCircuit, SlidersHorizontal, ListPlus, Pencil, AlertTriangle, Trash2, Check, Plus, ChevronDown } from 'lucide-react';
import { LLMModel } from '../types';
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
  const [activeTab, setActiveTab] = useState<'general' | 'models'>('general');

  // Model management form state (Add/Edit)
  const [isEditingExisting, setIsEditingExisting] = useState<boolean>(false);
  const [matchId, setMatchId] = useState<string>('');
  const [matchName, setMatchName] = useState<string>('');
  const [isModelFormCollapsed, setIsModelFormCollapsed] = useState<boolean>(true);
  
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
    setIsModelFormCollapsed(false); // Expand the form when editing
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
      setTimeout(() => {
        setModelSaveStatus('idle');
        setIsModelFormCollapsed(true); // Collapse form after successful save
      }, 1200);
    } catch (e) {
      console.error('Error saving model:', e);
      setModelSaveStatus('error');
      setTimeout(() => setModelSaveStatus('idle'), 1600);
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



  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 h-[70vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 flex-shrink-0">
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
        <div className="px-6 pt-4 border-b border-gray-200 flex-shrink-0">
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
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'general' && (
          <div className="h-full overflow-y-auto p-6">
            <form onSubmit={handleSubmit} className="space-y-6">
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
          </div>
          )}

        {activeTab === 'models' && (
          <div className="h-full overflow-y-auto p-6 space-y-6">
            {/* List + Actions */}
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-900">Manage LLM Models</h3>
              <div className="flex items-center space-x-2">
                <button type="button" onClick={() => { startAddNewModel(); setIsModelFormCollapsed(false); }} className="btn-secondary inline-flex items-center space-x-2">
                  <ListPlus className="w-4 h-4" />
                  <span>New Model</span>
                </button>
              </div>
            </div>
            
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

            {/* Collapsible Model Form */}
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => setIsModelFormCollapsed(!isModelFormCollapsed)}
                className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <Plus className="w-4 h-4" />
                  <span className="text-sm font-medium text-gray-900">
                    {isEditingExisting ? 'Edit Model' : 'Add New Model'}
                  </span>
                </div>
                <ChevronDown className={`w-5 h-5 text-gray-500 transition-transform duration-200 ${
                  isModelFormCollapsed ? '' : 'transform rotate-180'
                }`} />
              </button>
              
              {!isModelFormCollapsed && (
                <div className="p-4 space-y-4 bg-white">
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
                    <button type="button" className="btn-secondary" onClick={() => { startAddNewModel(); setIsModelFormCollapsed(true); }}>Cancel</button>
                    <button type="button" className={`btn-primary ${modelSaveStatus === 'saving' ? 'opacity-75 cursor-wait' : ''}`} disabled={modelSaveStatus === 'saving'} onClick={saveModel}>
                      {modelSaveStatus === 'saving' ? 'Saving...' : isEditingExisting ? 'Save Changes' : 'Add Model'}
                    </button>
                  </div>
                </div>
              )}
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
      </div>
      </div>
  );
}


