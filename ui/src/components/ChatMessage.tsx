import React from 'react';
import { Copy, User, Bot } from 'lucide-react';
import { ChatMessage as ChatMessageType } from '../types';
import { useI18n } from '../i18n/context';

interface ChatMessageProps {
  message: ChatMessageType;
  onCopy?: (content: string) => void;
}

export default function ChatMessage({ message, onCopy }: ChatMessageProps) {
  const { t, language } = useI18n();
  const isUser = message.type === 'user';
  
  const handleCopy = () => {
    if (onCopy) {
      onCopy(message.content);
    } else {
      navigator.clipboard.writeText(message.content);
    }
  };

  const formatTime = (timestamp: Date) => {
    const locale = language === 'fr' ? 'fr-FR' : 'en-US';
    return new Intl.DateTimeFormat(locale, {
      hour: '2-digit',
      minute: '2-digit'
    }).format(timestamp);
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} items-start space-x-3`}>
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 bg-medical-100 rounded-full flex items-center justify-center">
          <Bot className="w-4 h-4 text-medical-600" />
        </div>
      )}
      
      <div className={`group relative ${isUser ? 'order-2' : ''}`}>
        <div className={isUser ? 'chat-message-user' : 'chat-message-assistant'}>
          <div className="whitespace-pre-wrap break-words">
            {message.content}
          </div>
          
          {message.metadata && (
            <div className={`text-xs mt-2 opacity-75 ${isUser ? 'text-white' : 'text-gray-500'}`}>
              {message.metadata.processingTime && (
                <span>{t.assistant.messages.processingTime} {message.metadata.processingTime}ms</span>
              )}
              {message.metadata.resultCount && (
                <span className="ml-2">{message.metadata.resultCount} {t.assistant.messages.results}</span>
              )}
            </div>
          )}
        </div>
        
        <div className={`flex items-center mt-1 space-x-2 opacity-0 group-hover:opacity-100 transition-opacity ${isUser ? 'justify-end' : ''}`}>
          <span className="text-xs text-gray-500">
            {formatTime(message.timestamp)}
          </span>
          <button
            onClick={handleCopy}
            className="p-1 text-gray-400 hover:text-gray-600 rounded transition-colors"
            title={t.assistant.messages.copy}
          >
            <Copy className="w-3 h-3" />
          </button>
        </div>
      </div>
      
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 bg-medical-600 rounded-full flex items-center justify-center order-1">
          <User className="w-4 h-4 text-white" />
        </div>
      )}
    </div>
  );
} 