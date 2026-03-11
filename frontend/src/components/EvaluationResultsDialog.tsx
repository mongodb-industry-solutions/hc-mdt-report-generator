import React, { useState, useEffect } from 'react';
import { X, CheckCircle, XCircle, AlertTriangle, TrendingUp, Loader2, Download, RefreshCw } from 'lucide-react';
import { apiService } from '../services/api';
import { EvaluationSummary, EvaluationProgress } from '../types';

interface EvaluationResultsDialogProps {
  isOpen: boolean;
  onClose: () => void;
  patientId: string;
  reportUuid: string;
  onReEvaluate?: () => void;
}

interface EvaluationData {
  status: string;
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
}

export default function EvaluationResultsDialog({
  isOpen,
  onClose,
  patientId,
  reportUuid,
  onReEvaluate,
}: EvaluationResultsDialogProps) {
  const [evaluation, setEvaluation] = useState<EvaluationData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState<EvaluationProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'name' | 'llm_score'>('llm_score');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc'); // desc = best first, asc = worst first

  useEffect(() => {
    if (isOpen) {
      loadEvaluation();
    }
  }, [isOpen, patientId, reportUuid]);

  const loadEvaluation = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiService.getEvaluation(patientId, reportUuid);
      setEvaluation(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load evaluation');
    } finally {
      setIsLoading(false);
    }
  };

  const runEvaluation = async () => {
    setIsRunning(true);
    setProgress(null);
    setError(null);

    try {
      // LLM provider is determined by backend from LLM_PROVIDER env var
      await apiService.runEvaluation(patientId, reportUuid, (data) => {
        setProgress(data);
        if (data.status === 'FAILED') {
          setError(data.message);
        }
      });
      // Reload evaluation data after completion
      await loadEvaluation();
    } catch (err: any) {
      setError(err.message || 'Evaluation failed');
    } finally {
      setIsRunning(false);
      setProgress(null);
    }
  };

  if (!isOpen) return null;

  const sortedDetails = evaluation?.details
    ? [...evaluation.details].sort((a, b) => {
        if (sortBy === 'name') {
          const nameComparison = a.entity_name.localeCompare(b.entity_name);
          return sortDirection === 'asc' ? nameComparison : -nameComparison;
        }
        // Score sorting
        const scoreComparison = a.llm_score - b.llm_score;
        return sortDirection === 'asc' ? scoreComparison : -scoreComparison;
      })
    : [];

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.5) return 'text-amber-600';
    return 'text-red-600';
  };

  const getScoreBg = (score: number) => {
    if (score >= 0.8) return 'bg-green-100';
    if (score >= 0.5) return 'bg-amber-100';
    return 'bg-red-100';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-5xl mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b shrink-0">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">
              Evaluation Results
            </h2>
            {evaluation?.evaluated_at && (
              <p className="text-sm text-gray-500 mt-1">
                Evaluated: {new Date(evaluation.evaluated_at).toLocaleString()}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-navy-700 animate-spin" />
            </div>
          ) : error ? (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          ) : evaluation?.status === 'not_evaluated' ? (
            <div className="text-center py-12">
              <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Not Evaluated Yet
              </h3>
              <p className="text-gray-500 mb-6">
                Run evaluation to compare generated entities against ground truth.
              </p>
              <button
                onClick={runEvaluation}
                disabled={isRunning}
                className="px-6 py-3 bg-navy-700 text-white rounded-lg hover:bg-navy-800 disabled:opacity-50"
              >
                {isRunning ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Running...
                  </span>
                ) : (
                  'Run Evaluation'
                )}
              </button>
              {progress && (
                <div className="mt-4">
                  <div className="w-64 mx-auto bg-gray-200 rounded-full h-2">
                    <div
                      className="h-2 rounded-full bg-navy-700 transition-all"
                      style={{ width: `${progress.progress}%` }}
                    />
                  </div>
                  <p className="text-sm text-gray-500 mt-2">{progress.message}</p>
                </div>
              )}
            </div>
          ) : evaluation?.summary ? (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-4 gap-4 mb-6">
                {/* F1 Score */}
                <div className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl border border-blue-200">
                  <div className="text-sm text-blue-600 font-medium mb-1">F1 Score</div>
                  <div className="text-3xl font-bold text-blue-700">
                    {(evaluation.summary.exact_match.f1 * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-blue-500 mt-1">
                    P: {(evaluation.summary.exact_match.precision * 100).toFixed(0)}% | 
                    R: {(evaluation.summary.exact_match.recall * 100).toFixed(0)}%
                  </div>
                </div>

                {/* LLM Semantic Score */}
                <div className="p-4 bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl border border-purple-200">
                  <div className="text-sm text-purple-600 font-medium mb-1">LLM Score</div>
                  <div className="text-3xl font-bold text-purple-700">
                    {(evaluation.summary.llm_semantic_score * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-purple-500 mt-1">Semantic similarity</div>
                </div>

                {/* OOV Rate */}
                <div className="p-4 bg-gradient-to-br from-amber-50 to-amber-100 rounded-xl border border-amber-200">
                  <div className="text-sm text-amber-600 font-medium mb-1">OOV Rate</div>
                  <div className="text-3xl font-bold text-amber-700">
                    {(evaluation.summary.oov_rate * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-amber-500 mt-1">Out-of-vocabulary</div>
                </div>

                {/* Matched Count */}
                <div className="p-4 bg-gradient-to-br from-green-50 to-green-100 rounded-xl border border-green-200">
                  <div className="text-sm text-green-600 font-medium mb-1">Matched</div>
                  <div className="text-3xl font-bold text-green-700">
                    {evaluation.summary.matched_count}/{evaluation.summary.entity_count}
                  </div>
                  <div className="text-xs text-green-500 mt-1">
                    Missing: {evaluation.summary.missing_count} | Extra: {evaluation.summary.extra_count}
                  </div>
                </div>
              </div>

              {/* Worst Entities */}
              {evaluation.worst_entities && evaluation.worst_entities.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-sm font-medium text-gray-700 mb-3">
                    Worst Performing Entities
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {evaluation.worst_entities.map((entity) => (
                      <span
                        key={entity.name}
                        className="px-3 py-1 bg-red-50 border border-red-200 text-red-700 rounded-full text-sm"
                      >
                        {entity.name}: {(entity.f1 * 100).toFixed(0)}%
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Detail Table */}
              <div className="border rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-4 py-3 flex items-center justify-between">
                  <h3 className="text-sm font-medium text-gray-700">
                    Per-Entity Breakdown
                  </h3>
                  <div className="flex items-center space-x-3">
                    <select
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value as 'name' | 'llm_score')}
                      className="text-sm border-gray-300 rounded-lg"
                    >
                      <option value="llm_score">Sort by Score</option>
                      <option value="name">Sort by Name</option>
                    </select>
                    <select
                      value={sortDirection}
                      onChange={(e) => setSortDirection(e.target.value as 'asc' | 'desc')}
                      className="text-sm border-gray-300 rounded-lg"
                    >
                      {sortBy === 'llm_score' ? (
                        <>
                          <option value="desc">Highest to Lowest</option>
                          <option value="asc">Lowest to Highest</option>
                        </>
                      ) : (
                        <>
                          <option value="asc">A to Z</option>
                          <option value="desc">Z to A</option>
                        </>
                      )}
                    </select>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-y">
                      <tr>
                        <th className="px-4 py-2 text-left font-medium text-gray-600">Entity</th>
                        <th className="px-4 py-2 text-left font-medium text-gray-600">Ground Truth</th>
                        <th className="px-4 py-2 text-left font-medium text-gray-600">Predicted Value</th>
                        <th className="px-4 py-2 text-center font-medium text-gray-600">Match</th>
                        <th className="px-4 py-2 text-center font-medium text-gray-600">LLM Score</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {sortedDetails.map((detail) => (
                        <tr key={detail.entity_name} className="hover:bg-gray-50">
                          <td className="px-4 py-3 font-medium text-gray-900 whitespace-nowrap">
                            {detail.entity_name}
                          </td>
                          <td className="px-4 py-3 text-gray-600 max-w-md">
                            {detail.gold_value ? (
                              <div className="break-words text-sm leading-relaxed">
                                {detail.gold_value}
                              </div>
                            ) : (
                              <span className="text-gray-400 italic">empty</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-gray-600 max-w-md">
                            {detail.pred_value ? (
                              <div className="break-words text-sm leading-relaxed">
                                {detail.pred_value}
                              </div>
                            ) : (
                              <span className="text-gray-400 italic">not found</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-center">
                            {detail.llm_score >= 0.8 ? (
                              <CheckCircle className="w-5 h-5 text-green-500 inline" />
                            ) : detail.llm_score >= 0.5 ? (
                              <TrendingUp className="w-5 h-5 text-orange-500 inline" />
                            ) : (
                              <XCircle className="w-5 h-5 text-red-400 inline" />
                            )}
                          </td>
                          <td className="px-4 py-3 text-center whitespace-nowrap">
                            <span
                              className={`px-2 py-1 rounded-full text-xs font-medium ${getScoreBg(detail.llm_score)} ${getScoreColor(detail.llm_score)}`}
                            >
                              {(detail.llm_score * 100).toFixed(0)}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t bg-gray-50 rounded-b-xl shrink-0">
          <div className="text-sm text-gray-500">
            {evaluation?.ground_truth_info && (
              <span>
                GT: {evaluation.ground_truth_info.entity_count} entities ({evaluation.ground_truth_info.ocr_engine})
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            {evaluation?.status === 'COMPLETED' && (
              <button
                onClick={runEvaluation}
                disabled={isRunning}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${isRunning ? 'animate-spin' : ''}`} />
                Re-evaluate
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-white bg-navy-700 rounded-lg hover:bg-navy-800"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

