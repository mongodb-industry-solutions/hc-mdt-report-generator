import React, { useState, useEffect } from 'react';
import { ListPlus, Check, Trash2, AlertTriangle, Plus, Minus, Filter, ChevronDown, ChevronRight, Settings } from 'lucide-react';
import { EntityConfig, EntityDef, EntityTemplate, SourceFilter } from '../types';
import { apiService } from '../services/api';

interface TemplateConfigurationProps {
  onTemplateChange?: (templateId: string) => void;
}

export default function TemplateConfiguration({ onTemplateChange }: TemplateConfigurationProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  // Template management state
  const [templates, setTemplates] = useState<EntityTemplate[]>([]);
  const [activeTemplateId, setActiveTemplateId] = useState<string | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [showTemplateDialog, setShowTemplateDialog] = useState<'create' | 'rename' | null>(null);
  const [templateFormName, setTemplateFormName] = useState('');
  const [templateFormDescription, setTemplateFormDescription] = useState('');
  
  // Entity editing state
  const [entityConfigStatus, setEntityConfigStatus] = useState<'idle' | 'loading' | 'validating' | 'saving' | 'success' | 'error'>('idle');
  const [entityConfig, setEntityConfig] = useState<EntityConfig | null>(null);
  const [selectedEntityIndex, setSelectedEntityIndex] = useState<number>(0);

  // Load templates on component mount
  useEffect(() => {
    const loadEntityConfig = async () => {
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
  }, [templates.length]);

  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplateId(templateId);
    const template = templates.find(t => t.id === templateId);
    if (template) {
      setEntityConfig({ entities: template.entities });
      setSelectedEntityIndex(0);
    }
    onTemplateChange?.(templateId);
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
      onTemplateChange?.(template_id);
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
      onTemplateChange?.(templateId);
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
          onTemplateChange?.(data.templates[0].id);
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
    <div className="bg-green-50 rounded-lg shadow border border-green-200">
      <div 
        className="px-6 py-4 border-b border-green-200 cursor-pointer hover:bg-green-700 hover:text-white transition-colors group"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Settings className="w-5 h-5 text-gray-600 group-hover:text-white" />
            <h3 className="text-lg font-medium text-gray-900 group-hover:text-white">Template Configuration</h3>
            {activeTemplateId && templates.find(t => t.id === activeTemplateId) && (
              <span className="px-2 py-1 bg-green-100 text-green-800 group-hover:bg-white group-hover:text-green-700 text-xs font-medium rounded-full">
                Active: {templates.find(t => t.id === activeTemplateId)?.name}
              </span>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500 group-hover:text-white">
              {entityConfig ? `${entityConfig.entities?.length || 0} entities` : 'Loading...'}
            </span>
            {isExpanded ? <ChevronDown className="w-4 h-4 text-gray-500 group-hover:text-white" /> : <ChevronRight className="w-4 h-4 text-gray-500 group-hover:text-white" />}
          </div>
        </div>
        <p className="text-sm text-gray-500 group-hover:text-white mt-1">
          Configure which clinical entities to extract during report generation. The active template determines what medical information is captured from patient documents.
        </p>
      </div>

      {isExpanded && (
        <div className="p-6 space-y-4">{/* Template Selection Bar */}
          <div className="flex items-center justify-between border-b pb-3 mb-4">
            <div className="flex items-center space-x-3 flex-1">
              <label className="text-sm font-medium text-gray-700">Template:</label>
              <select
                className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent flex-1 max-w-xs"
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
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors shadow-sm inline-flex items-center space-x-2 text-sm font-medium"
                onClick={() => {
                  setTemplateFormName('');
                  setTemplateFormDescription('');
                  setShowTemplateDialog('create');
                }}
              >
                <ListPlus className="w-4 h-4" />
                <span>New Template</span>
              </button>
            </div>
            
            {/* Template Actions */}
            {selectedTemplateId && (
              <div className="flex items-center space-x-2 ml-4">
                {selectedTemplateId !== activeTemplateId && (
                  <button
                    type="button"
                    className="px-3 py-2 bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200 transition-colors inline-flex items-center space-x-1 text-sm"
                    onClick={() => handleActivateTemplate(selectedTemplateId)}
                  >
                    Set as Active
                  </button>
                )}
                {selectedTemplateId === activeTemplateId && (
                  <div className="px-3 py-2 bg-green-50 text-green-700 border border-green-200 rounded-md inline-flex items-center space-x-1 text-sm">
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
            <div className="text-sm text-gray-600 italic bg-gray-50 p-3 rounded">
              {templates.find(t => t.id === selectedTemplateId)?.description}
            </div>
          )}

          {/* Entity Configuration */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Entity List */}
            <div className="md:col-span-1 border border-gray-200 rounded-md max-h-96 overflow-auto bg-white">
              {entityConfig?.entities?.map((e, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setSelectedEntityIndex(idx)}
                  className={`w-full text-left px-3 py-2 border-b last:border-b-0 hover:bg-gray-50 ${selectedEntityIndex === idx ? 'bg-green-50 border-l-4 border-l-green-500' : ''}`}
                >
                  <div className="text-sm text-gray-900 truncate">{e.name || '(unnamed entity)'}</div>
                  <div className="text-xs text-gray-400 truncate">{e.processing_type || '(default)'}</div>
                </button>
              ))}
              <div className="p-2">
                <button
                  type="button"
                  className="w-full px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-all duration-200 text-sm font-medium shadow-sm hover:shadow-md border-2 border-green-600 hover:border-green-700"
                  onClick={() => {
                    const next: EntityConfig = entityConfig ? { ...entityConfig } : { entities: [] };
                    next.entities = [...(next.entities || []), { name: '', type: 'string', processing_type: 'aggregate_all_matches' } as EntityDef];
                    setEntityConfig(next);
                    setSelectedEntityIndex((next.entities.length - 1));
                  }}
                >
                  Add New Entity
                </button>
              </div>
            </div>

            {/* Entity Editor */}
            <div className="md:col-span-2">
              {entityConfig && entityConfig.entities && entityConfig.entities[selectedEntityIndex] && (
                <EntityEditor
                  entity={entityConfig.entities[selectedEntityIndex]}
                  onChange={(updated) => {
                    const next: EntityConfig = { ...(entityConfig as EntityConfig), entities: [...(entityConfig?.entities || [])] };
                    next.entities[selectedEntityIndex] = updated;
                    setEntityConfig(next);
                  }}
                  onDelete={() => {
                    const next: EntityConfig = { ...(entityConfig as EntityConfig), entities: [...(entityConfig?.entities || [])] };
                    next.entities.splice(selectedEntityIndex, 1);
                    setSelectedEntityIndex(0);
                    setEntityConfig(next);
                  }}
                />
              )}
              <div className="flex justify-end space-x-2 mt-4">
                <button
                  type="button"
                  className={`px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors ${entityConfigStatus === 'saving' ? 'opacity-75 cursor-wait' : ''}`}
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

      {/* Template Creation Dialog */}
      {showTemplateDialog === 'create' && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Create New Template</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Template Name *</label>
                <input
                  type="text"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={templateFormName}
                  onChange={(e) => setTemplateFormName(e.target.value)}
                  placeholder="e.g., Pediatric Cancer Template"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description (Optional)</label>
                <textarea
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
                className="px-4 py-2 border-2 border-gray-300 text-gray-700 rounded-md hover:border-red-400 hover:text-red-600 hover:bg-red-50 transition-all duration-200 font-medium"
                onClick={() => setShowTemplateDialog(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors disabled:opacity-50"
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

// Entity Editor component
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
  
  // Common report type options for medical reports
  const libnatcrOptions = [
    'Pathology Report',
    'Radiology Report', 
    'Consultation Report',
    'Operative Report',
    'Examination Report',
    'Multidisciplinary Team Report',
    'Hospitalization Report',
    'Emergency Report'
  ];
  
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

  return (
    <div className="space-y-4 p-4 border border-gray-200 rounded-md bg-gray-50">
      <div className="flex justify-between items-start">
        <h4 className="text-sm font-medium text-gray-900">Configure Entity</h4>
        <button
          type="button"
          onClick={onDelete}
          className="text-red-600 hover:text-red-800"
          title="Delete entity"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
          <input
            type="text"
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            value={entity.name || ''}
            onChange={(e) => update('name', e.target.value)}
            placeholder="Entity name"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
          <select
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            value={entity.type || 'string'}
            onChange={(e) => update('type', e.target.value)}
          >
            <option value="string">string</option>
            <option value="number">number</option>
            <option value="date">date</option>
            <option value="boolean">boolean</option>
          </select>
        </div>

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Processing Type</label>
          <select
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            value={entity.processing_type || 'aggregate_all_matches'}
            onChange={(e) => update('processing_type', e.target.value)}
          >
            <option value="first_match">first_match</option>
            <option value="multiple_matches">multiple_matches</option>
            <option value="aggregate_all_matches">aggregate_all_matches</option>
          </select>
        </div>

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Definition</label>
          <textarea
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            value={entity.definition || ''}
            onChange={(e) => update('definition', e.target.value)}
            placeholder="Describe what this entity represents"
            rows={2}
          />
        </div>

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Extraction Instructions</label>
          <textarea
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            value={entity.extraction_instructions || ''}
            onChange={(e) => update('extraction_instructions', e.target.value)}
            placeholder="Instructions for AI to extract this entity"
            rows={2}
          />
        </div>
      </div>

      {/* Source Filters Section */}
      <div className="border border-gray-200 rounded-lg p-3 bg-blue-50">
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
              Filter reports by type, title keywords, content keywords, and temporal depth.
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
              className="flex items-center space-x-1 text-sm text-blue-600 hover:text-blue-800 bg-blue-100 hover:bg-blue-200 px-3 py-2 rounded-md transition-colors"
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
              className="flex items-center space-x-1 text-sm text-orange-600 hover:text-orange-800 bg-orange-100 hover:bg-orange-200 px-3 py-2 rounded-md transition-colors"
              onClick={() => addSourceFilter(true)}
            >
              <Plus className="w-3 h-3" />
              <span>Add Fallback Filter</span>
            </button>
          </div>
        )}
      </div>
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
        {/* Report Type - Required */}
        <div className="col-span-2">
          <label className="block text-xs text-gray-600 mb-1">Report Type*</label>
          <select
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent mt-1"
              placeholder="Enter custom LIBNATCR"
              onChange={(e) => onChange('libnatcr', e.target.value)}
            />
          )}
        </div>
        
        {/* Title Keyword - Optional */}
        <div>
          <label className="block text-xs text-gray-600 mb-1">Title Keyword</label>
          <input
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            value={filter.title_keyword || ''}
            onChange={(e) => onChange('title_keyword', e.target.value || undefined)}
            placeholder="e.g., Pathology | Radiology"
          />
          <p className="text-xs text-gray-400 mt-0.5">Use | for OR: A|B</p>
        </div>
        
        {/* Content Keyword - Optional */}
        <div>
          <label className="block text-xs text-gray-600 mb-1">Content Keyword</label>
          <input
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            value={filter.content_keyword || ''}
            onChange={(e) => onChange('content_keyword', e.target.value || undefined)}
            placeholder="e.g., tumor | metastasis"
          />
          <p className="text-xs text-gray-400 mt-0.5">Searches in TEXTE</p>
        </div>
        
        {/* Depth - Temporal */}
        <div>
          <label className="block text-xs text-gray-600 mb-1">Depth (Temporal)</label>
          <select
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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