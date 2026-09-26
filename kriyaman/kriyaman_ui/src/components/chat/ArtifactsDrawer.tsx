'use client';

import React, { useState, useRef } from 'react';
import {
  X,
  Files,
  FileText,
  Upload,
  Trash2,
  CheckCircle2,
  Clock,
  Layers,
  Search,
  ExternalLink,
  Plus,
} from 'lucide-react';
import { DocumentItem } from '../../types';
import { cn } from '../../lib/utils';

interface ArtifactsDrawerProps {
  documents: DocumentItem[];
  onClose: () => void;
  onUploadDocument: (file: File) => Promise<void>;
  onDeleteDocument: (documentId: string) => Promise<void>;
  isUploading?: boolean;
}

export const ArtifactsDrawer: React.FC<ArtifactsDrawerProps> = ({
  documents,
  onClose,
  onUploadDocument,
  onDeleteDocument,
  isUploading = false,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const filteredDocs = documents.filter((d) =>
    d.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await onUploadDocument(file);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setDeletingId(id);
    try {
      await onDeleteDocument(id);
    } finally {
      setDeletingId(null);
    }
  };

  const getFileBadge = (name: string, mime: string) => {
    const ext = name.split('.').pop()?.toUpperCase() || mime.split('/')[1]?.toUpperCase() || 'DOC';
    if (ext === 'PDF') {
      return { label: 'PDF', bg: 'bg-red-50 text-red-600 border-red-200' };
    }
    if (ext === 'DOC' || ext === 'DOCX') {
      return { label: ext, bg: 'bg-blue-50 text-blue-600 border-blue-200' };
    }
    if (ext === 'TXT' || ext === 'MD') {
      return { label: ext, bg: 'bg-stone-100 text-stone-700 border-stone-200' };
    }
    return { label: ext, bg: 'bg-amber-50 text-amber-700 border-amber-200' };
  };

  return (
    <aside className="w-full sm:w-[380px] lg:w-[400px] h-full flex flex-col border-l border-[#E7E2DA] bg-[#FAF8F5] text-stone-900 shadow-sm z-20">
      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={handleFileChange}
        accept=".pdf,.docx,.txt,.md,.html"
      />

      {/* Drawer Header */}
      <div className="flex items-center justify-between px-4 py-3.5 border-b border-[#E7E2DA] bg-white flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-[#FAF8F5] border border-[#E7E2DA] flex items-center justify-center text-[#C25E43] flex-shrink-0">
            <Files className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs sm:text-sm font-semibold text-stone-900">Session Artifacts</h2>
              <span className="px-1.5 py-0.5 rounded-full bg-stone-100 text-stone-600 font-mono text-[10px] font-medium border border-stone-200">
                {documents.length} {documents.length === 1 ? 'doc' : 'docs'}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Quick Upload Button */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#FAF8F5] border border-[#E7E2DA] text-xs font-medium text-stone-700 hover:text-stone-900 hover:border-stone-400 transition-colors cursor-pointer disabled:opacity-50"
            title="Upload new document"
          >
            <Plus className="w-3.5 h-3.5 text-[#C25E43]" />
            <span className="hidden sm:inline">Add</span>
          </button>

          {/* Close Drawer Button */}
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-stone-400 hover:text-stone-800 hover:bg-[#F2EDE4] transition-colors cursor-pointer"
            title="Close drawer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Search / Filter Bar (if 3+ documents) */}
      {documents.length >= 3 && (
        <div className="px-4 py-2 border-b border-[#E7E2DA] bg-white/70">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-stone-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter session documents..."
              className="w-full pl-8 pr-3 py-1 text-xs bg-[#FAF8F5] border border-[#E7E2DA] rounded-lg text-stone-800 placeholder:text-stone-400 focus:outline-none focus:border-[#C25E43]"
            />
          </div>
        </div>
      )}

      {/* Drawer Body: 2 Files In A Row */}
      <div className="flex-1 overflow-y-auto p-3.5 sm:p-4">
        {documents.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 border-2 border-dashed border-[#E7E2DA] rounded-2xl bg-white/60">
            <div className="w-12 h-12 rounded-2xl bg-[#F2EDE4] flex items-center justify-center text-[#C25E43] mb-3">
              <Upload className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-semibold text-stone-800 mb-1">No Artifacts Ingested</h3>
            <p className="text-xs text-stone-500 mb-4 max-w-[260px] leading-relaxed">
              Upload documents (PDF, DOCX, TXT, MD) to query and ground answers in your active session.
            </p>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#C25E43] text-white text-xs font-medium hover:bg-[#B04E35] transition-colors cursor-pointer shadow-xs"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Upload Document</span>
            </button>
          </div>
        ) : filteredDocs.length === 0 ? (
          <div className="text-center py-12 text-stone-500 text-xs">
            No artifacts matching &quot;{searchQuery}&quot;
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-2.5">
            {filteredDocs.map((doc) => {
              const badge = getFileBadge(doc.name, doc.mime_type);
              const isDeleting = deletingId === doc.document_id;
              const isReady =
                doc.status === 'indexed' ||
                doc.status === 'ready' ||
                doc.status === 'completed' ||
                doc.status === 'processed';

              return (
                <div
                  key={doc.document_id}
                  className="rounded-xl border border-[#E7E2DA] bg-white p-2.5 flex flex-col justify-between hover:border-stone-400 hover:shadow-2xs transition-all relative group min-h-[128px]"
                >
                  {/* Top Bar: Badge & Delete Button */}
                  <div className="flex items-center justify-between gap-1 mb-2">
                    <span
                      className={cn(
                        'px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold border',
                        badge.bg
                      )}
                    >
                      {badge.label}
                    </span>

                    <button
                      type="button"
                      onClick={(e) => handleDelete(e, doc.document_id)}
                      disabled={isDeleting}
                      className="p-1 rounded-md text-stone-300 hover:text-red-600 hover:bg-red-50 transition-colors opacity-80 group-hover:opacity-100 cursor-pointer"
                      title="Delete document and chunk vectors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Document Name */}
                  <div className="flex-1 my-1">
                    <p
                      className="text-xs font-medium text-stone-900 line-clamp-2 leading-snug break-words"
                      title={doc.name}
                    >
                      {doc.name}
                    </p>
                  </div>

                  {/* Card Footer: Chunks & Ready Status */}
                  <div className="pt-2 border-t border-[#F2EDE4] flex items-center justify-between text-[11px] text-stone-500 font-mono mt-auto">
                    <span className="inline-flex items-center gap-1">
                      <Layers className="w-3 h-3 text-stone-400" />
                      <span>{doc.chunk_count || 0}</span>
                    </span>

                    <span
                      className={cn(
                        'inline-flex items-center gap-1 text-[10px] font-sans font-medium',
                        isReady ? 'text-[#5F7143]' : 'text-amber-600'
                      )}
                    >
                      {isReady ? (
                        <>
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Indexed</span>
                        </>
                      ) : (
                        <>
                          <Clock className="w-3 h-3" />
                          <span>Processing</span>
                        </>
                      )}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="p-3 border-t border-[#E7E2DA] bg-white text-[11px] text-stone-500 flex items-center justify-between font-mono">
        <span>Grounded via pgvector</span>
        <span>{documents.length} artifacts active</span>
      </div>
    </aside>
  );
};

