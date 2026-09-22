'use client';

import React, { useState, useRef } from 'react';
import {
  Upload,
  FileText,
  Trash2,
  Search,
  CheckCircle2,
  Clock,
  AlertCircle,
  File,
  ExternalLink,
  X,
  Layers,
  ArrowLeft,
} from 'lucide-react';
import { DocumentItem } from '../../types';
import { cn } from '../../lib/utils';

interface KnowledgeViewProps {
  documents: DocumentItem[];
  onUploadDocument: (file: File) => Promise<void>;
  onDeleteDocument: (documentId: string) => Promise<void>;
  isUploading?: boolean;
  onBack?: () => void;
}

export const KnowledgeView: React.FC<KnowledgeViewProps> = ({
  documents,
  onUploadDocument,
  onDeleteDocument,
  isUploading = false,
  onBack,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const filteredDocs = documents.filter((d) =>
    d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (d.mime_type && d.mime_type.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      await onUploadDocument(file);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await onUploadDocument(file);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await onDeleteDocument(id);
      if (selectedDoc?.document_id === id) {
        setSelectedDoc(null);
      }
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-8 max-w-5xl mx-auto w-full space-y-6">
      {/* Intro Header */}
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
            Document Library
          </h2>
          <p className="text-xs sm:text-sm text-stone-600 mt-1">
            Ingest unstructured documents into session-scoped vector indices with automated chunking, deduplication, and semantic embeddings.
          </p>
        </div>
      </div>

      {/* Drag and Drop Upload Area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        className={cn(
          'border-2 border-dashed rounded-2xl p-6 sm:p-8 text-center transition-all cursor-pointer bg-white',
          isDragging
            ? 'border-[#C25E43] bg-[#FDF6F3]'
            : 'border-[#E7E2DA] hover:border-[#C25E43] hover:bg-[#FAF8F5]',
          isUploading && 'opacity-60 pointer-events-none'
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          onChange={handleFileChange}
          accept=".pdf,.docx,.txt,.md,.html"
        />

        <div className="w-12 h-12 rounded-2xl bg-[#FDF6F3] border border-[#F1D6CE] flex items-center justify-center text-[#C25E43] mx-auto mb-3 shadow-xs">
          <Upload className="w-5 h-5" />
        </div>

        <h3 className="text-sm font-semibold text-stone-900 mb-1">
          {isUploading ? 'Parsing, chunking, and embedding...' : 'Click or drop files to ingest'}
        </h3>
        <p className="text-xs text-stone-500 max-w-sm mx-auto">
          Supports PDF, DOCX, TXT, Markdown, and HTML. Files are chunked and embedded into pgvector.
        </p>
      </div>

      {/* Search & Filter Bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-stone-400 absolute left-3 top-2.5 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search documents by name or mime type..."
            className="w-full pl-9 pr-4 py-2 rounded-xl text-xs bg-white border border-[#E7E2DA] placeholder:text-stone-400 text-stone-900 focus:outline-none focus:border-[#C25E43]"
          />
        </div>

        <div className="text-xs text-stone-500 font-mono">
          {filteredDocs.length} {filteredDocs.length === 1 ? 'document' : 'documents'}
        </div>
      </div>

      {/* Documents List / Table */}
      {filteredDocs.length === 0 ? (
        <div className="rounded-2xl border border-[#E7E2DA] bg-white p-12 text-center text-stone-500">
          <FileText className="w-8 h-8 text-stone-300 mx-auto mb-2" />
          <p className="text-sm font-medium text-stone-700">No documents in this session yet.</p>
          <p className="text-xs text-stone-400 mt-1">Upload a document above to begin semantic research.</p>
        </div>
      ) : (
        <div className="rounded-2xl border border-[#E7E2DA] bg-white overflow-hidden shadow-2xs">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#FAF8F5] border-b border-[#E7E2DA] text-stone-600 font-medium font-sans">
                <th className="py-3 px-4">Document Name</th>
                <th className="py-3 px-4 hidden sm:table-cell">Type</th>
                <th className="py-3 px-4">Chunks</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E7E2DA]">
              {filteredDocs.map((doc) => {
                const isReady = doc.status === 'indexed' || doc.status === 'ready' || doc.status === 'completed';
                return (
                  <tr key={doc.document_id} className="hover:bg-[#FAF8F5]/80 transition-colors">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2.5">
                        <FileText className="w-4 h-4 text-[#C25E43] flex-shrink-0" />
                        <span className="font-medium text-stone-900 truncate max-w-xs">
                          {doc.name}
                        </span>
                      </div>
                    </td>

                    <td className="py-3 px-4 hidden sm:table-cell text-stone-500 font-mono text-[11px]">
                      {doc.mime_type.split('/')[1] || doc.mime_type}
                    </td>

                    <td className="py-3 px-4 font-mono text-stone-700">
                      <span className="inline-flex items-center gap-1">
                        <Layers className="w-3 h-3 text-stone-400" />
                        {doc.chunk_count || 0}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      <span
                        className={cn(
                          'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border font-mono',
                          isReady
                            ? 'bg-[#F4F6F0] text-[#5F7143] border-[#DCE4D0]'
                            : 'bg-[#FDF9F2] text-[#C07D32] border-[#F5E5CF]'
                        )}
                      >
                        {isReady ? (
                          <CheckCircle2 className="w-3 h-3" />
                        ) : (
                          <Clock className="w-3 h-3" />
                        )}
                        {doc.status.toUpperCase()}
                      </span>
                    </td>

                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => setSelectedDoc(doc)}
                          className="p-1.5 rounded text-stone-500 hover:text-stone-900 hover:bg-stone-100 transition-colors cursor-pointer"
                          title="Inspect metadata"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(doc.document_id)}
                          disabled={deletingId === doc.document_id}
                          className="p-1.5 rounded text-stone-400 hover:text-[#BA3C2A] hover:bg-stone-100 transition-colors cursor-pointer"
                          title="Delete document and chunk vectors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Document Detail Preview Modal */}
      {selectedDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/30 backdrop-blur-xs">
          <div className="bg-white border border-[#E7E2DA] rounded-2xl p-6 max-w-lg w-full shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-[#C25E43]" />
                <h3 className="font-semibold text-stone-900 text-sm truncate">
                  {selectedDoc.name}
                </h3>
              </div>
              <button
                onClick={() => setSelectedDoc(null)}
                className="p-1 text-stone-400 hover:text-stone-700 rounded-md"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2 text-xs font-mono bg-[#FAF8F5] p-3.5 rounded-xl border border-[#E7E2DA]">
              <div className="flex justify-between">
                <span className="text-stone-500">Document ID:</span>
                <span className="text-stone-800 select-all">{selectedDoc.document_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-stone-500">MIME Type:</span>
                <span className="text-stone-800">{selectedDoc.mime_type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-stone-500">Total Chunks:</span>
                <span className="text-stone-800 font-bold">{selectedDoc.chunk_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-stone-500">SHA-256 Digest:</span>
                <span className="text-stone-800 truncate max-w-[200px] select-all">{selectedDoc.sha256}</span>
              </div>
            </div>

            <div className="text-xs text-stone-600 leading-relaxed font-sans">
              This document is indexed in the active session. When questions are asked, hybrid search retrieves relevant chunks with dense vector embeddings and reranking.
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedDoc(null)}
                className="px-4 py-1.5 rounded-xl bg-stone-900 text-white hover:bg-stone-800 text-xs font-medium cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

