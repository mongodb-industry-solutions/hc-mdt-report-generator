import React from 'react';
import { X, Info } from 'lucide-react';

export interface InfoModalContent {
  title: string;
  subtitle?: string;
  sections: {
    title: string;
    points: string[];
    icon?: React.ComponentType<{ className?: string }>;
  }[];
  tips?: string[];
}

interface InfoModalProps {
  isOpen: boolean;
  onClose: () => void;
  content: InfoModalContent;
}

export default function InfoModal({ isOpen, onClose, content }: InfoModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black bg-opacity-50" 
        onClick={onClose}
      ></div>
      
      {/* Modal Content */}
      <div className="relative w-full max-w-2xl max-h-[90vh] m-4">
        <div className="bg-white rounded-2xl shadow-2xl overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-navy-700 to-navy-800 px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-mongodb-green/20 rounded-lg flex items-center justify-center">
                  <Info className="w-5 h-5 text-mongodb-green" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">{content.title}</h2>
                  {content.subtitle && (
                    <p className="text-navy-200 text-sm mt-1">{content.subtitle}</p>
                  )}
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 text-navy-200 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 max-h-[calc(90vh-120px)] overflow-y-auto">
            <div className="space-y-6">
              {content.sections.map((section, index) => {
                const SectionIcon = section.icon;
                return (
                  <div key={index}>
                    <div className="flex items-center space-x-2 mb-3">
                      {SectionIcon && (
                        <SectionIcon className="w-5 h-5 text-navy-600" />
                      )}
                      <h3 className="text-lg font-semibold text-navy-800">{section.title}</h3>
                    </div>
                    <ul className="space-y-2">
                      {section.points.map((point, pointIndex) => (
                        <li key={pointIndex} className="flex items-start space-x-3">
                          <div className="w-2 h-2 bg-mongodb-green rounded-full mt-2 flex-shrink-0"></div>
                          <span className="text-gray-700 leading-relaxed">{point}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}

              {content.tips && content.tips.length > 0 && (
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-200">
                  <h3 className="text-lg font-semibold text-navy-800 mb-3 flex items-center space-x-2">
                    <div className="w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center">
                      <span className="text-white text-xs font-bold">!</span>
                    </div>
                    <span>Pro Tips</span>
                  </h3>
                  <ul className="space-y-2">
                    {content.tips.map((tip, tipIndex) => (
                      <li key={tipIndex} className="flex items-start space-x-2">
                        <div className="w-1.5 h-1.5 bg-blue-500 rounded-full mt-2.5 flex-shrink-0"></div>
                        <span className="text-blue-800 text-sm leading-relaxed">{tip}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex justify-end pt-6 mt-6 border-t border-gray-200">
              <button
                onClick={onClose}
                className="px-6 py-2 bg-gradient-to-r from-navy-600 to-navy-700 text-white rounded-lg hover:from-navy-700 hover:to-navy-800 transition-all font-medium shadow-lg"
              >
                Got it!
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}