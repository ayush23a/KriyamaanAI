'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  ArrowUp,
  Square,
  Paperclip,
  Globe,
  Database,
  SlidersHorizontal,
  X,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { cn, formatFileSize } from '../../lib/utils';
import { UploadingAttachment } from '../../types';

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
  uploadingAttachments?: UploadingAttachment[];
  onRemoveAttachment?: (id: string) => void;
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
  uploadingAttachments = [],
  onRemoveAttachment,
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

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') {
      return <FileText className="w-4 h-4 text-red-600" />;
    }
    if (ext === 'doc' || ext === 'docx') {
      return <FileText className="w-4 h-4 text-blue-600" />;
    }
    return <FileText className="w-4 h-4 text-[#C25E43]" />;
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

        {/* Uploading Attachments Preview Pill Bar (Gemini / Claude / ChatGPT style) */}
        {uploadingAttachments && uploadingAttachments.length > 0 && (
          <div className="flex flex-wrap gap-2 px-4 pt-3 pb-2 border-b border-[#F2EDE4]/80">
            {uploadingAttachments.map((att) => (
              <div
                key={att.id}
                className={cn(
                  'flex items-center gap-2.5 px-3 py-2 rounded-xl border transition-all text-xs max-w-xs group shadow-2xs',
                  att.status === 'error'
                    ? 'bg-red-50/70 border-red-200'
                    : att.status === 'uploading'
                    ? 'bg-[#FAF8F5] border-[#E7E2DA]'
                    : 'bg-[#F4F6F0]/70 border-[#DCE4D0]'
                )}
              >
                {/* File Icon */}
                <div className="w-7 h-7 rounded-lg bg-white border border-[#E7E2DA] flex items-center justify-center flex-shrink-0 shadow-3xs">
                  {getFileIcon(att.name)}
                </div>

                {/* File Details */}
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-stone-900 truncate text-[12px] leading-tight" title={att.name}>
                    {att.name}
                  </p>
                  <div className="flex items-center gap-1.5 text-[10px] text-stone-500 font-mono mt-0.5">
                    {att.status === 'uploading' && (
                      <span className="inline-flex items-center gap-1 text-[#C25E43] font-sans">
                        <Loader2 className="w-2.5 h-2.5 animate-spin" />
                        <span>Indexing vectors...</span>
                      </span>
                    )}
                    {att.status === 'completed' && (
                      <span className="inline-flex items-center gap-1 text-[#5F7143] font-sans font-medium">
                        <CheckCircle2 className="w-2.5 h-2.5" />
                        <span>{att.chunkCount ? `${att.chunkCount} chunks` : 'Indexed'}</span>
                      </span>
                    )}
                    {att.status === 'error' && (
                      <span className="inline-flex items-center gap-1 text-red-600 font-sans">
                        <AlertCircle className="w-2.5 h-2.5" />
                        <span>{att.error || 'Upload failed'}</span>
                      </span>
                    )}
                    <span>• {formatFileSize(att.size)}</span>
                  </div>
                </div>

                {/* Close / Dismiss button */}
                {onRemoveAttachment && (
                  <button
                    type="button"
                    onClick={() => onRemoveAttachment(att.id)}
                    className="p-1 rounded-md text-stone-400 hover:text-stone-700 hover:bg-[#E7E2DA]/60 transition-colors cursor-pointer"
                    title="Remove attachment preview"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

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

