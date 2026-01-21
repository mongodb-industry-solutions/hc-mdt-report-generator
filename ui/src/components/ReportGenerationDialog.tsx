import React, { useState, Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { X, Settings } from 'lucide-react';

interface ReportGenerationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onGenerate: (settings: ReportGenerationSettings) => void;
  isGenerating: boolean;
  patientId: string;
}

export interface ReportGenerationSettings {
  customTitle?: string;
  selectedFiles?: string[];
  autoRetrieveFiles?: boolean;
  nerConfig?: {
    maxEntitiesPerBatch: number;
    maxContentSize: number;
    chunkOverlapping: number;
  };
}

export default function ReportGenerationDialog({
  isOpen,
  onClose,
  onGenerate,
  isGenerating,
  patientId
}: ReportGenerationDialogProps) {
  const buildDefaultTitle = () => {
    try {
      const d = new Date();
      const yyyy = d.getFullYear();
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      const hh = String(d.getHours()).padStart(2, '0');
      const mi = String(d.getMinutes()).padStart(2, '0');
      return `${patientId} - ${yyyy}-${mm}-${dd} ${hh}:${mi}`;
    } catch {
      return `${patientId}`;
    }
  };
  const [customTitle, setCustomTitle] = useState(buildDefaultTitle());
  const [autoRetrieveFiles, setAutoRetrieveFiles] = useState(true);
  const [includeAllFiles, setIncludeAllFiles] = useState(true);
  
  // NER Configuration settings (defaults)
  const [maxEntitiesPerBatch, setMaxEntitiesPerBatch] = useState(10);
  const [maxContentSize, setMaxContentSize] = useState(30000);
  const [chunkOverlapping, setChunkOverlapping] = useState(20);

  const handleGenerate = () => {
    const settings: ReportGenerationSettings = {
      customTitle: customTitle.trim() || undefined,
      autoRetrieveFiles,
      selectedFiles: includeAllFiles ? undefined : [], // Will be implemented later
      nerConfig: {
        maxEntitiesPerBatch,
        maxContentSize,
        chunkOverlapping
      }
    };
    onGenerate(settings);
    handleClose();
  };

  const handleClose = () => {
    if (!isGenerating) {
      setCustomTitle(buildDefaultTitle());
      setAutoRetrieveFiles(true);
      setIncludeAllFiles(true);
      // Reset NER config to defaults
      setMaxEntitiesPerBatch(10);
      setMaxContentSize(30000);
      setChunkOverlapping(20);
      onClose();
    }
  };

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={handleClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-3xl transform overflow-hidden rounded-xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-medical-100 rounded-lg flex items-center justify-center">
                      <Settings className="w-5 h-5 text-medical-600" />
                    </div>
                    <div>
                      <Dialog.Title className="text-lg font-semibold text-gray-900">
                        Generate MDT Report
                      </Dialog.Title>
                      <p className="text-sm text-gray-500">Patient ID: {patientId}</p>
                    </div>
                  </div>
                  <button
                    onClick={handleClose}
                    disabled={isGenerating}
                    className="text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* Content */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* LEFT COLUMN: Report Title */}
                  <div className="space-y-6">
                    {/* Report Title */}
                    <div>
                      <label htmlFor="customTitle" className="block text-sm font-medium text-gray-700 mb-2">
                        Report Title (Optional)
                      </label>
                      <input
                        id="customTitle"
                        type="text"
                        value={customTitle}
                        onChange={(e) => setCustomTitle(e.target.value)}
                        placeholder="Enter custom report title..."
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-medical-500 focus:border-medical-500 transition-colors"
                        disabled={isGenerating}
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Leave empty to use auto-generated title
                      </p>
                    </div>
                  </div>

                  {/* RIGHT COLUMN: Advanced NER Configuration */}
                  <div className="border-t pt-4 mt-4 md:border-t-0 md:pt-0">
                    <h3 className="text-sm font-medium text-gray-800 mb-3">Advanced NER Configuration</h3>
                    
                    {/* Max Entities Per Batch (Extraction) */}
                    <div className="mb-3">
                      <label htmlFor="maxEntitiesPerBatch" className="block text-xs font-medium text-gray-700 mb-1">
                        Max Entities Per Batch (Extraction)
                      </label>
                      <div className="flex items-center">
                        <input
                          id="maxEntitiesPerBatch"
                          type="range"
                          min="1"
                          max="30"
                          value={maxEntitiesPerBatch}
                          onChange={(e) => setMaxEntitiesPerBatch(parseInt(e.target.value))}
                          className="w-full mr-2"
                          disabled={isGenerating}
                        />
                        <span className="text-sm font-medium w-6 text-center">{maxEntitiesPerBatch}</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Number of entities processed in each batch</p>
                    </div>
                    
                    {/* Max Content Size */}
                    <div className="mb-3">
                      <label htmlFor="maxContentSize" className="block text-xs font-medium text-gray-700 mb-1">
                        Max Content Size
                      </label>
                      <div className="flex items-center">
                        <input
                          id="maxContentSize"
                          type="range"
                          min="5000"
                          max="200000"
                          step="5000"
                          value={maxContentSize}
                          onChange={(e) => setMaxContentSize(parseInt(e.target.value))}
                          className="w-full mr-2"
                          disabled={isGenerating}
                        />
                        <span className="text-sm font-medium w-16 text-center">{maxContentSize.toLocaleString()}</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Maximum size of content chunks in characters (larger = fewer batches)</p>
                    </div>
                    
                    {/* Chunk Overlapping */}
                    <div>
                      <label htmlFor="chunkOverlapping" className="block text-xs font-medium text-gray-700 mb-1">
                        Chunk Overlapping
                      </label>
                      <div className="flex items-center">
                        <input
                          id="chunkOverlapping"
                          type="range"
                          min="0"
                          max="100"
                          step="5"
                          value={chunkOverlapping}
                          onChange={(e) => setChunkOverlapping(parseInt(e.target.value))}
                          className="w-full mr-2"
                          disabled={isGenerating}
                        />
                        <span className="text-sm font-medium w-12 text-center">{chunkOverlapping}</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Overlap between chunks in characters</p>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-end space-x-3 mt-8">
                  <button
                    onClick={handleClose}
                    disabled={isGenerating}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleGenerate}
                    disabled={isGenerating}
                    className="px-6 py-2 text-sm font-medium text-white bg-medical-600 border border-transparent rounded-lg hover:bg-medical-700 disabled:opacity-50 transition-colors"
                  >
                    Generate Report
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}