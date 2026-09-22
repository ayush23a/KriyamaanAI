'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  ArrowUp,
  Square,
  Paperclip,
  Globe,
  Database,
  SlidersHorizontal,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface ComposerProps {
  onSendMessage: (query: string, enableWeb: boolean) => void;
  onStopGeneration?: () => void;
  onUploadFile?: (file: File) => void;
  onOpenSettings?: () => void;
  isStreaming?: boolean;
  disabled?: boolean;
  initialQuery?: string;
  defaultEnableWeb?: boolean;
  documentCount?: number;
}

export const Composer: React.FC<ComposerProps> = ({
  onSendMessage,
  onStopGeneration,
  onUploadFile,
  onOpenSettings,
  isStreaming = false,
  disabled = false,
  initialQuery = '',
  defaultEnableWeb = false,
  documentCount = 0,
}) => {
  const [query, setQuery] = useState(initialQuery);
  const [enableWeb, setEnableWeb] = useState(defaultEnableWeb);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (initialQuery) {
      setQuery(initialQuery);
      textareaRef.current?.focus();
    }
  }, [initialQuery]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    const trimmed = query.trim();
    if (!trimmed || isStreaming || disabled) return;
    onSendMessage(trimmed, enableWeb);
    setQuery('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && onUploadFile) {
      onUploadFile(file);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-4 sm:pb-6">
      <div className="relative rounded-2xl border border-[#E7E2DA] bg-white shadow-xs focus-within:border-[#C25E43] focus-within:ring-1 focus-within:ring-[#C25E43]/20 transition-all">
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          onChange={handleFileChange}
          accept=".pdf,.docx,.txt,.md,.html"
        />

        {/* Text Input Area */}
        <div className="px-4 pt-3.5 pb-2">
          <textarea
            ref={textareaRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="Ask anything about your documents or research topic..."
            rows={1}
            className="w-full resize-none border-0 bg-transparent p-0 text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-0 text-[15px] leading-relaxed max-h-[180px]"
          />
        </div>

        {/* Controls & Scope Toolbar */}
        <div className="flex items-center justify-between px-3 pb-2.5 pt-1 text-xs text-stone-600">
          <div className="flex items-center gap-1.5 flex-wrap">
            {/* Attachment Button */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled || isStreaming}
              className="inline-flex items-center gap-1 py-1 px-2 rounded-lg hover:bg-[#F2EDE4] hover:text-stone-900 transition-colors disabled:opacity-50 cursor-pointer"
              title="Attach and ingest a document (.pdf, .docx, .txt, .md)"
            >
              <Paperclip className="w-3.5 h-3.5 text-stone-500" />
              <span className="hidden sm:inline">Attach doc</span>
            </button>

            {/* Knowledge Scope Indicator */}
            <div className="h-3.5 w-px bg-[#E7E2DA] mx-0.5 hidden sm:block" />

            <span className="inline-flex items-center gap-1 py-1 px-2 text-stone-500 font-mono text-[11px]">
              <Database className="w-3 h-3 text-stone-400" />
              <span>{documentCount} docs indexed</span>
            </span>

            {/* Web Search Toggle */}
            <button
              type="button"
              onClick={() => setEnableWeb(!enableWeb)}
              disabled={disabled || isStreaming}
              className={cn(
                'inline-flex items-center gap-1 py-1 px-2 rounded-lg transition-colors cursor-pointer text-xs',
                enableWeb
                  ? 'bg-[#FDF6F3] text-[#C25E43] border border-[#F1D6CE] font-medium'
                  : 'hover:bg-[#F2EDE4] text-stone-500 hover:text-stone-900'
              )}
              title="Toggle Web Search fallback"
            >
              <Globe className={cn('w-3.5 h-3.5', enableWeb ? 'text-[#C25E43]' : 'text-stone-400')} />
              <span>Web Search {enableWeb ? 'On' : 'Off'}</span>
            </button>

            {/* Agent Settings Shortcut */}
            {onOpenSettings && (
              <button
                type="button"
                onClick={onOpenSettings}
                className="hidden sm:inline-flex items-center gap-1 py-1 px-1.5 rounded-lg hover:bg-[#F2EDE4] text-stone-400 hover:text-stone-700 transition-colors cursor-pointer"
                title="Agent execution configuration"
              >
                <SlidersHorizontal className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Action Button: Send or Stop */}
          <div className="flex items-center gap-2">
            <span className="hidden sm:inline text-[11px] text-stone-400 font-mono">
              ↵ to send
            </span>

            {isStreaming ? (
              <button
                type="button"
                onClick={onStopGeneration}
                className="w-8 h-8 rounded-xl bg-stone-900 text-white flex items-center justify-center hover:bg-stone-800 transition-all cursor-pointer shadow-xs"
                title="Stop generation"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={!query.trim() || disabled}
                className={cn(
                  'w-8 h-8 rounded-xl flex items-center justify-center transition-all shadow-xs',
                  query.trim() && !disabled
                    ? 'bg-[#C25E43] text-white hover:bg-[#B04E35] cursor-pointer'
                    : 'bg-stone-200 text-stone-400 cursor-not-allowed'
                )}
                title="Send query"
              >
                <ArrowUp className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

