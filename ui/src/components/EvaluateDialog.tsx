import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';
import { Loader2 } from 'lucide-react';

type PendingItem = { uuid: string; timestamp_utc: string; model_llm: string; filenames_hash: string; patient_id: string };

export default function EvaluateDialog({ isOpen, onClose, onCompleted, currentModel }: { isOpen: boolean; onClose: () => void; onCompleted: () => void; currentModel: string; }) {
  const [pending, setPending] = useState<PendingItem[]>([]);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadPending();
      setProgress(null);
      setError(null);
    }
  }, [isOpen]);

  const loadPending = async () => {
    try {
      const data = await apiService.getPendingEvaluations();
      setPending(data.items);
    } catch (e: any) {
      setError(e?.message || 'Failed to load pending evaluations');
    }
  };

  const start = async () => {
    setRunning(true);
    setError(null);
    try {
      await apiService.runEvaluationsWithProgress((data) => {
        if (data.status === 'PROGRESS') {
          setProgress({ done: data.done || 0, total: data.total || 0 });
        }
        if (data.status === 'COMPLETED') {
          setProgress((prev) => prev ? { done: prev.total, total: prev.total } : null);
          setRunning(false);
          onCompleted();
        }
        if (data.status === 'FAILED') {
          setError(data.message || 'Evaluation failed');
          setRunning(false);
        }
      });
    } catch (e: any) {
      setError(e?.message || 'Evaluation failed');
      setRunning(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Evaluate Generations</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
        </div>

        <div className="mb-4 text-sm text-gray-600">
          <div>Model: <span className="font-mono font-medium">{currentModel}</span></div>
        </div>

        <div className="mb-4 max-h-56 overflow-auto border rounded">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Patient ID</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">LLM</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Docs Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {pending.length === 0 ? (
                <tr><td colSpan={4} className="px-3 py-4 text-center text-gray-500">No pending generations</td></tr>
              ) : (
                pending.map((p) => (
                  <tr key={p.uuid}>
                    <td className="px-3 py-2 text-sm">{new Date(p.timestamp_utc).toLocaleString()}</td>
                    <td className="px-3 py-2 text-sm font-mono">{p.patient_id}</td>
                    <td className="px-3 py-2 text-sm">{p.model_llm}</td>
                    <td className="px-3 py-2 text-xs font-mono">{p.filenames_hash.slice(0,10)}…</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {progress && (
          <div className="mb-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-navy-700 h-2 rounded-full" style={{ width: `${progress.total ? Math.round((progress.done / progress.total) * 100) : 0}%` }}></div>
            </div>
            <div className="mt-1 text-xs text-gray-600">
              {progress.done}/{progress.total} evaluated
            </div>
          </div>
        )}

        {error && (
          <div className="mb-3 text-sm text-red-600">{error}</div>
        )}

        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="btn-secondary">Close</button>
          <button onClick={start} disabled={running || pending.length === 0} className="btn-primary inline-flex items-center">
            {running && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            {running ? 'Evaluating…' : 'Start'}
          </button>
        </div>
      </div>
    </div>
  );
}


