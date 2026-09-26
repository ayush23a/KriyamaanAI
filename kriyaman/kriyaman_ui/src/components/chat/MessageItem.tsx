'use client';

import React, { useState } from 'react';
import {
  Copy,
  Check,
  RotateCw,
  Edit3,
  Activity,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Clock,
  Coins,
  Cpu,
} from 'lucide-react';
import { ChatMessage, EvidenceItem } from '../../types';
import { MarkdownContent } from './MarkdownContent';
import { EvidenceDrawer } from './EvidenceDrawer';
import { cn, formatCost, formatLatency, formatTokens } from '../../lib/utils';

interface MessageItemProps {
  message: ChatMessage;
  onRegenerate?: (query: string) => void;
  onEditMessage?: (content: string) => void;
  onOpenInspector?: (message: ChatMessage) => void;
  onPreviewSource?: (evidence: EvidenceItem) => void;
}

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  onRegenerate,
  onEditMessage,
  onOpenInspector,
  onPreviewSource,
}) => {
  const [copied, setCopied] = useState(false);
  const [activeCitationId, setActiveCitationId] = useState<string | null>(null);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCitationClick = (citationId: string) => {
    setActiveCitationId(citationId);
    const targetElement = document.getElementById(`evidence-${citationId}`);
    if (targetElement) {
      targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  // ---------------------------------------------------------------------------
  // User Message
  // ---------------------------------------------------------------------------
  if (message.role === 'user') {
    return (
      <div className="flex justify-end my-4 group">
        <div className="flex flex-col items-end max-w-2xl">
          <div className="bg-[#F2EDE4] text-stone-900 border border-[#E7E2DA] rounded-2xl rounded-tr-xs px-4 py-3 shadow-xs">
            <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{message.content}</p>
          </div>

          <div className="flex items-center gap-2 mt-1.5 px-1 text-xs text-stone-500 opacity-0 group-hover:opacity-100 transition-opacity">
            <span>{message.timestamp}</span>
            {onEditMessage && (
              <button
                onClick={() => onEditMessage(message.content)}
                className="hover:text-stone-900 p-0.5 rounded cursor-pointer"
                title="Edit and resend"
              >
                <Edit3 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Assistant Message
  // ---------------------------------------------------------------------------
  const isAnswer = message.status === 'answer' || (!message.status && !message.isStreaming);
  const isClarification = message.status === 'clarification';
  const isAbstention = message.status === 'abstention';

  return (
    <div className="flex gap-3.5 my-6 group">
      {/* Brand Glyph */}
      <div className="flex-shrink-0 mt-0.5">
        <div className="w-7 h-7 rounded-lg bg-[#FDF6F3] border border-[#F1D6CE] flex items-center justify-center text-[#C25E43] font-serif font-semibold text-xs shadow-xs">
          K
        </div>
      </div>

      <div className="flex-1 min-w-0 max-w-3xl">
        {/* Header line: Assistant name, timestamp, status badge */}
        <div className="flex items-center gap-2 mb-2 text-xs">
          <span className="font-semibold text-stone-900 font-sans">Kriyamaan</span>
          <span className="text-stone-400">{message.timestamp}</span>

          {message.status && (
            <span
              className={cn(
                'inline-flex items-center gap-1 px-1.5 py-0.2 rounded text-[11px] font-medium border',
                isAnswer && 'bg-[#F4F6F0] text-[#5F7143] border-[#DCE4D0]',
                isClarification && 'bg-[#FDF9F2] text-[#C07D32] border-[#F5E5CF]',
                isAbstention && 'bg-[#FCF3F2] text-[#BA3C2A] border-[#F7D5D1]'
              )}
            >
              {isAnswer ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
              {message.status.toUpperCase()}
            </span>
          )}
        </div>

        {/* Live Streaming State / Processing Indicator */}
        {message.isStreaming && (
          <div className="py-2 mb-2 flex items-center gap-2.5 text-xs text-stone-600 bg-[#F7F4EE] border border-[#E7E2DA] rounded-lg px-3.5">
            <span className="w-2 h-2 rounded-full bg-[#C25E43] animate-warm-pulse" />
            <span className="font-medium text-stone-700">
              {message.liveStatus || 'Searching your knowledge...'}
            </span>
          </div>
        )}

        {/* Message Content */}
        {message.content ? (
          <div className="text-stone-800">
            <MarkdownContent
              content={message.content}
              onCitationClick={handleCitationClick}
            />
          </div>
        ) : message.isStreaming ? (
          <div className="h-6 flex items-center">
            <span className="inline-block w-1.5 h-4 bg-[#C25E43] animate-pulse" />
          </div>
        ) : null}

        {/* Citations & Verified Evidence Drawer */}
        {message.evidence && message.evidence.length > 0 && (
          <EvidenceDrawer
            evidence={message.evidence}
            citations={message.citations}
            activeCitationId={activeCitationId}
            onPreviewSource={onPreviewSource}
          />
        )}

        {/* Footer actions: copy, regenerate, metadata telemetry summary */}
        <div className="flex items-center justify-between gap-2 mt-3 pt-2 text-xs text-stone-500">
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-1 py-1 px-1.5 rounded hover:bg-[#F2EDE4] hover:text-stone-900 transition-colors cursor-pointer"
              title="Copy message text"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-[#5F7143]" />
                  <span className="text-[#5F7143]">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy</span>
                </>
              )}
            </button>

            {onRegenerate && (
              <button
                onClick={() => onRegenerate(message.content)}
                className="inline-flex items-center gap-1 py-1 px-1.5 rounded hover:bg-[#F2EDE4] hover:text-stone-900 transition-colors cursor-pointer"
                title="Regenerate answer"
              >
                <RotateCw className="w-3.5 h-3.5" />
                <span>Regenerate</span>
              </button>
            )}
          </div>

          {/* Telemetry pill */}
          {message.metrics && (
            <button
              onClick={() => onOpenInspector?.(message)}
              className="inline-flex items-center gap-2 py-0.5 px-2 rounded bg-[#F7F4EE] border border-[#E7E2DA] hover:border-[#C25E43] hover:text-stone-900 transition-colors cursor-pointer font-mono text-[11px]"
              title="Open execution details inspector"
            >
              <Activity className="w-3 h-3 text-[#C25E43]" />
              {message.metrics.total_latency_ms !== undefined && (
                <span className="flex items-center gap-0.5">
                  <Clock className="w-2.5 h-2.5 text-stone-400" />
                  {formatLatency(message.metrics.total_latency_ms)}
                </span>
              )}
              {message.metrics.prompt_tokens !== undefined && (
                <span className="flex items-center gap-0.5">
                  <Cpu className="w-2.5 h-2.5 text-stone-400" />
                  {formatTokens((message.metrics.prompt_tokens || 0) + (message.metrics.completion_tokens || 0))} tok
                </span>
              )}
              {message.metrics.estimated_cost_usd !== undefined && (
                <span className="flex items-center gap-0.5">
                  <Coins className="w-2.5 h-2.5 text-stone-400" />
                  {formatCost(message.metrics.estimated_cost_usd)}
                </span>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

