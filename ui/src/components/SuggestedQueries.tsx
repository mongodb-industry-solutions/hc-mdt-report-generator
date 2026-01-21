import React from 'react';
import { Search, TrendingUp, Users, BarChart3, Microscope, Heart } from 'lucide-react';
import { SuggestedQuery } from '../types';
import { useI18n } from '../i18n/context';

interface SuggestedQueriesProps {
  onQuerySelect: (query: string) => void;
}

const iconMap = {
  Search,
  TrendingUp,
  Users,
  BarChart3,
  Microscope,
  Heart
};

export default function SuggestedQueries({ onQuerySelect }: SuggestedQueriesProps) {
  const { t } = useI18n();
  
  const suggestedQueries: SuggestedQuery[] = [
    {
      id: 'find_similar_cases',
      category: 'find_similar',
      title: t.assistant.chat.suggestedQueries.queries.findSimilarTitle,
      description: t.assistant.chat.suggestedQueries.queries.findSimilarDesc,
      query: t.assistant.chat.suggestedQueries.queries.findSimilarQuery,
      icon: 'Search'
    },
    {
      id: 'compare_treatments',
      category: 'compare_treatments',
      title: t.assistant.chat.suggestedQueries.queries.compareTitle,
      description: t.assistant.chat.suggestedQueries.queries.compareDesc,
      query: t.assistant.chat.suggestedQueries.queries.compareQuery,
      icon: 'BarChart3'
    },
    {
      id: 'outcome_analysis',
      category: 'analyze_outcomes',
      title: t.assistant.chat.suggestedQueries.queries.outcomeTitle,
      description: t.assistant.chat.suggestedQueries.queries.outcomeDesc,
      query: t.assistant.chat.suggestedQueries.queries.outcomeQuery,
      icon: 'TrendingUp'
    },
    {
      id: 'molecular_patterns',
      category: 'clinical_patterns',
      title: t.assistant.chat.suggestedQueries.queries.molecularTitle,
      description: t.assistant.chat.suggestedQueries.queries.molecularDesc,
      query: t.assistant.chat.suggestedQueries.queries.molecularQuery,
      icon: 'Microscope'
    },
    {
      id: 'cohort_analysis',
      category: 'find_similar',
      title: t.assistant.chat.suggestedQueries.queries.cohortTitle,
      description: t.assistant.chat.suggestedQueries.queries.cohortDesc,
      query: t.assistant.chat.suggestedQueries.queries.cohortQuery,
      icon: 'Users'
    },
    {
      id: 'comorbidity_analysis',
      category: 'clinical_patterns',
      title: t.assistant.chat.suggestedQueries.queries.comorbidityTitle,
      description: t.assistant.chat.suggestedQueries.queries.comorbidityDesc,
      query: t.assistant.chat.suggestedQueries.queries.comorbidityQuery,
      icon: 'Heart'
    }
  ];

  const handleQueryClick = (query: string) => {
    onQuerySelect(query);
  };

  return (
    <div className="space-y-4">
      <div className="text-center">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          {t.assistant.chat.suggestedQueries.title}
        </h3>
        <p className="text-sm text-gray-600 mb-6">
          {t.assistant.chat.suggestedQueries.subtitle}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {suggestedQueries.map((suggestion) => {
          const Icon = iconMap[suggestion.icon as keyof typeof iconMap];
          
          return (
            <div
              key={suggestion.id}
              onClick={() => handleQueryClick(suggestion.query)}
              className="chat-suggestion group"
            >
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-10 h-10 bg-medical-100 rounded-lg flex items-center justify-center group-hover:bg-medical-200 transition-colors">
                  <Icon className="w-5 h-5 text-medical-600" />
                </div>
                
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-gray-900 mb-1">
                    {suggestion.title}
                  </h4>
                  <p className="text-sm text-gray-600 mb-2 leading-relaxed">
                    {suggestion.description}
                  </p>
                  <p className="text-xs text-medical-600 font-medium italic">
                    "{suggestion.query}"
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="text-center pt-4 border-t border-gray-200">
        <p className="text-sm text-gray-500">
          {t.assistant.chat.suggestedQueries.footerText}
        </p>
      </div>
    </div>
  );
} 