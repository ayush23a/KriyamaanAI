'use client';

import React, { useEffect, useRef } from 'react';
import { ChatMessage, EvidenceItem } from '../../types';
import { MessageItem } from './MessageItem';
import { Sparkles, Compass, BookOpen, Layers } from 'lucide-react';

interface MessageListProps {
  messages: ChatMessage[];
  onRegenerate?: (query: string) => void;
  onEditMessage?: (content: string) => void;
  onOpenInspector?: (message: ChatMessage) => void;
  onPreviewSource?: (evidence: EvidenceItem) => void;
  onPromptSelect?: (prompt: string) => void;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  onRegenerate,
  onEditMessage,
  onOpenInspector,
  onPreviewSource,
  onPromptSelect,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, messages[messages.length - 1]?.content, messages[messages.length - 1]?.isStreaming]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 max-w-2xl mx-auto text-center">
        {/* Emblem */}
        <div className="w-12 h-12 rounded-2xl bg-[#FDF6F3] border border-[#F1D6CE] flex items-center justify-center text-[#C25E43] font-serif font-bold text-xl mb-4 shadow-sm">
          K
        </div>

        <h2 className="text-xl font-medium text-stone-900 mb-2">
          Kriyamaan Research Workspace
        </h2>
        <p className="text-sm text-stone-600 mb-8 max-w-md leading-relaxed">
          An agentic retrieval and reasoning system. Ask open-ended questions, explore ingested documents, or analyze evidence with verified citations.
        </p>

        {/* Suggested research prompts */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full text-left">
          {[
            {
              icon: BookOpen,
              title: 'Analyze Ingested Policies',
              desc: 'What are the return or replacement requirements?',
              prompt: 'What are the key policy requirements detailed in the documents?',
            },
            {
              icon: Compass,
              title: 'Synthesize Cross-Source Evidence',
              desc: 'Compare knowledge across multiple files.',
              prompt: 'Summarize the primary guidelines and point out any conflicts or gaps.',
            },
            {
              icon: Layers,
              title: 'Check Evidence & Citations',
              desc: 'Require strict verified attribution.',
              prompt: 'Provide a verified breakdown of the core requirements with citations.',
            },
            {
              icon: Sparkles,
              title: 'Research with Web Fallback',
              desc: 'Search beyond local documents.',
              prompt: 'What are the modern best practices for agentic RAG verification pipelines?',
            },
          ].map((item, idx) => {
            const Icon = item.icon;
            return (
              <button
                key={idx}
                onClick={() => onPromptSelect?.(item.prompt)}
                className="p-3.5 rounded-xl border border-[#E7E2DA] bg-white hover:border-[#C25E43] hover:bg-[#FDF6F3]/50 transition-all text-left group shadow-xs cursor-pointer"
              >
                <div className="flex items-center gap-2 mb-1 text-xs font-semibold text-stone-900 group-hover:text-[#C25E43] transition-colors">
                  <Icon className="w-4 h-4 text-stone-500 group-hover:text-[#C25E43]" />
                  <span>{item.title}</span>
                </div>
                <p className="text-xs text-stone-500 leading-normal line-clamp-2">
                  {item.desc}
                </p>
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 max-w-4xl w-full mx-auto">
      {messages.map((msg) => (
        <MessageItem
          key={msg.id}
          message={msg}
          onRegenerate={onRegenerate}
          onEditMessage={onEditMessage}
          onOpenInspector={onOpenInspector}
          onPreviewSource={onPreviewSource}
        />
      ))}
      <div ref={bottomRef} className="h-4" />
    </div>
  );
};

