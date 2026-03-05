import React, { useEffect, useMemo, useState } from 'react';
import { apiService } from '../services/api';
import { Calendar, Hash, Cpu, RefreshCw, BarChart3, Loader2, User } from 'lucide-react';
import { GroundTruthEntity } from '../types';
import { useI18n } from '../i18n/context';

type GenerationItem = {
  uuid: string;
  timestamp_utc: string;
  patient_id: string;
  model_llm: string;
  max_entities_per_batch: number;
  aggregation_batch_size: number;
  max_content_size: number;
  chunk_overlapping: number;
  max_concurrent_requests: number;
  report_title?: string | null;
  filenames_hash: string;
  elapsed_seconds: number;
  found_entities: number;
  status: string;
  error?: string | null;
  evaluation_status?: string | null;
  evaluation_summary?: { macro_accuracy?: number; macro_precision?: number; macro_recall?: number; macro_f1?: number; llm_score?: number } | null;
  report?: { uuid: string; [key: string]: any } | null; // The embedded report with its UUID
  gt_status?: string | null; // Ground truth upload status: 'COMPLETED' if GT exists
};

function formatDate(dt: string) {
  try {
    return new Date(dt).toLocaleString();
  } catch {
    return dt;
  }
}

function formatElapsed(seconds: number) {
  const s = Math.floor(seconds % 60);
  const m = Math.floor((seconds / 60) % 60);
  const h = Math.floor(seconds / 3600);
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

interface ObservabilityProps {
  patientId?: string;
  onShowGTUpload?: (generationItem: GenerationItem) => void;
  onShowGTVerify?: (generationItem: GenerationItem, entities: GroundTruthEntity[]) => void;
  onShowEvalResults?: (generationItem: GenerationItem) => void;
}

export default function Observability({ 
  patientId, 
  onShowGTUpload, 
  onShowGTVerify, 
  onShowEvalResults 
}: ObservabilityProps) {
  const { t } = useI18n();
  const [items, setItems] = useState<GenerationItem[]>([]);
  const [llms, setLlms] = useState<string[]>([]);
  const [hashes, setHashes] = useState<string[]>([]);
  const [selectedLLM, setSelectedLLM] = useState<string>('');
  const [selectedHash, setSelectedHash] = useState<string>('');
  const [start, setStart] = useState<string>('');
  const [end, setEnd] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  // Evaluation flow state - only keep what's needed for progress tracking
  const [isEvaluating, setIsEvaluating] = useState(false);

  useEffect(() => {
    loadFilters();
    // Initialize date range to last 7 days
    const now = new Date();
    const past = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    setStart(past.toISOString());
    setEnd(now.toISOString());
  }, []);

  useEffect(() => {
    fetchData();
  }, [selectedLLM, selectedHash, start, end, patientId]);

  const loadFilters = async () => {
    try {
      const data = await apiService.getGenerationsFilters();
      setLlms((data.llms || []).sort());
      setHashes((data.hashes || []).sort());
    } catch (e) {
      console.error('Failed to load filters', e);
    }
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (start) params.start = start;
      if (end) params.end = end;
      if (selectedLLM) params.model_llm = selectedLLM;
      if (selectedHash) params.filenames_hash = selectedHash;
      if (patientId) params.patient_id = patientId;
      const { items } = await apiService.getGenerations(params);
      setItems(items as GenerationItem[]);
    } catch (e) {
      console.error('Failed to load generations', e);
    } finally {
      setLoading(false);
    }
  };

  // Helper to get the report UUID from a generation
  const getReportUuid = (generation: GenerationItem): string | null => {
    return generation.report?.uuid || null;
  };

  // Evaluation handlers
  const handleStartEvaluation = async (generation: GenerationItem) => {
    const reportUuid = getReportUuid(generation);
    if (!reportUuid) {
      alert('Report UUID not found in this generation record');
      return;
    }
    
    // Route based on what data already exists
    if (generation.evaluation_status === 'COMPLETED') {
      // Evaluation exists → Show results directly
      onShowEvalResults?.(generation);
    } else if (generation.gt_status === 'COMPLETED') {
      // GT exists but no evaluation → Fetch GT entities and show verify dialog
      try {
        const gtData = await apiService.getGroundTruth(generation.patient_id, reportUuid);
        if (gtData.status === 'found' && gtData.ground_truth?.entities) {
          onShowGTVerify?.(generation, gtData.ground_truth.entities);
        } else {
          // GT not found (shouldn't happen), show upload
          onShowGTUpload?.(generation);
        }
      } catch (e) {
        console.error('Failed to fetch existing GT:', e);
        // Fallback to upload
        onShowGTUpload?.(generation);
      }
    } else {
      // No GT → Show upload dialog
      onShowGTUpload?.(generation);
    }
  };

  const distinctLLMs = useMemo(() => llms, [llms]);
  const distinctHashes = useMemo(() => hashes, [hashes]);

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">{t.observability.title}</h2>
        <div className="flex items-center gap-3">
          {patientId && (
            <div className="inline-flex items-center px-3 py-1 rounded-full bg-blue-100 text-blue-800 text-sm font-medium">
              <User className="w-4 h-4 mr-1.5" />
              Patient: {patientId}
            </div>
          )}
          <button
            onClick={fetchData}
            className="inline-flex items-center px-3 py-2 text-sm rounded-lg bg-gray-100 hover:bg-gray-200"
          >
            <RefreshCw className="w-4 h-4 mr-2" /> {t.observability.refresh}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
        <div className="space-y-1">
          <label className="text-xs text-gray-500">{t.observability.filters.startTime}</label>
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-500" />
            <input
              type="datetime-local"
              value={start ? new Date(start).toISOString().slice(0,16) : ''}
              onChange={(e) => {
                const val = e.target.value;
                setStart(val ? new Date(val).toISOString() : '');
              }}
              className="input"
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs text-gray-500">{t.observability.filters.endTime}</label>
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-500" />
            <input
              type="datetime-local"
              value={end ? new Date(end).toISOString().slice(0,16) : ''}
              onChange={(e) => {
                const val = e.target.value;
                setEnd(val ? new Date(val).toISOString() : '');
              }}
              className="input"
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs text-gray-500">{t.observability.filters.llm}</label>
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-gray-500" />
            <select
              className="input"
              value={selectedLLM}
              onChange={(e) => setSelectedLLM(e.target.value)}
            >
              <option value="">{t.observability.filters.all}</option>
              {distinctLLMs.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs text-gray-500">{t.observability.filters.docsHash}</label>
          <div className="flex items-center gap-2">
            <Hash className="w-4 h-4 text-gray-500" />
            <select
              className="input"
              value={selectedHash}
              onChange={(e) => setSelectedHash(e.target.value)}
            >
              <option value="">All</option>
              {distinctHashes.map((h) => (
                <option key={h} value={h}>{h}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-auto rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{t.observability.table.timeUtc}</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{t.observability.table.patientId}</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{t.observability.table.llm}</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{t.observability.table.foundEntities}</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{t.observability.table.elapsed}</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{t.observability.table.docsHash}</th>
              <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 uppercase">{t.observability.table.entitiesPerBatch}</th>
              <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 uppercase">{t.observability.table.aggBatch}</th>
              <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 uppercase">{t.observability.table.maxSize}</th>
              <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 uppercase">{t.observability.table.accuracy}</th>
              <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">{t.observability.table.evaluate}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {loading ? (
              <tr>
                <td colSpan={11} className="px-4 py-8 text-center text-gray-500">{t.observability.table.loading}</td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={11} className="px-4 py-8 text-center text-gray-500">{t.observability.table.noData}</td>
              </tr>
            ) : (
              items.map((g) => (
                <tr key={g.uuid} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm text-gray-700">{formatDate(g.timestamp_utc)}</td>
                  <td className="px-4 py-2 text-sm font-mono text-gray-700">{g.patient_id}</td>
                  <td className="px-4 py-2 text-sm text-gray-700">{g.model_llm}</td>
                  <td className="px-4 py-2 text-sm text-gray-700">{g.found_entities}</td>
                  <td className="px-4 py-2 text-sm text-gray-700">{formatElapsed(g.elapsed_seconds)}</td>
                  <td className="px-4 py-2 text-xs font-mono text-gray-600">{g.filenames_hash.slice(0, 10)}…</td>
                  <td className="px-2 py-2 text-sm text-gray-700">{g.max_entities_per_batch}</td>
                  <td className="px-2 py-2 text-sm text-gray-700">{g.aggregation_batch_size}</td>
                  <td className="px-2 py-2 text-sm text-gray-700">{g.max_content_size}</td>
                  <td className="px-2 py-2 text-sm text-gray-700">{g.evaluation_summary?.macro_accuracy?.toFixed(2) ?? '-'}</td>
                  <td className="px-3 py-2 text-center">
                    <button
                      onClick={() => handleStartEvaluation(g)}
                      className={`inline-flex items-center px-2 py-1 text-xs rounded-md transition-colors ${
                        g.evaluation_status === 'COMPLETED'
                          ? 'bg-green-100 hover:bg-green-200 text-green-800'
                          : g.gt_status === 'COMPLETED'
                          ? 'bg-amber-100 hover:bg-amber-200 text-amber-800'
                          : 'bg-blue-100 hover:bg-blue-200 text-blue-800'
                      }`}
                      title={
                        g.evaluation_status === 'COMPLETED'
                          ? t.observability.evaluation.viewResults
                          : g.gt_status === 'COMPLETED'
                          ? t.observability.evaluation.runEvaluationExisting
                          : t.observability.evaluation.uploadGroundTruthEvaluate
                      }
                    >
                      <BarChart3 className="w-3 h-3 mr-1" />
                      {g.evaluation_status === 'COMPLETED'
                        ? t.observability.evaluation.view
                        : g.gt_status === 'COMPLETED'
                        ? t.observability.evaluation.evaluate
                        : t.observability.evaluation.uploadGT}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Evaluation Progress Overlay */}
      {isEvaluating && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 text-white">
          <div className="text-center">
            <Loader2 className="w-12 h-12 animate-spin mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">{t.observability.evaluation.runningTitle}</h3>
            <p className="text-lg">{t.observability.evaluation.runningDescription}</p>
          </div>
        </div>
      )}
    </div>
  );
}
