import React, { useState } from 'react';
import { X, Check } from 'lucide-react';
import { useI18n } from '../i18n/context';

interface DisclaimerModalProps {
  isOpen: boolean;
  onAccept: () => void;
  onReject: () => void;
}

const DisclaimerModal: React.FC<DisclaimerModalProps> = ({ isOpen, onAccept, onReject }) => {
  const [hasReadDisclaimer, setHasReadDisclaimer] = useState(false);
  const [acknowledgeChecked, setAcknowledgeChecked] = useState(false);
  const { t } = useI18n();

  if (!isOpen) return null;

  const handleAccept = () => {
    if (acknowledgeChecked) {
      onAccept();
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-xl w-full">
        <div className="px-6 pt-6">
          <h1 className="text-lg font-semibold text-gray-900 tracking-tight">
            {t.disclaimer.modalShort.headline}
          </h1>
          <div className="mt-3 space-y-2">
            {t.disclaimer.modalShort.body.map((line: string, idx: number) => (
              <p key={idx} className="text-sm text-gray-700">
                {line}
              </p>
            ))}
          </div>
          <div className="mt-4 flex items-start space-x-3">
            <input
              type="checkbox"
              id="acknowledge"
              checked={acknowledgeChecked}
              onChange={(e) => setAcknowledgeChecked(e.target.checked)}
              className="mt-0.5 w-4 h-4 text-navy-700 border-gray-300 rounded focus:ring-navy-500"
            />
            <label htmlFor="acknowledge" className="text-sm text-gray-800">
              {t.disclaimer.modalShort.checkbox}
            </label>
          </div>
        </div>
        <div className="px-6 py-4 mt-4 border-t border-gray-200 flex items-center justify-between rounded-b-xl bg-gray-50">
          <button
            onClick={onReject}
            className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
          >
            <X className="w-4 h-4 mr-2" />
            {t.disclaimer.modal.buttons.exit}
          </button>
          <button
            onClick={handleAccept}
            disabled={!acknowledgeChecked}
            className={`inline-flex items-center px-4 py-2 text-sm font-medium rounded-md ${
              acknowledgeChecked
                ? 'bg-navy-700 text-white hover:bg-navy-800'
                : 'bg-gray-200 text-gray-500 cursor-not-allowed'
            }`}
          >
            <Check className="w-4 h-4 mr-2" />
            {t.disclaimer.modal.buttons.continue}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DisclaimerModal; 