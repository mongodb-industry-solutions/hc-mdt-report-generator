import React from 'react';
import { AssistantConversation } from '../types';
import ConversationList from './ConversationList';

interface AssistantSidebarProps {
  conversations: AssistantConversation[];
  activeConversationId: string | null;
  onConversationSelect: (conversation: AssistantConversation) => void;
  onConversationDelete: (conversationId: string) => void;
  onNewConversation: () => void;
}

export default function AssistantSidebar({
  conversations,
  activeConversationId,
  onConversationSelect,
  onConversationDelete,
  onNewConversation
}: AssistantSidebarProps) {
  return (
    <div className="w-80 bg-white border-r border-gray-200 h-full flex flex-col">
      <ConversationList
        conversations={conversations}
        activeConversationId={activeConversationId}
        onConversationSelect={onConversationSelect}
        onConversationDelete={onConversationDelete}
        onNewConversation={onNewConversation}
      />
    </div>
  );
} 