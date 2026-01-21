import React from 'react';
import { MessageCircle, Trash2, Calendar } from 'lucide-react';
import { AssistantConversation } from '../types';
import { useI18n } from '../i18n/context';

interface ConversationListProps {
  conversations: AssistantConversation[];
  activeConversationId: string | null;
  onConversationSelect: (conversation: AssistantConversation) => void;
  onConversationDelete: (conversationId: string) => void;
  onNewConversation: () => void;
}

export default function ConversationList({
  conversations,
  activeConversationId,
  onConversationSelect,
  onConversationDelete,
  onNewConversation
}: ConversationListProps) {
  const { t, language } = useI18n();
  
  const formatRelativeTime = (date: Date) => {
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) {
      return t.time.now;
    } else if (diffInHours < 24) {
      return `${diffInHours}h ${t.time.ago}`;
    } else if (diffInHours < 48) {
      return t.assistant.conversations.yesterday;
    } else {
      const diffInDays = Math.floor(diffInHours / 24);
      return `${diffInDays} ${diffInDays > 1 ? t.time.days : 'jour'} ${t.time.ago}`;
    }
  };

  const groupConversationsByDate = (conversations: AssistantConversation[]) => {
    const groups: { [key: string]: AssistantConversation[] } = {};
    
    conversations.forEach(conversation => {
      const date = conversation.updated_at.toDateString();
      if (!groups[date]) {
        groups[date] = [];
      }
      groups[date].push(conversation);
    });
    
    return groups;
  };

  const conversationGroups = groupConversationsByDate(conversations);
  const groupKeys = Object.keys(conversationGroups).sort((a, b) => 
    new Date(b).getTime() - new Date(a).getTime()
  );

  const truncateTitle = (title: string, maxLength: number = 40) => {
    if (title.length <= maxLength) return title;
    return title.substring(0, maxLength) + '...';
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={onNewConversation}
          className="w-full btn-primary flex items-center justify-center space-x-2"
        >
          <MessageCircle className="w-4 h-4" />
          <span>{t.assistant.conversations.newConversation}</span>
        </button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto">
        {conversations.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            <MessageCircle className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p className="text-sm">{t.assistant.conversations.empty.title}</p>
            <p className="text-xs mt-1">{t.assistant.conversations.empty.subtitle}</p>
          </div>
        ) : (
          <div className="p-2 space-y-4">
            {groupKeys.map(dateKey => {
              const groupDate = new Date(dateKey);
              const isToday = groupDate.toDateString() === new Date().toDateString();
              const isYesterday = new Date(Date.now() - 24 * 60 * 60 * 1000).toDateString() === groupDate.toDateString();
              
              let groupLabel = t.assistant.conversations.today;
              if (isYesterday) {
                groupLabel = t.assistant.conversations.yesterday;
              } else if (!isToday) {
                const locale = language === 'fr' ? 'fr-FR' : 'en-US';
                groupLabel = groupDate.toLocaleDateString(locale, { 
                  weekday: 'long', 
                  day: 'numeric', 
                  month: 'long' 
                });
              }

              return (
                <div key={dateKey}>
                  <div className="flex items-center space-x-2 px-2 py-1 mb-2">
                    <Calendar className="w-3 h-3 text-gray-400" />
                    <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                      {groupLabel}
                    </span>
                  </div>
                  
                  <div className="space-y-1">
                    {conversationGroups[dateKey].map(conversation => (
                      <div
                        key={conversation.id}
                        className={
                          activeConversationId === conversation.id 
                            ? 'conversation-item-active' 
                            : 'conversation-item'
                        }
                      >
                        <div 
                          onClick={() => onConversationSelect(conversation)}
                          className="flex-1 cursor-pointer"
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                              <h4 className="text-sm font-medium text-gray-900 truncate">
                                {truncateTitle(conversation.title)}
                              </h4>
                              <div className="flex items-center space-x-2 mt-1">
                                <span className="text-xs text-gray-500">
                                  {conversation.messages.length} {conversation.messages.length > 1 ? t.assistant.conversations.messageCountPlural : t.assistant.conversations.messageCount}
                                </span>
                                <span className="text-xs text-gray-400">•</span>
                                <span className="text-xs text-gray-500">
                                  {formatRelativeTime(conversation.updated_at)}
                                </span>
                              </div>
                            </div>
                            
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onConversationDelete(conversation.id);
                              }}
                              className="p-1 text-gray-400 hover:text-red-600 rounded transition-colors opacity-0 group-hover:opacity-100"
                              title={t.assistant.conversations.deleteTooltip}
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer */}
      {conversations.length > 0 && (
        <div className="p-4 border-t border-gray-200">
          <button
            onClick={() => {
              if (window.confirm(t.assistant.conversations.deleteAllConfirm)) {
                conversations.forEach(conv => onConversationDelete(conv.id));
              }
            }}
            className="w-full text-sm text-gray-500 hover:text-red-600 transition-colors flex items-center justify-center space-x-2"
          >
            <Trash2 className="w-4 h-4" />
            <span>{t.assistant.conversations.deleteAll}</span>
          </button>
        </div>
      )}
    </div>
  );
} 