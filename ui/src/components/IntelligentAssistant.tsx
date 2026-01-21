import React, { useState, useEffect } from 'react';
import { AssistantConversation, ChatMessage } from '../types';
import { useI18n } from '../i18n/context';
import AssistantSidebar from './AssistantSidebar';
import AssistantChat from './AssistantChat';

export default function IntelligentAssistant() {
  const { t } = useI18n();
  const [conversations, setConversations] = useState<AssistantConversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Load conversations from localStorage on mount
  useEffect(() => {
    const savedConversations = localStorage.getItem('assistant_conversations');
    if (savedConversations) {
      try {
        const parsed = JSON.parse(savedConversations);
        const conversationsWithDates = parsed.map((conv: any) => ({
          ...conv,
          created_at: new Date(conv.created_at),
          updated_at: new Date(conv.updated_at),
          messages: conv.messages.map((msg: any) => ({
            ...msg,
            timestamp: new Date(msg.timestamp)
          }))
        }));
        setConversations(conversationsWithDates);
      } catch (error) {
        console.error('Error loading conversations:', error);
      }
    }
  }, []);

  // Save conversations to localStorage whenever they change
  useEffect(() => {
    if (conversations.length > 0) {
      localStorage.setItem('assistant_conversations', JSON.stringify(conversations));
    }
  }, [conversations]);

  const generateId = () => {
    return Math.random().toString(36).substring(2) + Date.now().toString(36);
  };

  const createNewConversation = (): AssistantConversation => {
    return {
      id: generateId(),
      title: t.assistant.conversations.defaultTitle,
      messages: [],
      created_at: new Date(),
      updated_at: new Date(),
      metadata: {
        totalMessages: 0,
        queryTypes: []
      }
    };
  };

  const handleNewConversation = () => {
    const newConversation = createNewConversation();
    setConversations(prev => [newConversation, ...prev]);
    setActiveConversationId(newConversation.id);
  };

  const handleConversationSelect = (conversation: AssistantConversation) => {
    setActiveConversationId(conversation.id);
  };

  const handleConversationDelete = (conversationId: string) => {
    setConversations(prev => prev.filter(conv => conv.id !== conversationId));
    
    if (activeConversationId === conversationId) {
      const remainingConversations = conversations.filter(conv => conv.id !== conversationId);
      setActiveConversationId(remainingConversations.length > 0 ? remainingConversations[0].id : null);
    }
  };

  const simulateAssistantResponse = async (userMessage: string): Promise<string> => {
    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, 1500 + Math.random() * 1000));
    
    // Generate contextual responses based on message content
    const messageWords = userMessage.toLowerCase();
    
    if (messageWords.includes('patient') || messageWords.includes('cas')) {
      return t.assistant.responses.patientQuery.replace('{query}', userMessage);
    }
    
    if (messageWords.includes('traitement') || messageWords.includes('thérapie') || messageWords.includes('médicament')) {
      return t.assistant.responses.treatmentQuery.replace('{query}', userMessage);
    }
    
    if (messageWords.includes('mutation') || messageWords.includes('génétique') || messageWords.includes('biomarqueur')) {
      return t.assistant.responses.molecularQuery.replace('{query}', userMessage);
    }
    
    // Default response
    const responses = t.assistant.responses.defaultResponses.map(response => 
      response.replace('{query}', userMessage)
    );
    
    return responses[Math.floor(Math.random() * responses.length)];
  };

  const handleSendMessage = async (message: string) => {
    let conversation = conversations.find(conv => conv.id === activeConversationId);
    
    // Create new conversation if none exists
    if (!conversation) {
      conversation = createNewConversation();
      setConversations(prev => [conversation!, ...prev]);
      setActiveConversationId(conversation.id);
    }

    // Create user message
    const userMessage: ChatMessage = {
      id: generateId(),
      type: 'user',
      content: message,
      timestamp: new Date(),
      metadata: {
        queryType: 'general'
      }
    };

    // Update conversation title with first message
    const isFirstMessage = conversation.messages.length === 0;
    const conversationTitle = isFirstMessage 
      ? message.length > 50 ? message.substring(0, 47) + '...' : message
      : conversation.title;

    // Add user message to conversation
    setConversations(prev => prev.map(conv => 
      conv.id === conversation!.id 
        ? {
            ...conv,
            title: conversationTitle,
            messages: [...conv.messages, userMessage],
            updated_at: new Date(),
            metadata: {
              totalMessages: conv.messages.length + 1,
              queryTypes: [...(conv.metadata?.queryTypes || []), 'general']
            }
          }
        : conv
    ));

    setIsLoading(true);

    try {
      // Simulate assistant response
      const assistantResponseText = await simulateAssistantResponse(message);
      
      const assistantMessage: ChatMessage = {
        id: generateId(),
        type: 'assistant',
        content: assistantResponseText,
        timestamp: new Date(),
        metadata: {
          processingTime: 1500 + Math.random() * 1000,
          queryType: 'general'
        }
      };

      // Add assistant message to conversation
      setConversations(prev => prev.map(conv => 
        conv.id === conversation!.id 
          ? {
              ...conv,
              messages: [...conv.messages, assistantMessage],
              updated_at: new Date(),
              metadata: {
                totalMessages: conv.messages.length + 2,
                queryTypes: [...(conv.metadata?.queryTypes || []), 'general']
              }
            }
          : conv
      ));

    } catch (error) {
      console.error('Error getting assistant response:', error);
      
      // Add error message
      const errorMessage: ChatMessage = {
        id: generateId(),
        type: 'assistant',
        content: t.assistant.messages.error,
        timestamp: new Date(),
        metadata: {
          queryType: 'general'
        }
      };

      setConversations(prev => prev.map(conv => 
        conv.id === conversation!.id 
          ? {
              ...conv,
              messages: [...conv.messages, errorMessage],
              updated_at: new Date()
            }
          : conv
      ));
    } finally {
      setIsLoading(false);
    }
  };

  const activeConversation = conversations.find(conv => conv.id === activeConversationId) || null;

  return (
    <div className="h-[calc(100vh-12rem)] flex bg-gray-50 rounded-lg overflow-hidden shadow-sm border border-gray-200">
      {/* Sidebar - Hidden on mobile, shown on lg+ */}
      <div className="hidden lg:block">
        <AssistantSidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          onConversationSelect={handleConversationSelect}
          onConversationDelete={handleConversationDelete}
          onNewConversation={handleNewConversation}
        />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        <AssistantChat
          conversation={activeConversation}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
        />
      </div>

      {/* Mobile Sidebar - Could be implemented as a modal/drawer */}
      {/* For now, we'll keep it simple with just the chat interface on mobile */}
    </div>
  );
} 