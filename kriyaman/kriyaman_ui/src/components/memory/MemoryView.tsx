'use client';

import React, { useState } from 'react';
import {
  Brain,
  Plus,
  Trash2,
  Tag,
  CheckCircle2,
  User,
  BookMarked,
  Briefcase,
  Search,
  Sparkles,
  ArrowLeft,
} from 'lucide-react';
import { MemoryItem } from '../../types';
import { cn } from '../../lib/utils';

interface MemoryViewProps {
  memories: MemoryItem[];
  onCreateMemory: (content: string, kind: string) => Promise<void>;
  onDeleteMemory: (memoryId: string) => Promise<void>;
  onBack?: () => void;
}

export const MemoryView: React.FC<MemoryViewProps> = ({
  memories,
  onCreateMemory,
  onDeleteMemory,
  onBack,
}) => {
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [isAdding, setIsAdding] = useState(false);
  const [content, setContent] = useState('');
  const [kind, setKind] = useState('user_preference');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const filteredMemories = memories
    .filter((m) => {
      if (activeFilter === 'all') return true;
      return m.kind === activeFilter;
    })
    .filter((m) => m.content.toLowerCase().includes(searchQuery.toLowerCase()));

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    setIsSubmitting(true);
    try {
      await onCreateMemory(content.trim(), kind);
      setContent('');
      setIsAdding(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await onDeleteMemory(id);
    } finally {
      setDeletingId(null);
    }
  };

  const getKindLabel = (k: string) => {
    switch (k) {
      case 'user_preference':
        return 'Preference';
      case 'domain_fact':
        return 'Domain Fact';
      case 'project_directive':
        return 'Project Directive';
      default:
        return k;
    }
  };

  const getKindIcon = (k: string) => {
    switch (k) {
      case 'user_preference':
        return <User className="w-3.5 h-3.5 text-[#C25E43]" />;
      case 'domain_fact':
        return <BookMarked className="w-3.5 h-3.5 text-[#5F7143]" />;
      case 'project_directive':
        return <Briefcase className="w-3.5 h-3.5 text-[#C07D32]" />;
      default:
        return <Tag className="w-3.5 h-3.5 text-stone-500" />;
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-8 max-w-4xl mx-auto w-full space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              className="p-2 -ml-2 rounded-xl text-stone-500 hover:text-stone-900 hover:bg-[#F2EDE4] transition-colors cursor-pointer mt-0.5"
              title="Back to conversation"
              aria-label="Back to conversation"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
          )}
          <div>
            <h2 className="text-xl font-semibold text-stone-900 tracking-tight">
              Explicit Long-term Memory
            </h2>
            <p className="text-xs sm:text-sm text-stone-600 mt-1">
              Deterministic, user-approved memories injected into agent context to guide answering tone, domain rules, and workflow preferences.
            </p>
          </div>
        </div>

        <button
          onClick={() => setIsAdding(!isAdding)}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#C25E43] text-white hover:bg-[#B04E35] text-xs font-medium transition-colors shadow-xs cursor-pointer self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Add Memory</span>
        </button>
      </div>

      {/* Add Memory Card */}
      {isAdding && (
        <form onSubmit={handleSave} className="rounded-2xl border border-[#E7E2DA] bg-white p-5 space-y-4 shadow-2xs">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-stone-900">Record New Memory</h3>
            <button
              type="button"
              onClick={() => setIsAdding(false)}
              className="text-xs text-stone-400 hover:text-stone-700"
            >
              Cancel
            </button>
          </div>

          <div>
            <label className="block text-xs font-medium text-stone-700 mb-1.5">
              Memory Content
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="e.g. Always structure policy answers with bullet points and explicit citation references."
              rows={3}
              required
              className="w-full text-xs p-3 rounded-xl border border-[#E7E2DA] bg-[#FAF8F5] placeholder:text-stone-400 text-stone-900 focus:outline-none focus:border-[#C25E43] focus:bg-white transition-colors"
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <label className="block text-xs font-medium text-stone-700 mb-1.5">
                Category
              </label>
              <div className="flex gap-2">
                {[
                  { key: 'user_preference', label: 'User Preference' },
                  { key: 'domain_fact', label: 'Domain Fact' },
                  { key: 'project_directive', label: 'Project Directive' },
                ].map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => setKind(item.key)}
                    className={cn(
                      'px-2.5 py-1 rounded-lg text-xs font-medium transition-colors border cursor-pointer',
                      kind === item.key
                        ? 'bg-[#FDF6F3] text-[#C25E43] border-[#F1D6CE]'
                        : 'bg-white text-stone-600 border-[#E7E2DA] hover:bg-stone-50'
                    )}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={isSubmitting || !content.trim()}
                className="px-4 py-2 rounded-xl bg-[#C25E43] text-white hover:bg-[#B04E35] disabled:opacity-50 text-xs font-medium transition-colors cursor-pointer"
              >
                {isSubmitting ? 'Saving...' : 'Save to Principal Namespace'}
              </button>
            </div>
          </div>
        </form>
      )}

      {/* Filter Tabs & Search */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E7E2DA] pb-3">
        <div className="flex items-center gap-1 overflow-x-auto text-xs font-medium">
          {[
            { id: 'all', label: 'All Memories' },
            { id: 'user_preference', label: 'Preferences' },
            { id: 'domain_fact', label: 'Domain Facts' },
            { id: 'project_directive', label: 'Project Rules' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveFilter(tab.id)}
              className={cn(
                'px-3 py-1.5 rounded-lg transition-colors cursor-pointer whitespace-nowrap',
                activeFilter === tab.id
                  ? 'bg-stone-900 text-white'
                  : 'text-stone-600 hover:bg-[#F2EDE4] hover:text-stone-900'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 text-stone-400 absolute left-2.5 top-2.5 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter memories..."
            className="w-full pl-8 pr-3 py-1.5 rounded-lg text-xs bg-white border border-[#E7E2DA] text-stone-900 focus:outline-none focus:border-[#C25E43]"
          />
        </div>
      </div>

      {/* Memory List */}
      {filteredMemories.length === 0 ? (
        <div className="rounded-2xl border border-[#E7E2DA] bg-white p-12 text-center text-stone-500">
          <Brain className="w-8 h-8 text-stone-300 mx-auto mb-2" />
          <p className="text-sm font-medium text-stone-700">No memories found</p>
          <p className="text-xs text-stone-400 mt-1">
            Click "Add Memory" above to establish explicit guidance for Kriyamaan.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredMemories.map((mem) => (
            <div
              key={mem.memory_id}
              className="rounded-xl border border-[#E7E2DA] bg-white p-4 hover:border-stone-300 transition-colors shadow-2xs group flex items-start justify-between gap-4"
            >
              <div className="space-y-1.5 flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#FAF8F5] border border-[#E7E2DA] text-[11px] font-medium text-stone-700 font-mono">
                    {getKindIcon(mem.kind)}
                    <span>{getKindLabel(mem.kind)}</span>
                  </span>
                  <span className="text-[11px] text-stone-400">
                    {new Date(mem.created_at).toLocaleDateString()}
                  </span>
                </div>
                <p className="text-xs text-stone-800 leading-relaxed whitespace-pre-wrap font-sans">
                  {mem.content}
                </p>
              </div>

              <button
                onClick={() => handleDelete(mem.memory_id)}
                disabled={deletingId === mem.memory_id}
                className="opacity-0 group-hover:opacity-100 p-1 text-stone-400 hover:text-[#BA3C2A] rounded transition-opacity cursor-pointer"
                title="Delete memory"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

