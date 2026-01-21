import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot } from 'lucide-react';
import { AssistantConversation, ChatMessage as ChatMessageType } from '../types';
import { useI18n } from '../i18n/context';
import ChatMessage from './ChatMessage';
import SuggestedQueries from './SuggestedQueries';

interface AssistantChatProps {
  conversation: AssistantConversation | null;
  onSendMessage: (message: string) => Promise<void>;
  isLoading?: boolean;
}

export default function AssistantChat({ 
  conversation, 
  onSendMessage, 
  isLoading = false 
}: AssistantChatProps) {
  const { t } = useI18n();
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation?.messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const message = inputValue.trim();
    setInputValue('');
    setIsTyping(true);

    try {
      await onSendMessage(message);
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleQuerySelect = (query: string) => {
    setInputValue(query);
    textareaRef.current?.focus();
  };

  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [inputValue]);



  return (
    <div className="chat-container h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-white">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-medical-100 rounded-full flex items-center justify-center">
            <Bot className="w-5 h-5 text-medical-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              {t.assistant.title}
            </h2>
            <div className="flex items-center space-x-2">
              <span className="preview-badge">{t.assistant.previewBadge}</span>
              <span className="text-sm text-gray-500">
                {t.assistant.subtitle}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="chat-messages flex-1">
        {!conversation || conversation.messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="max-w-2xl w-full">
              <div className="text-center mb-8">
                <div className="w-16 h-16 bg-medical-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Bot className="w-8 h-8 text-medical-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {t.assistant.chat.welcome.title}
                </h3>
                <p className="text-gray-600 mb-6">
                  {t.assistant.chat.welcome.description}
                </p>
                <div className="inline-flex items-center space-x-2 text-sm text-amber-700 bg-amber-50 px-3 py-2 rounded-lg border border-amber-200">
                  <span>🚧</span>
                  <span>{t.assistant.chat.welcome.previewNotice}</span>
                </div>
              </div>
              
              <SuggestedQueries onQuerySelect={handleQuerySelect} />
            </div>
          </div>
        ) : (
          <>
            {conversation.messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            
            {isTyping && (
              <div className="flex justify-start items-start space-x-3">
                <div className="flex-shrink-0 w-8 h-8 bg-medical-100 rounded-full flex items-center justify-center">
                  <Bot className="w-4 h-4 text-medical-600" />
                </div>
                <div className="chat-message-assistant">
                  <div className="flex items-center space-x-2">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                    <span className="text-sm text-gray-500">{t.assistant.thinking}</span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="chat-input-container">
        <div className="flex items-end space-x-3">
          <div className="flex-1">
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={t.assistant.chat.placeholder}
              className="chat-input resize-none"
              rows={1}
              disabled={isLoading}
            />
          </div>
          
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isLoading}
            className="btn-primary p-3 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        
        <div className="mt-2 text-xs text-gray-500">
          {t.assistant.chat.helpText}
        </div>
      </div>
    </div>
  );
} 