import React from 'react';
import { Info } from 'lucide-react';

interface InfoButtonProps {
  onClick: () => void;
  className?: string;
  isActive?: boolean;
}

export default function InfoButton({ onClick, className = '', isActive = false }: InfoButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`
        inline-flex items-center justify-center px-3 py-3
        ${isActive 
          ? 'bg-gradient-to-r from-navy-700 to-navy-800 text-white border border-navy-600 shadow-lg'
          : 'bg-gray-50 hover:bg-mongodb-green/10 text-gray-600 hover:text-mongodb-green border border-gray-200 hover:border-mongodb-green/30 shadow-sm hover:shadow-md'
        }
        rounded-xl transition-all duration-200
        group
        ${className}
      `}
      title="Learn about this section"
    >
      <Info className={`w-4 h-4 transition-colors duration-200 ${isActive ? 'text-mongodb-green' : ''}`} />
    </button>
  );
}