'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronUp, FileText, Globe, CheckCircle2, ExternalLink } from 'lucide-react';
import { EvidenceItem } from '../../types';
import { cn } from '../../lib/utils';

interface EvidenceDrawerProps {
  evidence: EvidenceItem[];
  citations?: string[];
  activeCitationId?: string | null;
  onPreviewSource?: (evidence: EvidenceItem) => void;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({
  evidence,
  citations = [],
  activeCitationId,
  onPreviewSource,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({});

  if (!evidence || evidence.length === 0) return null;

  const toggleItem = (id: string) => {
    setExpandedItems((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const citedCount = evidence.filter((e) => citations.includes(e.evidence_id)).length;

  return (
    <div className="mt-3.5 pt-3 border-t border-[#E7E2DA]/70">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center gap-2 text-xs font-medium text-stone-600 hover:text-stone-900 transition-colors py-1 px-2 -ml-2 rounded hover:bg-[#F2EDE4]/60 cursor-pointer"
      >
        <span className="flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5 text-[#C25E43]" />
          <span>
            {evidence.length} {evidence.length === 1 ? 'source' : 'sources'}
            {citedCount > 0 && ` (${citedCount} cited in answer)`}
          </span>
        </span>
        {isOpen ? <ChevronUp className="w-3.5 h-3.5 text-stone-400" /> : <ChevronDown className="w-3.5 h-3.5 text-stone-400" />}
      </button>

      {isOpen && (
        <div className="mt-2 space-y-2">
          {evidence.map((item) => {
            const isCited = citations.includes(item.evidence_id);
            const isTargeted = activeCitationId === item.evidence_id;
            const isItemExpanded = !!expandedItems[item.evidence_id];
            const isWeb = item.source_type === 'web' || item.retrieval_method === 'web';

            return (
              <div
                key={item.evidence_id}
                id={`evidence-${item.evidence_id}`}
                className={cn(
                  'rounded-lg border text-xs p-3 transition-all',
                  isTargeted
                    ? 'border-[#C25E43] bg-[#FDF6F3] shadow-xs'
                    : isCited
                    ? 'border-[#DCE4D0] bg-[#F4F6F0]/60'
                    : 'border-[#E7E2DA] bg-white'
                )}
              >
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {/* Method Badge */}
                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-stone-100 text-stone-700 font-mono text-[11px] border border-stone-200">
                      {isWeb ? <Globe className="w-3 h-3 text-stone-500" /> : <FileText className="w-3 h-3 text-stone-500" />}
                      {item.retrieval_method || item.source_type}
                    </span>

                    {/* Evidence ID */}
                    <span className="font-mono text-stone-500 text-[11px]">
                      {item.evidence_id}
                    </span>

                    {/* Cited Badge */}
                    {isCited && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#F4F6F0] text-[#5F7143] border border-[#DCE4D0] font-medium text-[11px]">
                        <CheckCircle2 className="w-3 h-3" />
                        Cited
                      </span>
                    )}

                    {/* Score */}
                    {item.retrieval_score !== null && item.retrieval_score !== undefined && (
                      <span className="text-stone-400 text-[11px]">
                        score: {item.retrieval_score.toFixed(3)}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5">
                    {onPreviewSource && (
                      <button
                        onClick={() => onPreviewSource(item)}
                        className="text-stone-500 hover:text-stone-800 p-0.5 rounded hover:bg-stone-100"
                        title="Inspect source snippet"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </button>
                    )}
                    <button
                      onClick={() => toggleItem(item.evidence_id)}
                      className="text-stone-500 hover:text-stone-800 p-0.5 rounded hover:bg-stone-100"
                    >
                      {isItemExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                <div className="text-stone-700 leading-relaxed font-sans text-xs">
                  {isItemExpanded ? (
                    <p className="whitespace-pre-wrap">{item.content}</p>
                  ) : (
                    <p className="line-clamp-2">{item.content}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

