import React, { useState } from 'react';
import { ChevronDown, Globe } from 'lucide-react';
import { useI18n, Language } from '../i18n/context';

const LanguageSwitcher: React.FC = () => {
  const { language, setLanguage, t } = useI18n();
  const [isOpen, setIsOpen] = useState(false);

  const languages = [
    { code: 'en' as Language, name: t.settings.language.english, flag: '🇺🇸' },
    { code: 'fr' as Language, name: t.settings.language.french, flag: '🇫🇷' },
  ];

  const currentLanguage = languages.find(lang => lang.code === language);

  const handleLanguageChange = (newLanguage: Language) => {
    setLanguage(newLanguage);
    setIsOpen(false);
  };

  const handleClickOutside = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      setIsOpen(false);
    }
  };

  return (
    <div className="relative">
      {/* Language Switcher Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="
          flex items-center space-x-2 px-3 py-2 
          text-gray-600 hover:text-gray-900 hover:bg-gray-100 
          rounded-lg transition-all duration-200 
          focus:outline-none focus:ring-2 focus:ring-navy-500 focus:ring-offset-2
          border border-transparent hover:border-gray-200
        "
        aria-label={t.settings.language.title}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <Globe className="w-4 h-4" />
        <span className="text-sm font-medium">
          {currentLanguage?.flag} {currentLanguage?.name}
        </span>
        <ChevronDown 
          className={`w-4 h-4 transition-transform duration-200 ${
            isOpen ? 'rotate-180' : 'rotate-0'
          }`} 
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={handleClickOutside}
            aria-hidden="true"
          />
          
          {/* Menu */}
          <div className="
            absolute right-0 top-full mt-2 w-48 z-50
            bg-white rounded-lg shadow-lg border border-gray-200
            py-1 animate-in fade-in-0 zoom-in-95 duration-200
          ">
            {languages.map((lang) => (
              <button
                key={lang.code}
                onClick={() => handleLanguageChange(lang.code)}
                className={`
                  w-full flex items-center space-x-3 px-4 py-3 text-left
                  transition-colors duration-150
                  ${language === lang.code
                    ? 'bg-navy-50 text-navy-700 border-r-2 border-navy-500'
                    : 'text-gray-700 hover:bg-gray-50'
                  }
                  focus:outline-none focus:bg-gray-50
                `}
                role="menuitem"
              >
                <span className="text-lg" role="img" aria-label={`${lang.name} flag`}>
                  {lang.flag}
                </span>
                <div className="flex-1">
                  <div className="font-medium">{lang.name}</div>
                  <div className="text-xs text-gray-500">
                    {lang.code === 'en' ? 'English' : 'Français'}
                  </div>
                </div>
                {language === lang.code && (
                  <div className="w-2 h-2 bg-navy-500 rounded-full" />
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default LanguageSwitcher; 