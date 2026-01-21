import React, { useEffect, useMemo, useRef, useState } from 'react';
import { User, Users, Search } from 'lucide-react';
import { apiService } from '../services/api';

interface PatientSelectorProps {
  patientId: string;
  onPatientIdChange: (patientId: string) => void;
  onOpenPatients?: () => void;
}

export default function PatientSelector({ patientId, onPatientIdChange, onOpenPatients }: PatientSelectorProps) {
  const [patients, setPatients] = useState<string[]>([]);
  const [openSuggestions, setOpenSuggestions] = useState(false);
  const [query, setQuery] = useState('');
  const [highlighted, setHighlighted] = useState<number>(-1);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let mounted = true;
    apiService.getPatients().then(res => {
      if (mounted) setPatients(res.items || []);
    }).catch(() => {});
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(e.target as Node)) {
        setOpenSuggestions(false);
        setHighlighted(-1);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  useEffect(() => {
    setQuery(patientId || '');
  }, [patientId]);

  const filtered = useMemo(() => {
    if (!query) return patients.slice(0, 8);
    const q = query.toLowerCase();
    return patients.filter(p => p.toLowerCase().includes(q)).slice(0, 8);
  }, [patients, query]);

  const commitSelection = (pid: string) => {
    onPatientIdChange(pid);
    setQuery(pid);
    setOpenSuggestions(false);
    setHighlighted(-1);
  };

  return (
    <div className="relative" ref={containerRef}>
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2">
          <User className="w-4 h-4 text-gray-500" />
          <label htmlFor="patientId" className="text-sm font-medium text-gray-700">
            Patient ID:
          </label>
        </div>
        <div className="relative">
          <div className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-gray-400">
            <Search className="w-4 h-4" />
          </div>
          <input
            id="patientId"
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); onPatientIdChange(e.target.value); setOpenSuggestions(true); setHighlighted(-1); }}
            onFocus={() => setOpenSuggestions(true)}
            onKeyDown={(e) => {
              if (!openSuggestions && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
                setOpenSuggestions(true);
                return;
              }
              if (e.key === 'ArrowDown') {
                e.preventDefault();
                setHighlighted((prev) => Math.min(prev + 1, filtered.length));
              } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setHighlighted((prev) => Math.max(prev - 1, -1));
              } else if (e.key === 'Enter') {
                if (highlighted >= 0 && highlighted < filtered.length) {
                  commitSelection(filtered[highlighted]);
                } else if (highlighted === filtered.length) {
                  onOpenPatients && onOpenPatients();
                  setOpenSuggestions(false);
                }
              } else if (e.key === 'Escape') {
                setOpenSuggestions(false);
                setHighlighted(-1);
              }
            }}
            className="input-field w-56 pl-7"
            placeholder="Enter patient ID"
            name="patient-id"
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="none"
            spellCheck={false}
            aria-autocomplete="list"
            aria-expanded={openSuggestions}
          />
          {openSuggestions && (
            <div className="absolute z-50 mt-1 w-full bg-white border border-gray-200 rounded-md shadow-lg">
              {filtered.length === 0 ? (
                <div className="px-3 py-2 text-sm text-gray-500">No matches</div>
              ) : (
                <ul className="max-h-64 overflow-auto py-1">
                  {filtered.map((pid, idx) => (
                    <li key={pid}>
                      <button
                        className={`w-full text-left px-3 py-2 text-sm ${idx === highlighted ? 'bg-medical-50 text-medical-700' : 'hover:bg-gray-50 text-gray-700'}`}
                        onMouseEnter={() => setHighlighted(idx)}
                        onMouseLeave={() => setHighlighted(-1)}
                        onClick={() => commitSelection(pid)}
                      >
                        {pid}
                      </button>
                    </li>
                  ))}
                  {onOpenPatients && (
                    <li>
                      <button
                        className={`w-full text-left px-3 py-2 text-sm ${highlighted === filtered.length ? 'bg-medical-50 text-medical-700' : 'hover:bg-gray-50 text-gray-700'}`}
                        onMouseEnter={() => setHighlighted(filtered.length)}
                        onMouseLeave={() => setHighlighted(-1)}
                        onClick={() => { onOpenPatients(); setOpenSuggestions(false); }}
                      >
                        View all patients…
                      </button>
                    </li>
                  )}
                </ul>
              )}
            </div>
          )}
        </div>
        <button
          type="button"
          className="inline-flex items-center justify-center w-8 h-8 rounded-md border border-medical-200 bg-medical-50 text-medical-700 hover:bg-medical-100"
          onClick={onOpenPatients}
          title="Browse all patients"
        >
          <Users className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}