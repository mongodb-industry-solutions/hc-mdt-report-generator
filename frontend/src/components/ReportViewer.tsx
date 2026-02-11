import React, { useState } from 'react';
import { X, ChevronDown, ChevronRight, User, Stethoscope, Target, Presentation, Settings, Activity, FileText, List, Eye, Search, AlertCircle } from 'lucide-react';
import { Report, ReportEntity } from '../types';
import reportGroupingConfig from '../config/report_grouping_config.json';
import SourceViewerModal from './SourceViewerModal';
import ReportDisclaimer from './ReportDisclaimer';

interface ReportViewerProps {
  report: Report;
  onClose: () => void;
}

const NotFoundEntityCard = ({ entityName, category }: { entityName: string; category: string }) => {
  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'Patient Information':
        return 'bg-blue-50 border-blue-200';
      case 'Clinical Summary':
        return 'bg-green-50 border-green-200';
      case 'General Health and Functional Status':
        return 'bg-teal-50 border-teal-200';
      case 'Laboratory and Exploration Results':
        return 'bg-cyan-50 border-cyan-200';
      case 'Medical Diagnoses':
        return 'bg-rose-50 border-rose-200';
      case 'Psychological and Social Factors':
        return 'bg-indigo-50 border-indigo-200';
      case 'Patient and Tumor Characteristics':
        return 'bg-purple-50 border-purple-200';
      case 'Presentation Reason':
        return 'bg-orange-50 border-orange-200';
      case 'MDT Recommendation (EXPERIMENTAL - Medical validation required)':
        return 'bg-amber-50 border-amber-200';
      case 'DRAFT System Recommendation':
        return 'bg-red-50 border-red-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className={`border-2 border-dashed rounded-lg p-4 ${getCategoryColor(category)} transition-all duration-200`}>
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

const EntityCard = ({ entity, category, onViewSource }: { entity: ReportEntity; category: string; onViewSource: (filename: string) => void }) => {
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

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'Patient Information':
        return 'bg-blue-100 text-blue-800';
      case 'Clinical Summary':
        return 'bg-green-100 text-green-800';
      case 'General Health and Functional Status':
        return 'bg-teal-100 text-teal-800';
      case 'Laboratory and Exploration Results':
        return 'bg-cyan-100 text-cyan-800';
      case 'Medical Diagnoses':
        return 'bg-rose-100 text-rose-800';
      case 'Psychological and Social Factors':
        return 'bg-indigo-100 text-indigo-800';
      case 'Patient and Tumor Characteristics':
        return 'bg-purple-100 text-purple-800';
      case 'Presentation Reason':
        return 'bg-orange-100 text-orange-800';
      case 'MDT Recommendation (EXPERIMENTAL - Medical validation required)':
        return 'bg-amber-100 text-amber-800';
      case 'DRAFT System Recommendation':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

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
            <span className={`px-2 py-1 text-xs rounded-full whitespace-nowrap ${getCategoryColor(category)}`}>
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

  const handleViewSource = (filename: string) => {
    setSourceViewerModal({ isOpen: true, filename });
  };

  const handleCloseSourceViewer = () => {
    setSourceViewerModal({ isOpen: false, filename: '' });
  };
  // Get unique categories from config
  const semanticCategories = [...new Set(Object.values(reportGroupingConfig))];
  
  // Helper function to get semantic category for an entity
  const getEntityCategory = (entityName: string): string => {
    return reportGroupingConfig[entityName as keyof typeof reportGroupingConfig] || 'Uncategorized';
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
  const availableCategories = semanticCategories.filter(category => 
    (organizedEntities[category] && organizedEntities[category].length > 0) ||
    (organizedNotFound[category] && organizedNotFound[category].length > 0)
  );
  
  // Add uncategorized if it has entities or not-found entities
  if ((organizedEntities['Uncategorized'] && organizedEntities['Uncategorized'].length > 0) ||
      (organizedNotFound['Uncategorized'] && organizedNotFound['Uncategorized'].length > 0)) {
    availableCategories.push('Uncategorized');
  }

  // Initialize activeTab with first available category
  const [activeTab, setActiveTab] = useState<string>(availableCategories[0] || 'Patient Information');

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

  const getCategoryColor = (category: string, isActive: boolean = false) => {
    switch (category) {
      case 'Patient Information':
        return isActive
          ? 'border-blue-500 text-blue-600 bg-blue-50'
          : 'border-transparent text-gray-500 hover:text-blue-600 hover:border-blue-300';
      case 'Clinical Summary':
        return isActive
          ? 'border-green-500 text-green-600 bg-green-50'
          : 'border-transparent text-gray-500 hover:text-green-600 hover:border-green-300';
      case 'General Health and Functional Status':
        return isActive
          ? 'border-teal-500 text-teal-600 bg-teal-50'
          : 'border-transparent text-gray-500 hover:text-teal-600 hover:border-teal-300';
      case 'Laboratory and Exploration Results':
        return isActive
          ? 'border-cyan-500 text-cyan-600 bg-cyan-50'
          : 'border-transparent text-gray-500 hover:text-cyan-600 hover:border-cyan-300';
      case 'Medical Diagnoses':
        return isActive
          ? 'border-rose-500 text-rose-600 bg-rose-50'
          : 'border-transparent text-gray-500 hover:text-rose-600 hover:border-rose-300';
      case 'Psychological and Social Factors':
        return isActive
          ? 'border-indigo-500 text-indigo-600 bg-indigo-50'
          : 'border-transparent text-gray-500 hover:text-indigo-600 hover:border-indigo-300';
      case 'Patient and Tumor Characteristics':
        return isActive
          ? 'border-purple-500 text-purple-600 bg-purple-50'
          : 'border-transparent text-gray-500 hover:text-purple-600 hover:border-purple-300';
      case 'Presentation Reason':
        return isActive
          ? 'border-orange-500 text-orange-600 bg-orange-50'
          : 'border-transparent text-gray-500 hover:text-orange-600 hover:border-orange-300';
      case 'MDT Recommendation (EXPERIMENTAL - Medical validation required)':
        return isActive
          ? 'border-amber-500 text-amber-600 bg-amber-50'
          : 'border-transparent text-gray-500 hover:text-amber-600 hover:border-amber-300';
      case 'DRAFT System Recommendation':
        return isActive
          ? 'border-red-500 text-red-600 bg-red-50'
          : 'border-transparent text-gray-500 hover:text-red-600 hover:border-red-300';
      default:
        return isActive
          ? 'border-gray-500 text-gray-600 bg-gray-50'
          : 'border-transparent text-gray-500 hover:text-gray-600 hover:border-gray-300';
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
      <div className="max-h-96 overflow-y-auto border-b border-gray-200">
        <ReportDisclaimer 
          reportDate={new Date(report.created_at).toLocaleString()}
          aiModel="AI Large Language Model (AWS Bedrock/Mistral)"
          version="Proof of Concept v1.0"
        />
      </div>

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

      {/* Tabs */}
      <div className="flex border-b border-gray-200 overflow-x-auto">
        {availableCategories.map((category) => {
          const Icon = getCategoryIcon(category);
          const foundCount = organizedEntities[category]?.length || 0;
          const notFoundCount = organizedNotFound[category]?.length || 0;
          const isActive = activeTab === category;
          return (
            <button
              key={category}
              onClick={() => setActiveTab(category)}
              className={`
                flex items-center space-x-2 px-4 py-3 text-sm font-medium border-b-2 transition-all duration-200
                whitespace-nowrap ${getCategoryColor(category, isActive)}
              `}
            >
              <Icon className="w-4 h-4" />
              <span>{category}</span>
              <div className="flex items-center space-x-1">
                <span className={`
                  px-2 py-1 rounded-full text-xs font-medium
                  ${isActive
                    ? 'bg-white text-green-600 shadow-sm'
                    : 'bg-green-100 text-green-600'
                  }
                `}>
                  {foundCount}
                </span>
                {notFoundCount > 0 && (
                  <span className={`
                    px-2 py-1 rounded-full text-xs font-medium
                    ${isActive
                      ? 'bg-white text-orange-600 shadow-sm'
                      : 'bg-orange-100 text-orange-600'
                    }
                  `}>
                    {notFoundCount}
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 scrollbar-thin">
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