import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
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
  const [dropdownPosition, setDropdownPosition] = useState<{ top: number; left: number; width: number } | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    let mounted = true;
    apiService.getPatients().then(res => {
      if (mounted) setPatients(res.items || []);
    }).catch(() => {});
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (!containerRef.current || !inputRef.current) return;
      
      // Check if click is outside the input AND the dropdown
      const clickedOutsideInput = !containerRef.current.contains(target);
      const dropdownElement = document.querySelector('[data-patient-dropdown]');
      const clickedOutsideDropdown = !dropdownElement || !dropdownElement.contains(target);
      
      if (clickedOutsideInput && clickedOutsideDropdown) {
        setOpenSuggestions(false);
        setHighlighted(-1);
        setDropdownPosition(null);
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
    setDropdownPosition(null);
  };

  const updateDropdownPosition = () => {
    if (inputRef.current) {
      const rect = inputRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.bottom + window.scrollY + 4,
        left: rect.left + window.scrollX,
        width: rect.width
      });
    }
  };

  const handleFocus = () => {
    updateDropdownPosition();
    setOpenSuggestions(true);
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
            ref={inputRef}
            id="patientId"
            type="text"
            value={query}
            onChange={(e) => { 
              setQuery(e.target.value); 
              onPatientIdChange(e.target.value); 
              if (!openSuggestions) {
                updateDropdownPosition();
                setOpenSuggestions(true);
              }
              setHighlighted(-1); 
            }}
            onFocus={handleFocus}
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
        </div>
        <button
          type="button"
          className="inline-flex items-center justify-center w-8 h-8 rounded-md border border-navy-200 bg-navy-50 text-navy-700 hover:bg-navy-100"
          onClick={onOpenPatients}
          title="Browse all patients"
        >
          <Users className="w-4 h-4" />
        </button>
      </div>
      
      {/* Portal dropdown outside header stacking context */}
      {openSuggestions && dropdownPosition && createPortal(
        <div 
          data-patient-dropdown
          className="fixed z-[9999] bg-white border border-gray-200 rounded-md shadow-2xl"
          style={{
            top: dropdownPosition.top,
            left: dropdownPosition.left,
            width: dropdownPosition.width,
          }}
        >
          {filtered.length === 0 ? (
            <div className="px-3 py-2 text-sm text-gray-500">No matches</div>
          ) : (
            <ul className="max-h-64 overflow-auto py-1">
              {filtered.map((pid, idx) => (
                <li key={pid}>
                  <button
                    className={`w-full text-left px-3 py-2 text-sm ${idx === highlighted ? 'bg-navy-50 text-navy-700' : 'hover:bg-gray-50 text-gray-700'}`}
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
                    className={`w-full text-left px-3 py-2 text-sm ${highlighted === filtered.length ? 'bg-navy-50 text-navy-700' : 'hover:bg-gray-50 text-gray-700'}`}
                    onMouseEnter={() => setHighlighted(filtered.length)}
                    onMouseLeave={() => setHighlighted(-1)}
                    onClick={() => { onOpenPatients(); setOpenSuggestions(false); setDropdownPosition(null); }}
                  >
                    View all patients…
                  </button>
                </li>
              )}
            </ul>
          )}
        </div>,
        document.body
      )}
    </div>
  );
}