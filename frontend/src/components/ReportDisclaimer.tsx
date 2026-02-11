import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { useI18n } from '../i18n/context';

interface ReportDisclaimerProps {
  reportDate?: string;
  aiModel?: string;
  version?: string;
}

const ReportDisclaimer: React.FC<ReportDisclaimerProps> = ({
  reportDate = new Date().toLocaleString(),
  aiModel = "Large Language Model",
  version = "Proof of Concept v1.0"
}) => {
  const { t } = useI18n();

  return (
    <div className="bg-red-50 border-2 border-red-200 rounded-lg p-4 my-4">
      <div className="flex items-center justify-center space-x-2 text-red-800">
        <AlertTriangle className="w-5 h-5" />
        <div className="text-center">
          <h2 className="text-lg font-bold">
            {t.disclaimer.report.title}
          </h2>
          <p className="text-base font-semibold">
            {t.disclaimer.report.subtitle}
          </p>
        </div>
        <AlertTriangle className="w-5 h-5" />
      </div>
    </div>
  );
};

export default ReportDisclaimer; 