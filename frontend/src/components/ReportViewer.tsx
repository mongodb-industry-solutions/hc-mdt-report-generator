import React, { useState, useEffect, useMemo } from 'react';
import { X, ChevronDown, ChevronRight, User, Stethoscope, Target, Presentation, Settings, Activity, FileText, List, Eye, Search, AlertCircle } from 'lucide-react';
import { Report, ReportEntity, EntityTemplate, SectionConfig } from '../types';
import { apiService } from '../services/api';
import SourceViewerModal from './SourceViewerModal';
import ReportDisclaimer from './ReportDisclaimer';

interface ReportViewerProps {
  report: Report;
  onClose: () => void;
}

const NotFoundEntityCard = ({ entityName, category, sectionColor }: { entityName: string; category: string; sectionColor?: string }) => {
  return (
    <div 
      className="border-2 border-dashed rounded-lg p-4 transition-all duration-200"
      style={{ 
        backgroundColor: sectionColor ? `${sectionColor}20` : '#F3F4F6', 
        borderColor: sectionColor ? `${sectionColor}60` : '#D1D5DB' 
      }}
    >
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0 mt-0.5">
          <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
            <Search className="w-4 h-4 text-gray-400" />
          </div>
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2 mb-1">
            <h3 className="text-sm font-medium text-gray-900 truncate">
              {entityName}
            </h3>
            <div className="flex-shrink-0">
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                Not Found
              </span>
            </div>
          </div>
          
          <div className="flex items-center space-x-2 text-xs text-gray-500">
            <AlertCircle className="w-3 h-3" />
            <span>No data found in processed documents</span>
          </div>
          
          <div className="mt-2 text-xs text-gray-400">
            This entity was expected but not found in any of the processed documents. 
            Consider adding this information manually or reviewing the source documents.
          </div>
        </div>
      </div>
    </div>
  );
};

