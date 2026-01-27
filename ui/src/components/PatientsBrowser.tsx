import React, { useEffect, useMemo, useState } from 'react';
import { apiService } from '../services/api';
import { Search, User } from 'lucide-react';

interface PatientsBrowserProps {
  onSelect: (patientId: string) => void;
}

export default function PatientsBrowser({ onSelect }: PatientsBrowserProps) {
  const [patients, setPatients] = useState<string[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    apiService.getPatients()
      .then(res => { if (mounted) setPatients(res.items || []); })
      .catch(err => { if (mounted) setError(err?.message || 'Failed to load patients'); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, []);

  const filtered = useMemo(() => {
    if (!query) return patients;
    const q = query.toLowerCase();
    return patients.filter(p => p.toLowerCase().includes(q));
  }, [patients, query]);

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Patients</h2>
        <div className="flex items-center space-x-2 border border-gray-200 rounded-md px-2 py-1 bg-white">
          <Search className="w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by patient ID"
            className="outline-none text-sm"
          />
        </div>
      </div>

      {loading && (
        <div className="py-6 text-sm text-gray-500">Loading...</div>
      )}
      {error && (
        <div className="py-6 text-sm text-red-600">{error}</div>
      )}

      {!loading && !error && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {filtered.map(pid => (
            <button
              key={pid}
              className="flex items-center space-x-2 px-3 py-2 border border-gray-200 rounded-md bg-white hover:bg-gray-50 text-left"
              onClick={() => onSelect(pid)}
            >
              <div className="w-6 h-6 bg-navy-100 text-navy-700 rounded flex items-center justify-center">
                <User className="w-4 h-4" />
              </div>
              <div className="text-sm font-medium text-gray-800">{pid}</div>
            </button>
          ))}
          {filtered.length === 0 && (
            <div className="text-sm text-gray-500 col-span-full">No patients found</div>
          )}
        </div>
      )}
    </div>
  );
}


