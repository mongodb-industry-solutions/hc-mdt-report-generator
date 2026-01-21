import React, { useState, useEffect } from 'react';
import { X, Save, Edit2, Check, AlertTriangle, FileText, Loader2 } from 'lucide-react';
import { apiService } from '../services/api';
import { GroundTruthEntity } from '../types';

interface GTVerifyDialogProps {
  isOpen: boolean;
  onClose: () => void;
  patientId: string;
  reportUuid: string;
  initialEntities: GroundTruthEntity[];
  onSave: () => void;
  onRunEvaluation: () => void;
}

export default function GTVerifyDialog({
  isOpen,
  onClose,
  patientId,
  reportUuid,
  initialEntities,
  onSave,
  onRunEvaluation,
}: GTVerifyDialogProps) {
  const [entities, setEntities] = useState<GroundTruthEntity[]>([]);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editValue, setEditValue] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && initialEntities) {
      setEntities([...initialEntities]);
      setHasChanges(false);
    }
  }, [isOpen, initialEntities]);

  if (!isOpen) return null;

  const handleEdit = (index: number) => {
    setEditingIndex(index);
    setEditValue(entities[index].value || '');
  };

  const handleSaveEdit = (index: number) => {
    const updated = [...entities];
    updated[index] = {
      ...updated[index],
      value: editValue.trim() || null,
      source: 'manual',
      confidence: 1.0,
    };
    setEntities(updated);
    setEditingIndex(null);
    setHasChanges(true);
  };

  const handleCancelEdit = () => {
    setEditingIndex(null);
    setEditValue('');
  };

  const handleSaveAll = async () => {
    setIsSaving(true);
    setError(null);

    try {
      await apiService.updateGroundTruthEntities(
        patientId,
        reportUuid,
        entities.map((e) => ({ entity_name: e.entity_name, value: e.value }))
      );
      setHasChanges(false);
      onSave();
    } catch (err: any) {
      setError(err.message || 'Failed to save changes');
    } finally {
      setIsSaving(false);
    }
  };

  const handleRunEvaluation = async () => {
    if (hasChanges) {
      await handleSaveAll();
    }
    onRunEvaluation();
  };

  const foundEntities = entities.filter((e) => e.value);
  const missingEntities = entities.filter((e) => !e.value);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b shrink-0">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              Verify Ground Truth Entities
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              Review and edit extracted values before evaluation
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {/* Summary */}
          <div className="flex gap-4 mb-6">
            <div className="flex-1 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center gap-2">
                <Check className="w-5 h-5 text-green-600" />
                <span className="text-sm font-medium text-green-800">
                  {foundEntities.length} entities extracted
                </span>
              </div>
            </div>
            {missingEntities.length > 0 && (
              <div className="flex-1 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-600" />
                  <span className="text-sm font-medium text-amber-800">
                    {missingEntities.length} entities not found
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Entity List */}
          <div className="space-y-3">
            {entities.map((entity, index) => (
              <div
                key={entity.entity_name}
                className={`p-4 rounded-lg border ${
                  entity.value
                    ? 'bg-white border-gray-200'
                    : 'bg-amber-50 border-amber-200'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-gray-900">
                        {entity.entity_name}
                      </span>
                      {entity.source === 'manual' && (
                        <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">
                          edited
                        </span>
                      )}
                      {!entity.value && (
                        <span className="px-2 py-0.5 text-xs bg-amber-100 text-amber-700 rounded">
                          not found
                        </span>
                      )}
                    </div>

                    {editingIndex === index ? (
                      <div className="flex items-center gap-2 mt-2">
                        <input
                          type="text"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          placeholder="Enter value..."
                          className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-medical-500 focus:border-medical-500"
                          autoFocus
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSaveEdit(index);
                            if (e.key === 'Escape') handleCancelEdit();
                          }}
                        />
                        <button
                          onClick={() => handleSaveEdit(index)}
                          className="p-2 text-green-600 hover:bg-green-50 rounded-lg"
                          title="Save"
                        >
                          <Check className="w-4 h-4" />
                        </button>
                        <button
                          onClick={handleCancelEdit}
                          className="p-2 text-gray-400 hover:bg-gray-50 rounded-lg"
                          title="Cancel"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <p className="text-sm text-gray-600">
                        {entity.value || (
                          <span className="italic text-gray-400">
                            No value - click edit to add
                          </span>
                        )}
                      </p>
                    )}
                  </div>

                  {editingIndex !== index && (
                    <button
                      onClick={() => handleEdit(index)}
                      className="p-2 text-gray-400 hover:text-medical-600 hover:bg-medical-50 rounded-lg"
                      title="Edit"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Error */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t bg-gray-50 rounded-b-xl shrink-0">
          <div className="text-sm text-gray-500">
            {hasChanges && (
              <span className="text-amber-600 font-medium">
                ● Unsaved changes
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
            >
              Cancel
            </button>
            {hasChanges && (
              <button
                onClick={handleSaveAll}
                disabled={isSaving}
                className="px-4 py-2 text-sm font-medium text-white bg-gray-600 rounded-lg hover:bg-gray-700 disabled:opacity-50 flex items-center gap-2"
              >
                {isSaving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                Save Changes
              </button>
            )}
            <button
              onClick={handleRunEvaluation}
              disabled={isSaving}
              className="px-4 py-2 text-sm font-medium text-white bg-medical-600 rounded-lg hover:bg-medical-700 disabled:opacity-50 flex items-center gap-2"
            >
              Run Evaluation →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}