const EntityCard = ({ 
  entity, 
  category, 
  onViewSource, 
  getSectionColorClasses 
}: { 
  entity: ReportEntity; 
  category: string; 
  onViewSource: (filename: string) => void;
  getSectionColorClasses: (categoryName: string, type?: 'background' | 'text' | 'border') => string;
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showFullContent, setShowFullContent] = useState(false);
  const [showMobilizedDocs, setShowMobilizedDocs] = useState(false);
  
  // Get mobilized documents from metadata (persisted from extraction)
  const documentsMobilises = entity.metadata?.documents_mobilises as Array<{
    date: string;
    libnatcr: string;
    title: string;
    filename: string;
  }> | undefined;

  // Filter documents to only show those that were actually used for this entity
  const getRelevantDocuments = () => {
    if (!documentsMobilises) return [];
    
    // For now, return all documents to avoid over-filtering
    // TODO: Implement proper document filtering once we understand the metadata structure better
    return documentsMobilises;
    
    /* Disabled filtering logic until we can debug properly
    const usedFilenames = new Set<string>();
    
    // Strategy 1: For aggregate entities with multiple sources
    if (entity.processing_type === 'aggregate_all_matches' && entity.metadata?.sources && Array.isArray(entity.metadata.sources)) {
      entity.metadata.sources.forEach((source: any) => {
        if (source.filename) {
          usedFilenames.add(source.filename);
        }
      });
    }
    
    // Strategy 2: For entities with values array (detailed breakdown)
    if (entity.values && Array.isArray(entity.values)) {
      entity.values.forEach((value: any) => {
        if (value.metadata?.filename) {
          usedFilenames.add(value.metadata.filename);
        }
      });
    }
    
    // Strategy 3: For single source entities
    if (entity.metadata?.filename) {
      usedFilenames.add(entity.metadata.filename);
    }
    
    console.log(`Entity: ${entity.entity_name}, Found sources:`, Array.from(usedFilenames), 'Processing type:', entity.processing_type);
    
    // If we found specific sources, filter documents
    if (usedFilenames.size > 0) {
      const filtered = documentsMobilises.filter(doc => usedFilenames.has(doc.filename));
      console.log(`Filtered documents for ${entity.entity_name}:`, filtered.length, 'out of', documentsMobilises.length);
      return filtered;
    }
    
    // If no specific sources found, return all documents but log it
    console.log(`No specific sources found for ${entity.entity_name}, showing all documents`);
    return documentsMobilises;
    */
  };

  const relevantDocuments = getRelevantDocuments();

  // Helper function to render entity values
  const renderEntityValue = () => {
    // Handle multiple match entities (array values)
    if (Array.isArray(entity.value)) {
      if (entity.value.length === 0) {
        return <span className="text-sm text-gray-500 italic">No values found</span>;
      }
      
      return (
        <div className="mt-2">
          <div className="flex items-center space-x-2 mb-2">
            <List className="w-4 h-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">
              Multiple Values ({entity.value.length}):
            </span>
          </div>
          <div className="space-y-1 pl-6">
            {entity.value.map((val, index) => (
              <div key={index} className="flex items-start space-x-2">
                <span className="text-xs text-gray-400 mt-1">•</span>
                <span className="text-sm text-gray-800 break-words leading-relaxed">
                  {val}
                </span>
              </div>
            ))}
          </div>
        </div>
      );
    }

    // Handle single values (string)
    if (entity.value) {
      const value = entity.value.toString();
      const isLongContent = value.length > 200;
      const displayValue = !showFullContent && isLongContent 
        ? value.substring(0, 200) + '...' 
        : value;

      return (
        <div className="mt-2">
          <div className="text-sm text-gray-800 break-words leading-relaxed whitespace-pre-wrap">
            {displayValue}
          </div>
          {isLongContent && (
            <button
              onClick={() => setShowFullContent(!showFullContent)}
              className="mt-1 text-xs text-blue-600 hover:text-blue-800 flex items-center space-x-1"
            >
              <Eye className="w-3 h-3" />
              <span>{showFullContent ? 'Show less' : 'Show more'}</span>
            </button>
          )}
        </div>
      );
    }

    // Handle aggregated values
    if (entity.aggregated_value) {
      const value = entity.aggregated_value.toString();
      const isLongContent = value.length > 200;
      const displayValue = !showFullContent && isLongContent 
        ? value.substring(0, 200) + '...' 
        : value;

      return (
        <div className="mt-2">
          <div className="text-sm text-gray-800 break-words leading-relaxed whitespace-pre-wrap">
            {displayValue}
          </div>
          {isLongContent && (
            <button
              onClick={() => setShowFullContent(!showFullContent)}
              className="mt-1 text-xs text-blue-600 hover:text-blue-800 flex items-center space-x-1"
            >
              <Eye className="w-3 h-3" />
              <span>{showFullContent ? 'Show less' : 'Show more'}</span>
            </button>
          )}
        </div>
      );
    }

    return <span className="text-sm text-gray-500 italic mt-2 block">No value available</span>;
  };

  // Check if entity has detailed values to show in expandable section
  const hasDetailedValues = entity.values && entity.values.length > 0;

  return (
    <div className="border border-gray-200 rounded-lg p-4 mb-3 hover:shadow-md transition-shadow duration-200">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2 mb-2">
            <h4 className="font-medium text-gray-900 break-words">{entity.entity_name}</h4>
            <span className={`px-2 py-1 text-xs rounded-full whitespace-nowrap ${getSectionColorClasses(category)}`}>
              {category}
            </span>
          </div>
        </div>
        
        {hasDetailedValues && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded ml-2 flex-shrink-0"
            title="Show detailed breakdown"
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>
        )}
      </div>

      {/* Main Content */}
      <div className="min-h-0">
        {renderEntityValue()}
      </div>

      {/* Expandable detailed values section */}
      {isExpanded && hasDetailedValues && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <h5 className="text-sm font-medium text-gray-700 mb-3 flex items-center space-x-2">
            <List className="w-4 h-4" />
            <span>Detailed Breakdown ({entity.values!.length} sources):</span>
          </h5>
          <div className="space-y-3">
            {entity.values!.map((value, index) => (
              <div key={index} className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                <div className="text-sm text-gray-900 mb-2 break-words leading-relaxed whitespace-pre-wrap">
                  {value.value}
                </div>
                <div className="text-xs text-gray-500 flex flex-wrap gap-x-4 gap-y-1">
                  <span className="flex items-center space-x-1">
                    <span className="font-medium">Source:</span>
                    <button
                      onClick={() => onViewSource(value.metadata.filename)}
                      className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                      title="Click to view source document"
                    >
                      {value.metadata.filename}
                    </button>
                  </span>
                  {value.metadata.section_id && (
                    <span className="flex items-center space-x-1">
                      <span className="font-medium">Section:</span>
                      <span>{value.metadata.section_id}</span>
                    </span>
                  )}
                  {value.metadata.page_id && (
                    <span className="flex items-center space-x-1">
                      <span className="font-medium">Page:</span>
                      <span>{value.metadata.page_id}</span>
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Collapsible Documents in use section - only shown when source filters were used */}
      {relevantDocuments && relevantDocuments.length > 0 && (
        <div className="mt-3 pt-2 border-t border-gray-100">
          <button
            onClick={() => setShowMobilizedDocs(!showMobilizedDocs)}
            className="flex items-center space-x-2 text-xs font-medium text-gray-600 hover:text-gray-800 transition-colors"
          >
            {showMobilizedDocs ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
            <span>
              Documents in use ({relevantDocuments.length})
            </span>
            <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
              filtering not available
            </span>
          </button>
          
          {showMobilizedDocs && (
            <div className="mt-2 space-y-2 ml-6">
              {/* Documents list */}
              <div className="space-y-1">
                {relevantDocuments.map((doc, index) => (
                  <div
                    key={index}
                    className="flex items-start text-xs bg-blue-50 px-3 py-1.5 rounded border border-blue-200"
                  >
                    <span className="text-blue-600 mr-2 font-mono shrink-0">
                      [{doc.date || '--------'}]
                    </span>
                    <span className="font-medium text-blue-800 mr-2 shrink-0">
                      {doc.libnatcr || 'Unknown'}
                    </span>
                    <span className="text-blue-700 truncate flex-1">
                      {doc.title || '-'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Metadata footer */}
      {entity.metadata && !hasDetailedValues && (
        <div className="mt-3 pt-2 border-t border-gray-100">
          <div className="text-xs text-gray-500 flex flex-wrap gap-x-4 gap-y-1">
            {/* Handle aggregate entities with multiple sources */}
            {entity.processing_type === 'aggregate_all_matches' && entity.metadata.sources && Array.isArray(entity.metadata.sources) ? (
              <div className="w-full">
                {(() => {
                  // Remove duplicates by filename while preserving first occurrence for metadata
                  const uniqueSources = entity.metadata.sources!.filter((source: any, index: number, arr: any[]) => 
                    arr.findIndex((s: any) => s.filename === source.filename) === index
                  );
                  
                  // Check if sources have useful metadata (not just "Unknown")
                  const hasUsefulSourceMetadata = uniqueSources.some(
                    (s: any) => (s.CR_DATE || s.DATEACTE) && s.LIBNATCR && s.LIBNATCR !== 'Unknown'
                  );
                  
                  // If sources are missing metadata but we have documents_mobilises, use that instead
                  const displaySources = (!hasUsefulSourceMetadata && documentsMobilises && documentsMobilises.length > 0)
                    ? documentsMobilises.map(d => ({
                        CR_DATE: d.date,
                        LIBNATCR: d.libnatcr,
                        TITLE: d.title,
                        filename: d.filename
                      }))
                    : uniqueSources;
                  
                  return (
                    <>
                      <span className="font-medium">
                        Sources d'extraction ({displaySources.length}):
                        {entity.metadata?.used_fallback && (
                          <span className="ml-2 text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded">
                            via fallback
                          </span>
                        )}
                      </span>
                      
                      {/* List of source reports with date, type, and title */}
                      <div className="mt-2 space-y-1 w-full">
                        {displaySources.map((source: any, index: number) => {
                          const hasStructuredData = source.LIBNATCR || source.libnatcr;
                          const reportType = source.LIBNATCR || source.libnatcr || 'Document complet';
                          const reportTitle = source.TITLE || source.title || source.display_name;
                          // Format date: prefer CR_DATE format (YYYYMMDD), otherwise try to extract date from ISO
                          const rawDate = source.CR_DATE || source.DATEACTE || source.date || '';
                          const displayDate = rawDate.includes('T') 
                            ? rawDate.split('T')[0].replace(/-/g, '') 
                            : rawDate;
                          
                          return (
                            <div
                              key={index}
                              className="flex items-start text-xs bg-gray-50 px-3 py-1.5 rounded border border-gray-200"
                            >
                              <span className="text-gray-500 mr-2 font-mono shrink-0">
                                [{displayDate || '--------'}]
                              </span>
                              <span className="font-medium text-gray-700 mr-2 shrink-0">
                                {reportType}
                              </span>
                              {/* Only show title if we have structured data with actual title */}
                              {hasStructuredData && reportTitle && (
                                <span className="text-gray-600 truncate flex-1">
                                  {reportTitle}
                                </span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                      
                      {/* Single file link at bottom */}
                      {(displaySources[0]?.filename || uniqueSources[0]?.filename) && (
                        <div className="mt-2 pt-2 border-t border-gray-200 w-full">
                          <button
                            onClick={() => onViewSource(displaySources[0]?.filename || uniqueSources[0]?.filename)}
                            className="text-blue-600 hover:text-blue-800 hover:underline text-xs flex items-center space-x-1"
                          >
                            <span>📄</span>
                            <span>{displaySources[0]?.filename || uniqueSources[0]?.filename}</span>
                          </button>
                        </div>
                      )}
                    </>
                  );
                })()}
              </div>
            ) : (
              /* Single source handling for non-aggregate entities */
              <span className="flex items-center space-x-1">
                <span className="font-medium">Source:</span>
                {entity.metadata?.filename ? (
                  <button
                    onClick={() => onViewSource(entity.metadata!.filename)}
                    className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                    title="Click to view source document"
                  >
                    {entity.metadata.filename}
                  </button>
                ) : (
                  <span>Unknown source</span>
                )}
              </span>
            )}
            
            {/* Show section and page for non-aggregate entities */}
            {entity.processing_type !== 'aggregate_all_matches' && entity.metadata.section_id && (
              <span className="flex items-center space-x-1">
                <span className="font-medium">Section:</span>
                <span>{entity.metadata.section_id}</span>
              </span>
            )}
            {entity.processing_type !== 'aggregate_all_matches' && entity.metadata.page_id && (
              <span className="flex items-center space-x-1">
                <span className="font-medium">Page:</span>
                <span>{entity.metadata.page_id}</span>
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default function ReportViewer({ report, onClose }: ReportViewerProps) {
  const [sourceViewerModal, setSourceViewerModal] = useState<{ isOpen: boolean; filename: string }>({
    isOpen: false,
    filename: ''
  });
  
  // Template and sections state
  const [activeTemplate, setActiveTemplate] = useState<EntityTemplate | null>(null);
  const [isTemplateLoading, setIsTemplateLoading] = useState(true);

  // Load active template on mount
  useEffect(() => {
    const loadActiveTemplate = async () => {
      try {
        setIsTemplateLoading(true);
        const { template } = await apiService.getActiveTemplate();
        setActiveTemplate(template);
      } catch (error) {
        console.error('Failed to load active template:', error);
        // Fallback to create a basic template structure if none exists
        setActiveTemplate({ 
          id: 'fallback', 
          name: 'Default Template', 
          entities: [], 
          sections: [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        });
      } finally {
        setIsTemplateLoading(false);
      }
    };

    loadActiveTemplate();
  }, []);

  const handleViewSource = (filename: string) => {
    setSourceViewerModal({ isOpen: true, filename });
  };

  const handleCloseSourceViewer = () => {
    setSourceViewerModal({ isOpen: false, filename: '' });
  };

  // Get sections from active template, fallback to default if none
  const getTemplateSections = (): SectionConfig[] => {
    if (!activeTemplate?.sections || activeTemplate.sections.length === 0) {
      // Fallback to default sections if template has no sections
      return [
        { id: 'default', name: 'Uncategorized', color: '#D1D5DB', order: 0 }
      ];
    }
    return activeTemplate.sections.sort((a, b) => a.order - b.order);
  };

  // Get unique categories from template sections
  const semanticCategories = getTemplateSections().map(section => section.name);
  
  // Helper function to get semantic category for an entity
  const getEntityCategory = (entityName: string): string => {
    if (!activeTemplate?.entities) return 'Uncategorized';
    
    // Find the entity in the template
    const templateEntity = activeTemplate.entities.find(e => e.name === entityName);
    if (!templateEntity?.section_id) return 'Uncategorized';
    
    // Find the section by ID
    const section = getTemplateSections().find(s => s.id === templateEntity.section_id);
    return section?.name || 'Uncategorized';
  };

  // Helper function to get section color from template
  const getSectionColor = (categoryName: string): string => {
    const section = getTemplateSections().find(s => s.name === categoryName);
    return section?.color || '#D1D5DB'; // Default to soft gray if not found
  };

  // Convert section color to CSS classes and inline styles for different opacity levels
  const getSectionColorClasses = (categoryName: string, type: 'background' | 'text' | 'border' = 'background'): string => {
    const color = getSectionColor(categoryName);
    
    // Use a more reliable approach with predefined Tailwind classes for pastel colors
    const colorToTailwind: { [key: string]: { bg: string; text: string; border: string } } = {
      '#A5B4FC': { bg: 'bg-indigo-100 text-indigo-800', text: 'text-indigo-800', border: 'border-indigo-200' },
      '#86EFAC': { bg: 'bg-green-100 text-green-800', text: 'text-green-800', border: 'border-green-200' },
      '#FDE047': { bg: 'bg-yellow-100 text-yellow-800', text: 'text-yellow-800', border: 'border-yellow-200' },
      '#FCA5A5': { bg: 'bg-red-100 text-red-800', text: 'text-red-800', border: 'border-red-200' },
      '#C4B5FD': { bg: 'bg-purple-100 text-purple-800', text: 'text-purple-800', border: 'border-purple-200' },
      '#67E8F9': { bg: 'bg-cyan-100 text-cyan-800', text: 'text-cyan-800', border: 'border-cyan-200' },
      '#FDBA74': { bg: 'bg-orange-100 text-orange-800', text: 'text-orange-800', border: 'border-orange-200' },
      '#BEF264': { bg: 'bg-lime-100 text-lime-800', text: 'text-lime-800', border: 'border-lime-200' },
      '#F9A8D4': { bg: 'bg-pink-100 text-pink-800', text: 'text-pink-800', border: 'border-pink-200' },
      '#D1D5DB': { bg: 'bg-gray-100 text-gray-800', text: 'text-gray-800', border: 'border-gray-200' },
      // Keep old colors for backward compatibility
      '#3B82F6': { bg: 'bg-blue-100 text-blue-800', text: 'text-blue-800', border: 'border-blue-200' },
      '#10B981': { bg: 'bg-green-100 text-green-800', text: 'text-green-800', border: 'border-green-200' },
      '#F59E0B': { bg: 'bg-yellow-100 text-yellow-800', text: 'text-yellow-800', border: 'border-yellow-200' },
      '#EF4444': { bg: 'bg-red-100 text-red-800', text: 'text-red-800', border: 'border-red-200' },
      '#8B5CF6': { bg: 'bg-purple-100 text-purple-800', text: 'text-purple-800', border: 'border-purple-200' },
      '#06B6D4': { bg: 'bg-cyan-100 text-cyan-800', text: 'text-cyan-800', border: 'border-cyan-200' },
      '#F97316': { bg: 'bg-orange-100 text-orange-800', text: 'text-orange-800', border: 'border-orange-200' },
      '#84CC16': { bg: 'bg-lime-100 text-lime-800', text: 'text-lime-800', border: 'border-lime-200' },
      '#EC4899': { bg: 'bg-pink-100 text-pink-800', text: 'text-pink-800', border: 'border-pink-200' },
      '#6B7280': { bg: 'bg-gray-100 text-gray-800', text: 'text-gray-800', border: 'border-gray-200' }
    };
    
    const colorMapping = colorToTailwind[color] || colorToTailwind['#D1D5DB']; // Default to soft gray
    
    switch (type) {
      case 'text': return colorMapping.text;
      case 'border': return colorMapping.border;
      default: return colorMapping.bg;
    }
  };

  // Helper function to get a normalized entity value
  const getEntityValue = (entity: any): string => {
    if (!entity) return '';
    // Backend may use either `value` or `entity_value`
    // Treat null/undefined/empty string as not found
    return (entity.value ?? entity.entity_value ?? '').toString().trim();
  };

  // Helper to decide if an entity should count as "found"
  const isFoundEntity = (entity: any): boolean => {
    const val = getEntityValue(entity);
    const status = entity?.metadata?.status;
    // Exclude placeholders explicitly marked as not_found and entities with empty values
    return status !== 'not_found' && val.length > 0;
  };

  // Helper function to organize entities by semantic categories
  const organizeEntitiesByCategory = () => {
    const categorizedEntities: Record<string, ReportEntity[]> = {};
    const categorizedNotFound: Record<string, string[]> = {};
    
    // Initialize all categories
    semanticCategories.forEach(category => {
      categorizedEntities[category] = [];
      categorizedNotFound[category] = [];
    });
    categorizedEntities['Uncategorized'] = [];
    categorizedNotFound['Uncategorized'] = [];

    // Collect all not-found entities from different processing types
    const allNotFoundEntities: string[] = [];
    
    // Check the new structure: content.ner_results.raw_results_by_type
    const rawResults = report.content?.ner_results?.raw_results_by_type;
    if (rawResults) {
      if (rawResults.first_match?.not_found_entities) {
        console.log('Found first_match not_found_entities:', rawResults.first_match.not_found_entities.length);
        allNotFoundEntities.push(...rawResults.first_match.not_found_entities.map((e: any) => e.entity_name));
      }
      if (rawResults.multiple_match?.not_found_entities) {
        console.log('Found multiple_match not_found_entities:', rawResults.multiple_match.not_found_entities.length);
        allNotFoundEntities.push(...rawResults.multiple_match.not_found_entities.map((e: any) => e.entity_name));
      }
      if (rawResults.aggregate_all_matches?.not_found_entities) {
        console.log('Found aggregate_all_matches not_found_entities:', rawResults.aggregate_all_matches.not_found_entities.length);
        allNotFoundEntities.push(...rawResults.aggregate_all_matches.not_found_entities.map((e: any) => e.entity_name));
      }
    }
    
    // Fallback: check old structure for backward compatibility
    if (allNotFoundEntities.length === 0) {
      if (report.content?.first_match?.not_found_entities) {
        console.log('Found first_match not_found_entities (old structure):', report.content.first_match.not_found_entities.length);
        allNotFoundEntities.push(...report.content.first_match.not_found_entities.map((e: any) => e.entity_name));
      }
      if (report.content?.multiple_match?.not_found_entities) {
        console.log('Found multiple_match not_found_entities (old structure):', report.content.multiple_match.not_found_entities.length);
        allNotFoundEntities.push(...report.content.multiple_match.not_found_entities.map((e: any) => e.entity_name));
      }
      if (report.content?.aggregate_all_matches?.not_found_entities) {
        console.log('Found aggregate_all_matches not_found_entities (old structure):', report.content.aggregate_all_matches.not_found_entities.length);
        allNotFoundEntities.push(...report.content.aggregate_all_matches.not_found_entities.map((e: any) => e.entity_name));
      }
    }

    // Remove duplicates from not-found entities
    const uniqueNotFoundEntities = [...new Set(allNotFoundEntities)];
    console.log('Total unique not-found entities:', uniqueNotFoundEntities.length, uniqueNotFoundEntities);

    // Organize not-found entities by category
    uniqueNotFoundEntities.forEach(entityName => {
      const category = getEntityCategory(entityName);
      if (categorizedNotFound[category]) {
        categorizedNotFound[category].push(entityName);
      } else {
        categorizedNotFound['Uncategorized'].push(entityName);
      }
    });

    // Check for new structure first
    if (report.content?.ner_results?.entities) {
      const entities = report.content.ner_results.entities;
      
      entities.forEach(entity => {
        if (!isFoundEntity(entity)) return; // Only count/display found entities here
        const category = getEntityCategory(entity.entity_name);
        if (categorizedEntities[category]) {
          categorizedEntities[category].push(entity);
        } else {
          categorizedEntities['Uncategorized'].push(entity);
        }
      });
      
      // Note: For new structure, not_found_entities are still in the old structure sections
      // So we still need to collect them from there even when using ner_results
    } else {
      // Fallback to old structure for backward compatibility
      const allEntities: ReportEntity[] = [];
      
      if (report.content?.first_match?.found_entities) {
        allEntities.push(...report.content.first_match.found_entities);
      }
      if (report.content?.multiple_match?.found_entities) {
        allEntities.push(...report.content.multiple_match.found_entities);
      }
      if (report.content?.aggregate_all_matches?.found_entities) {
        allEntities.push(...report.content.aggregate_all_matches.found_entities);
      }

      allEntities.forEach(entity => {
        if (!isFoundEntity(entity)) return; // Only count/display found entities here
        const category = getEntityCategory(entity.entity_name);
        if (categorizedEntities[category]) {
          categorizedEntities[category].push(entity);
        } else {
          categorizedEntities['Uncategorized'].push(entity);
        }
      });
    }

    // If we still have no not_found from raw structures, derive from entities placeholders
    if (uniqueNotFoundEntities.length === 0 && report.content?.ner_results?.entities) {
      const placeholders = report.content.ner_results.entities.filter((e: any) => e?.metadata?.status === 'not_found');
      placeholders.forEach((entity: any) => {
        const entityName = entity?.entity_name ?? '';
        if (!entityName) return;
        const category = getEntityCategory(entityName);
        if (categorizedNotFound[category]) {
          if (!categorizedNotFound[category].includes(entityName)) {
            categorizedNotFound[category].push(entityName);
          }
        } else {
          categorizedNotFound['Uncategorized'].push(entityName);
        }
      });
    }

    return { entities: categorizedEntities, notFound: categorizedNotFound };
  };

  const organizedData = organizeEntitiesByCategory();
  const organizedEntities = organizedData.entities;
  const organizedNotFound = organizedData.notFound;

  // Create tabs for categories that have entities or not-found entities
  const availableCategories = useMemo(() => {
    const categories = semanticCategories.filter(category => 
      (organizedEntities[category] && organizedEntities[category].length > 0) ||
      (organizedNotFound[category] && organizedNotFound[category].length > 0)
    );
    
    // Add uncategorized if it has entities or not-found entities
    if ((organizedEntities['Uncategorized'] && organizedEntities['Uncategorized'].length > 0) ||
        (organizedNotFound['Uncategorized'] && organizedNotFound['Uncategorized'].length > 0)) {
      categories.push('Uncategorized');
    }
    
    return categories;
  }, [semanticCategories, organizedEntities, organizedNotFound]);

  // Initialize activeTab with default value, will be updated when template loads
  const [activeTab, setActiveTab] = useState<string>('');
  const [hoveredTab, setHoveredTab] = useState<string | null>(null);

  // Set activeTab to first available category when template loads and categories are available
  useEffect(() => {
    if (!isTemplateLoading && availableCategories.length > 0 && !activeTab) {
      setActiveTab(availableCategories[0]);
    }
  }, [isTemplateLoading, availableCategories, activeTab]);

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'Patient Information':
        return User;
      case 'Clinical Summary':
        return Stethoscope;
      case 'General Health and Functional Status':
        return Activity;
      case 'Laboratory and Exploration Results':
        return Search;
      case 'Medical Diagnoses':
        return AlertCircle;
      case 'Psychological and Social Factors':
        return User;
      case 'Patient and Tumor Characteristics':
        return Target;
      case 'Presentation Reason':
        return Presentation;
      case 'MDT Recommendation (EXPERIMENTAL - Medical validation required)':
        return FileText;
      case 'DRAFT System Recommendation':
        return Settings;
      default:
        return Activity;
    }
  };

  const getCategoryColor = (category: string, isActive: boolean = false, isHovered: boolean = false): { className: string; style: React.CSSProperties } => {
    const color = getSectionColor(category);
    
    if (isActive) {
      return {
        className: 'border text-gray-800',
        style: {
          borderColor: color,
          backgroundColor: `${color}30`,
          color: '#1F2937'
        }
      };
    } else if (isHovered) {
      return {
        className: 'border text-gray-800 transition-all duration-200',
        style: {
          borderColor: `${color}80`,
          backgroundColor: `${color}20`,
          color: '#1F2937'
        }
      };
    } else {
      return {
        className: 'border text-gray-600 transition-all duration-200',
        style: {
          borderColor: `${color}60`,
          backgroundColor: `${color}10`,
          color: '#4B5563'
        }
      };
    }
  };

  const currentTabEntities = organizedEntities[activeTab] || [];
  const currentTabNotFound = organizedNotFound[activeTab] || [];

  if (!report.content) {
    return (
      <div className="w-full h-full bg-white rounded-lg shadow-xl border border-gray-200 flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">Report Viewer</h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 flex items-center justify-center p-6">
          <p className="text-gray-500">No content available for this report.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full bg-white rounded-lg shadow-xl border border-gray-200 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div>
          <h2 className="text-lg font-medium text-gray-900">Report Viewer</h2>
          <p className="text-sm text-gray-500">{report.title}</p>
        </div>
        <button
          onClick={onClose}
          className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
          title="Close report viewer"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Disclaimer */}
      {/* <div className="max-h-96 overflow-y-auto border-b border-gray-200">
        <ReportDisclaimer 
          reportDate={new Date(report.created_at).toLocaleString()}
          aiModel="AI Large Language Model (AWS Bedrock/Mistral)"
          version="Proof of Concept v1.0"
        />
      </div> */}

      {/* Loading state for template */}
      {isTemplateLoading && (
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3"></div>
            <p className="text-gray-500">Loading template configuration...</p>
          </div>
        </div>
      )}

      {/* Main content - only show when template is loaded */}
      {!isTemplateLoading && (
        <>
          {/* Summary */}
          <div className="p-4 bg-gray-50 border-b border-gray-200">
        <h3 className="font-medium text-gray-900 mb-2">Entity Categories Summary</h3>
        <div className="grid grid-cols-2 gap-4 text-sm mb-3">
          <div>
            <span className="text-gray-600">Found Entities:</span>{' '}
            <span className="font-medium">
              {Object.values(organizedEntities).reduce((sum, entities) => sum + entities.length, 0)}
            </span>
          </div>
          <div>
            <span className="text-gray-600">Not Found:</span>{' '}
            <span className="font-medium text-orange-600">
              {Object.values(organizedNotFound).reduce((sum, entities) => sum + entities.length, 0)}
            </span>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
          {availableCategories.map(category => {
            const foundCount = organizedEntities[category]?.length || 0;
            const notFoundCount = organizedNotFound[category]?.length || 0;
            return (
              <div key={category} className="flex justify-between">
                <span className="text-gray-600 truncate mr-2">{category}:</span>
                <div className="flex items-center space-x-2 flex-shrink-0">
                  <span className="font-medium text-green-600">{foundCount}</span>
                  {notFoundCount > 0 && (
                    <>
                      <span className="text-gray-400">|</span>
                      <span className="font-medium text-orange-600">{notFoundCount}</span>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Content Area - Flex layout with sidebar and content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar - Entity Categories */}
        <div className="w-80 bg-gray-50 border-r border-gray-200 overflow-y-auto">
          <div className="p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Entity Categories</h3>
            <div className="space-y-1">
              {availableCategories.map((category) => {
                const Icon = getCategoryIcon(category);
                const foundCount = organizedEntities[category]?.length || 0;
                const notFoundCount = organizedNotFound[category]?.length || 0;
                const isActive = activeTab === category;
                const isHovered = hoveredTab === category;
                const categoryColors = getCategoryColor(category, isActive, isHovered);
                return (
                  <button
                    key={category}
                    onClick={() => setActiveTab(category)}
                    onMouseEnter={() => setHoveredTab(category)}
                    onMouseLeave={() => setHoveredTab(null)}
                    className={`
                      w-full flex items-start space-x-3 p-3 text-sm font-medium rounded-lg
                      ${categoryColors.className}
                    `}
                    style={categoryColors.style}
                  >
                    <Icon className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <div className="flex-1 text-left">
                      <div className="font-medium">{category}</div>
                      <div className="flex items-center space-x-2 mt-1">
                        <span className={`
                          px-2 py-1 rounded-full text-xs font-medium
                          ${isActive
                            ? 'bg-green-100 text-green-700'
                            : 'bg-green-50 text-green-600'
                          }
                        `}>
                          {foundCount} found
                        </span>
                        {notFoundCount > 0 && (
                          <span className={`
                            px-2 py-1 rounded-full text-xs font-medium
                            ${isActive
                              ? 'bg-orange-100 text-orange-700'
                              : 'bg-orange-50 text-orange-600'
                            }
                          `}>
                            {notFoundCount} missing
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="w-full">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">{activeTab}</h2>
            {currentTabEntities.length > 0 || currentTabNotFound.length > 0 ? (
              <div className="space-y-3">
                {/* Found Entities Section */}
                {currentTabEntities.length > 0 && (
                  <div className="space-y-1">
                    {currentTabEntities.map((entity: ReportEntity, index: number) => (
                      <EntityCard
                        key={`found-${index}`}
                        entity={entity}
                        category={activeTab}
                        onViewSource={handleViewSource}
                        getSectionColorClasses={getSectionColorClasses}
                      />
                    ))}
                  </div>
                )}
                
                {/* Not Found Entities Section */}
                {currentTabNotFound.length > 0 && (
                  <div className="space-y-1">
                    {/* Separator if there are both found and not-found entities */}
                    {currentTabEntities.length > 0 && (
                      <div className="flex items-center py-3">
                        <div className="flex-1 border-t border-gray-200"></div>
                        <div className="px-3 text-xs font-medium text-gray-500 bg-gray-50 rounded-full">
                          Expected but not found
                        </div>
                        <div className="flex-1 border-t border-gray-200"></div>
                      </div>
                    )}
                    
                    {currentTabNotFound.map((entityName: string, index: number) => (
                      <NotFoundEntityCard
                        key={`not-found-${index}`}
                        entityName={entityName}
                        category={activeTab}
                        sectionColor={getSectionColor(activeTab)}
                      />
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8">
                <div className="text-gray-400 mb-2">
                  <FileText className="w-8 h-8 mx-auto" />
                </div>
                <p className="text-gray-500">No entities found for this category.</p>
              </div>
            )}
          </div>
        </div>
      </div>
        </>
      )}

      {/* Source Viewer Modal */}
      <SourceViewerModal
        isOpen={sourceViewerModal.isOpen}
        onClose={handleCloseSourceViewer}
        patientId={report.patient_id}
        filename={sourceViewerModal.filename}
      />
    </div>
  );
} 