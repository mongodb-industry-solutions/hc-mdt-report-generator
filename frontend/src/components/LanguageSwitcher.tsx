import React from 'react';
import { Globe } from 'lucide-react';
import { useI18n } from '../i18n/context';

const LanguageSwitcher: React.FC = () => {
  const { t } = useI18n();

  return (
    <div className="relative">
      {/* Language Display - English only */}
      <div
        className="
          flex items-center space-x-2 px-3 py-2 
          text-gray-600 bg-gray-50 rounded-lg
          border border-gray-200
        "
        aria-label={t.settings.language.title}
      >
        <Globe className="w-4 h-4 text-gray-400" />
        <span className="text-sm font-medium">🇺🇸 {t.settings.language.english}</span>
      </div>
    </div>
  );
};

export default LanguageSwitcher; 