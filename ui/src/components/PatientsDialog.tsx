import React from 'react';
import PatientsBrowser from './PatientsBrowser';

interface PatientsDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (patientId: string) => void;
}

export default function PatientsDialog({ isOpen, onClose, onSelect }: PatientsDialogProps) {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30" onClick={onClose}></div>
      <div className="relative bg-white w-full max-w-4xl mx-4 rounded-lg shadow-lg border border-gray-200">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <h3 className="text-lg font-semibold">Select Patient</h3>
          <button className="text-gray-500 hover:text-gray-700" onClick={onClose}>✕</button>
        </div>
        <div className="p-4">
          <PatientsBrowser onSelect={(pid) => { onSelect(pid); onClose(); }} />
        </div>
      </div>
    </div>
  );
}


