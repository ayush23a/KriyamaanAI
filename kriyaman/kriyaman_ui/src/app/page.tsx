'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  AppNavView,
  ChatMessage,
  DocumentItem,
  EvidenceItem,
  HealthStatus,
  LocalSessionMeta,
  MemoryItem,
  RunEvent,
  UserSettings,
} from '../types';
import {
  checkHealth,
  createMemory,
  createRun,
  createSession,
  deleteDocument,
  deleteMemory,
  getRunEvents,
  getSession,
  listDocuments,
  listMemories,
  uploadDocument,
} from '../lib/api';
import {
  deleteLocalSession,
  getLocalSessions,
  getUserSettings,
  groupSessionsByDate,
  saveLocalSession,
  updateLocalSessionTitle,
} from '../lib/storage';
import { Sidebar } from '../components/layout/Sidebar';
import { Header } from '../components/layout/Header';
import { MessageList } from '../components/chat/MessageList';
import { Composer } from '../components/chat/Composer';
import { ExecutionInspector } from '../components/chat/ExecutionInspector';
import { KnowledgeView } from '../components/knowledge/KnowledgeView';
import { MemoryView } from '../components/memory/MemoryView';
import { SettingsView } from '../components/settings/SettingsView';

export default function AppPage() {
  // Navigation & View
  const [currentView, setCurrentView] = useState<AppNavView>('chat');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);

  // User Settings
  const [settings, setSettings] = useState<UserSettings>(getUserSettings());

  // Health
  const [health, setHealth] = useState<HealthStatus | null>(null);

  // Session & Conversations
  const [localSessions, setLocalSessions] = useState<LocalSessionMeta[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessionTitle, setSessionTitle] = useState<string>('New Research');

  // Chat Stream State
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [composerInitialQuery, setComposerInitialQuery] = useState('');
  const [selectedInspectorMessage, setSelectedInspectorMessage] = useState<ChatMessage | null>(null);

  // Knowledge & Documents
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isUploadingDoc, setIsUploadingDoc] = useState(false);

  // Memories
  const [memories, setMemories] = useState<MemoryItem[]>([]);

  // Abort control
  const activeAbortRef = useRef<boolean>(false);

  // ---------------------------------------------------------------------------
  // Initial Boot: Load Sessions & Health
  // ---------------------------------------------------------------------------
  useEffect(() => {
    // 1. Fetch Health
    checkHealth()
      .then((h) => setHealth(h))
      .catch(() =>
        setHealth({
          status: 'unhealthy',
          version: '1.0.0',
          dependencies: { api: 'unreachable' },
        })
      );

    // 2. Load Local Sessions
    const stored = getLocalSessions();
    setLocalSessions(stored);

    if (stored.length > 0) {
      const mostRecent = stored[0];
      setActiveSessionId(mostRecent.id);
      setSessionTitle(mostRecent.title || 'Research Workspace');
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Session Change: Fetch Session Turns, Docs & Memories from Backend
  // ---------------------------------------------------------------------------
  const loadSessionData = useCallback(async (sessionId: string) => {
    try {
      // Load session details (turns)
      const detail = await getSession(sessionId);
      if (detail && detail.turns) {
        const msgs: ChatMessage[] = [];
        detail.turns.forEach((t) => {
          // User message
          msgs.push({
            id: `usr-${t.turn_id}`,
            role: 'user',
            content: t.user_query,
            timestamp: new Date(t.created_at).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            }),
          });
          // Assistant message
          if (t.answer) {
            msgs.push({
              id: `ast-${t.turn_id}`,
              role: 'assistant',
              content: t.answer.answer_text,
              timestamp: new Date(t.created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              }),
              runId: t.run_id,
              citations: t.answer.citation_ids,
              status: t.status,
            });
          }
        });
        setChatMessages(msgs);
      }

      if (detail.title) {
        setSessionTitle(detail.title);
      }
    } catch {
      // Fallback: If session not on server yet, keep empty message stream
      setChatMessages([]);
    }

    // Load Documents for this session
    try {
      const docs = await listDocuments(sessionId);
      setDocuments(docs);
    } catch {
      setDocuments([]);
    }

    // Load Memories for this session principal
    try {
      const mems = await listMemories(sessionId);
      setMemories(mems);
    } catch {
      setMemories([]);
    }
  }, []);

  useEffect(() => {
    if (activeSessionId) {
      loadSessionData(activeSessionId);
    }
  }, [activeSessionId, loadSessionData]);

  // ---------------------------------------------------------------------------
  // Create / Switch Sessions
  // ---------------------------------------------------------------------------
  const handleNewSession = async () => {
    try {
      const newSess = await createSession('New Research');
      const meta: LocalSessionMeta = {
        id: newSess.session_id,
        title: newSess.title || 'New Research',
        createdAt: newSess.created_at,
        updatedAt: newSess.updated_at,
      };
      saveLocalSession(meta);
      setLocalSessions(getLocalSessions());
      setActiveSessionId(newSess.session_id);
      setSessionTitle('New Research');
      setChatMessages([]);
      setCurrentView('chat');
    } catch {
      // Client-side fallback ID if backend is offline
      const tempId = `sess-${Date.now()}`;
      const meta: LocalSessionMeta = {
        id: tempId,
        title: 'New Research',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      saveLocalSession(meta);
      setLocalSessions(getLocalSessions());
      setActiveSessionId(tempId);
      setSessionTitle('New Research');
      setChatMessages([]);
      setCurrentView('chat');
    }
  };

  const handleSelectSession = (id: string) => {
    setActiveSessionId(id);
    const item = localSessions.find((s) => s.id === id);
    if (item) setSessionTitle(item.title);
  };

  const handleDeleteSession = (id: string) => {
    deleteLocalSession(id);
    const updated = getLocalSessions();
    setLocalSessions(updated);
    if (activeSessionId === id) {
      if (updated.length > 0) {
        setActiveSessionId(updated[0].id);
        setSessionTitle(updated[0].title);
      } else {
        setActiveSessionId(null);
        setSessionTitle('New Research');
        setChatMessages([]);
      }
    }
  };

  const handleUpdateSessionTitle = (newTitle: string) => {
    setSessionTitle(newTitle);
    if (activeSessionId) {
      updateLocalSessionTitle(activeSessionId, newTitle);
      setLocalSessions(getLocalSessions());
    }
  };

  // ---------------------------------------------------------------------------
  // Query Execution (Chat Flow)
  // ---------------------------------------------------------------------------
  const handleSendMessage = async (queryText: string, enableWeb: boolean) => {
    activeAbortRef.current = false;
    let sessionId = activeSessionId;

    // Create session if none exists
    if (!sessionId) {
      try {
        const titleExcerpt = queryText.length > 32 ? `${queryText.slice(0, 32)}...` : queryText;
        const newSess = await createSession(titleExcerpt);
        sessionId = newSess.session_id;
        const meta: LocalSessionMeta = {
          id: newSess.session_id,
          title: titleExcerpt,
          createdAt: newSess.created_at,
          updatedAt: newSess.updated_at,
        };
        saveLocalSession(meta);
        setLocalSessions(getLocalSessions());
        setActiveSessionId(newSess.session_id);
        setSessionTitle(titleExcerpt);
      } catch {
        sessionId = `sess-${Date.now()}`;
        setActiveSessionId(sessionId);
      }
    }

    // 1. Append User Message
    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      role: 'user',
      content: queryText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    // 2. Append Assistant streaming placeholder with progressive live statuses
    const assistantMsgId = `ast-${Date.now()}`;
    const assistantPlaceholder: ChatMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      isStreaming: true,
      liveStatus: 'Searching your knowledge...',
    };

    setChatMessages((prev) => [...prev, userMsg, assistantPlaceholder]);
    setIsStreaming(true);

    // Live status progression interval
    const statusSteps = [
      'Searching your knowledge...',
      enableWeb ? 'Searching the web...' : 'Scanning chunk embeddings...',
      'Checking evidence & citations...',
      'Preparing answer...',
    ];
    let stepIndex = 0;
    const statusInterval = setInterval(() => {
      stepIndex = (stepIndex + 1) % statusSteps.length;
      if (!activeAbortRef.current) {
        setChatMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? { ...msg, liveStatus: statusSteps[stepIndex] }
              : msg
          )
        );
      }
    }, 1800);

    try {
      // 3. Dispatch run to backend
      const runResult = await createRun(sessionId, {
        query: queryText,
        enable_web_search: enableWeb,
        response_mode: settings.responseMode,
        budgets: settings.budgets,
      });

      clearInterval(statusInterval);

      if (activeAbortRef.current) return;

      // Extract result components
      const answerText = runResult.answer?.answer_text || 'No answer generated by model.';
      const citationIds = runResult.answer?.citation_ids || [];
      const evidence = runResult.evidence || [];
      const metrics = runResult.usage || {};
      const status = runResult.status;

      // Fetch structured events for replay
      let events: RunEvent[] = [];
      try {
        events = await getRunEvents(runResult.run_id);
      } catch {}

      const completedMsg: ChatMessage = {
        id: assistantMsgId,
        role: 'assistant',
        content: answerText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        runId: runResult.run_id,
        citations: citationIds,
        evidence: evidence,
        metrics: metrics,
        budgets: settings.budgets,
        status: status,
        assessment: runResult.evidence_assessment,
        events: events,
        isStreaming: false,
      };

      setChatMessages((prev) =>
        prev.map((msg) => (msg.id === assistantMsgId ? completedMsg : msg))
      );

      // Update inspector target
      setSelectedInspectorMessage(completedMsg);
      if (settings.showTelemetryByDefault) {
        setIsInspectorOpen(true);
      }

      // Update local storage preview
      if (sessionId) {
        const item = localSessions.find((s) => s.id === sessionId);
        saveLocalSession({
          id: sessionId,
          title: item?.title || (queryText.length > 32 ? `${queryText.slice(0, 32)}...` : queryText),
          createdAt: item?.createdAt || new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          previewText: answerText.slice(0, 60),
        });
        setLocalSessions(getLocalSessions());
      }
    } catch (err: unknown) {
      clearInterval(statusInterval);
      const errMessage = err instanceof Error ? err.message : String(err);

      setChatMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? {
                ...msg,
                content: `Unable to complete query: ${errMessage}. Please verify the FastAPI backend status in Settings.`,
                isStreaming: false,
                status: 'error',
              }
            : msg
        )
      );
    } finally {
      setIsStreaming(false);
    }
  };

  const handleStopGeneration = () => {
    activeAbortRef.current = true;
    setIsStreaming(false);
    setChatMessages((prev) =>
      prev.map((msg) => (msg.isStreaming ? { ...msg, isStreaming: false, liveStatus: undefined } : msg))
    );
  };

  const handleRegenerate = (content: string) => {
    // Find preceding user query
    const index = chatMessages.findIndex((m) => m.content === content);
    if (index > 0) {
      const precedingUserMsg = chatMessages[index - 1];
      if (precedingUserMsg && precedingUserMsg.role === 'user') {
        handleSendMessage(precedingUserMsg.content, settings.enableWebFallback);
      }
    }
  };

  const handleEditMessage = (content: string) => {
    setComposerInitialQuery(content);
  };

  const handleOpenInspector = (msg: ChatMessage) => {
    setSelectedInspectorMessage(msg);
    setIsInspectorOpen(true);
  };

  // ---------------------------------------------------------------------------
  // Document Operations
  // ---------------------------------------------------------------------------
  const handleUploadDocument = async (file: File) => {
    let sessId = activeSessionId;
    if (!sessId) {
      const newSess = await createSession('Document Ingestion');
      sessId = newSess.session_id;
      setActiveSessionId(sessId);
      saveLocalSession({
        id: sessId,
        title: 'Document Ingestion',
        createdAt: newSess.created_at,
        updatedAt: newSess.updated_at,
      });
      setLocalSessions(getLocalSessions());
    }

    setIsUploadingDoc(true);
    try {
      const doc = await uploadDocument(sessId, file);
      setDocuments((prev) => [doc, ...prev]);

      // Inform user in chat thread if in chat view
      const confirmMsg: ChatMessage = {
        id: `sys-${Date.now()}`,
        role: 'assistant',
        content: `Ingested **${doc.name}** into session knowledge. Chunked into **${doc.chunk_count}** vectors. You can now ask questions grounded in this document.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setChatMessages((prev) => [...prev, confirmMsg]);
    } finally {
      setIsUploadingDoc(false);
    }
  };

  const handleDeleteDocument = async (documentId: string) => {
    await deleteDocument(documentId);
    setDocuments((prev) => prev.filter((d) => d.document_id !== documentId));
  };

  // ---------------------------------------------------------------------------
  // Memory Operations
  // ---------------------------------------------------------------------------
  const handleCreateMemory = async (content: string, kind: string) => {
    if (!activeSessionId) return;
    const item = await createMemory(activeSessionId, content, kind);
    setMemories((prev) => [item, ...prev]);
  };

  const handleDeleteMemory = async (memoryId: string) => {
    await deleteMemory(memoryId);
    setMemories((prev) => prev.filter((m) => m.memory_id !== memoryId));
  };

  // Grouped sessions for sidebar
  const groupedSessions = groupSessionsByDate(localSessions);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#FAF8F5] text-stone-900">
      {/* 1. Left Collapsible Navigation Sidebar */}
      <Sidebar
        currentView={currentView}
        onViewChange={setCurrentView}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onNewSession={handleNewSession}
        onDeleteSession={handleDeleteSession}
        groupedSessions={groupedSessions}
        health={health}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
      />

      {/* 2. Main Workspace Layout */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden relative">
        {/* Workspace Top Header */}
        <Header
          currentView={currentView}
          sessionTitle={sessionTitle}
          onUpdateSessionTitle={handleUpdateSessionTitle}
          onToggleInspector={() => setIsInspectorOpen(!isInspectorOpen)}
          isInspectorOpen={isInspectorOpen}
          onOpenMobileSidebar={() => setIsMobileSidebarOpen(true)}
          documentCount={documents.length}
          enableWebSearch={settings.enableWebFallback}
          hasRunMetrics={!!selectedInspectorMessage}
        />

        {/* Dynamic Route View */}
        <div className="flex-1 flex min-h-0 overflow-hidden relative">
          <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden bg-[#FAF8F5]">
            {/* View: Chat (Conversation visually dominates!) */}
            {currentView === 'chat' && (
              <div className="flex-1 flex flex-col h-full overflow-hidden">
                <MessageList
                  messages={chatMessages}
                  onRegenerate={handleRegenerate}
                  onEditMessage={handleEditMessage}
                  onOpenInspector={handleOpenInspector}
                  onPromptSelect={(prompt) => handleSendMessage(prompt, settings.enableWebFallback)}
                />
                <Composer
                  onSendMessage={handleSendMessage}
                  onStopGeneration={handleStopGeneration}
                  onUploadFile={handleUploadDocument}
                  onOpenSettings={() => setCurrentView('settings')}
                  isStreaming={isStreaming}
                  initialQuery={composerInitialQuery}
                  defaultEnableWeb={settings.enableWebFallback}
                  documentCount={documents.length}
                />
              </div>
            )}

            {/* View: Knowledge */}
            {currentView === 'knowledge' && (
              <KnowledgeView
                documents={documents}
                onUploadDocument={handleUploadDocument}
                onDeleteDocument={handleDeleteDocument}
                isUploading={isUploadingDoc}
                onBack={() => setCurrentView('chat')}
              />
            )}

            {/* View: Memory */}
            {currentView === 'memory' && (
              <MemoryView
                memories={memories}
                onCreateMemory={handleCreateMemory}
                onDeleteMemory={handleDeleteMemory}
                onBack={() => setCurrentView('chat')}
              />
            )}

            {/* View: Settings */}
            {currentView === 'settings' && (
              <SettingsView
                settings={settings}
                onUpdateSettings={setSettings}
                onBack={() => setCurrentView('chat')}
              />
            )}
          </main>

          {/* 3. Optional Right Execution Inspector */}
          {isInspectorOpen && (
            <ExecutionInspector
              message={selectedInspectorMessage || chatMessages.filter((m) => m.role === 'assistant').pop() || null}
              onClose={() => setIsInspectorOpen(false)}
            />
          )}
        </div>
      </div>
    </div>
  );
}
