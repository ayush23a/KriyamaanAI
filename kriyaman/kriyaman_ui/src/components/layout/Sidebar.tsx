'use client';

import React, { useState } from 'react';
import {
  Plus,
  Search,
  MessageSquare,
  FileText,
  Brain,
  Settings,
  ChevronLeft,
  ChevronRight,
  Trash2,
  Activity,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  X,
} from 'lucide-react';
import { AppNavView, HealthStatus, LocalSessionMeta } from '../../types';
import { GroupedSessions } from '../../lib/storage';
import { cn } from '../../lib/utils';

interface SidebarProps {
  currentView: AppNavView;
  onViewChange: (view: AppNavView) => void;
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string) => void;
  groupedSessions: GroupedSessions;
  health: HealthStatus | null;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  onViewChange,
  activeSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  groupedSessions,
  health,
  isCollapsed,
  onToggleCollapse,
  isMobileOpen,
  onCloseMobile,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [showHealthDetails, setShowHealthDetails] = useState(false);

  // Filter sessions by search query
  const filterList = (list: LocalSessionMeta[]) => {
    if (!searchQuery.trim()) return list;
    const q = searchQuery.toLowerCase();
    return list.filter(
      (s) => s.title.toLowerCase().includes(q) || (s.previewText && s.previewText.toLowerCase().includes(q))
    );
  };

  const filteredToday = filterList(groupedSessions.today);
  const filteredYesterday = filterList(groupedSessions.yesterday);
  const filteredOlder = filterList(groupedSessions.older);

  const isHealthy = health?.status === 'healthy';
  const isDegraded = health?.status === 'degraded';

  const sidebarContent = (
    <div className="flex flex-col h-full bg-[#FAF8F5] border-r border-[#E7E2DA] select-none">
      {/* Brand Header */}
      <div className="flex items-center justify-between px-3.5 py-4 border-b border-[#E7E2DA]/80">
        {!isCollapsed ? (
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-xl bg-[#FDF6F3] border border-[#F1D6CE] flex items-center justify-center text-[#C25E43] font-serif font-bold text-sm shadow-xs flex-shrink-0">
              K
            </div>
            <div className="flex flex-col min-w-0">
              <span className="font-semibold text-stone-900 tracking-tight text-sm truncate font-sans">
                Kriyamaan
              </span>
              <span className="text-[11px] text-stone-500 truncate">
                Agentic RAG Workspace
              </span>
            </div>
          </div>
        ) : (
          <div className="w-8 h-8 mx-auto rounded-xl bg-[#FDF6F3] border border-[#F1D6CE] flex items-center justify-center text-[#C25E43] font-serif font-bold text-sm shadow-xs">
            K
          </div>
        )}

        {/* Desktop Collapse Toggle */}
        <button
          onClick={onToggleCollapse}
          className="hidden md:flex p-1 rounded-md text-stone-400 hover:text-stone-700 hover:bg-[#F2EDE4] transition-colors cursor-pointer"
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>

        {/* Mobile Close Button */}
        <button
          onClick={onCloseMobile}
          className="flex md:hidden p-1 rounded-md text-stone-400 hover:text-stone-700 hover:bg-[#F2EDE4] transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* New Chat Button */}
      <div className="p-3">
        <button
          onClick={onNewSession}
          className={cn(
            'w-full flex items-center justify-center gap-2 rounded-xl py-2 px-3 transition-all cursor-pointer shadow-xs font-medium text-xs',
            'bg-white border border-[#E7E2DA] text-stone-900 hover:border-[#C25E43] hover:text-[#C25E43] hover:bg-[#FDF6F3]'
          )}
          title="Start a new research chat (⌘N)"
        >
          <Plus className="w-4 h-4 text-[#C25E43]" />
          {!isCollapsed && <span>New Chat</span>}
        </button>
      </div>

      {/* Search Input (When expanded) */}
      {!isCollapsed && (
        <div className="px-3 pb-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-stone-400 absolute left-2.5 top-2.5 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search conversations..."
              className="w-full pl-8 pr-3 py-1.5 rounded-lg text-xs bg-white border border-[#E7E2DA] placeholder:text-stone-400 text-stone-900 focus:outline-none focus:border-[#C25E43]"
            />
          </div>
        </div>
      )}

      {/* Conversations List (Scrollable) */}
      <div className="flex-1 overflow-y-auto px-2 py-1 space-y-4 text-xs">
        {!isCollapsed ? (
          <>
            {/* Today */}
            {filteredToday.length > 0 && (
              <div>
                <div className="px-2.5 py-1 text-[10px] font-semibold text-stone-600 uppercase tracking-wider">
                  Today
                </div>
                <div className="space-y-0.5 mt-0.5">
                  {filteredToday.map((sess) => (
                    <SessionItem
                      key={sess.id}
                      session={sess}
                      isActive={activeSessionId === sess.id && currentView === 'chat'}
                      onSelect={() => {
                        onSelectSession(sess.id);
                        onViewChange('chat');
                        onCloseMobile();
                      }}
                      onDelete={() => onDeleteSession(sess.id)}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Yesterday */}
            {filteredYesterday.length > 0 && (
              <div>
                <div className="px-2.5 py-1 text-[10px] font-semibold text-stone-600 uppercase tracking-wider">
                  Yesterday
                </div>
                <div className="space-y-0.5 mt-0.5">
                  {filteredYesterday.map((sess) => (
                    <SessionItem
                      key={sess.id}
                      session={sess}
                      isActive={activeSessionId === sess.id && currentView === 'chat'}
                      onSelect={() => {
                        onSelectSession(sess.id);
                        onViewChange('chat');
                        onCloseMobile();
                      }}
                      onDelete={() => onDeleteSession(sess.id)}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Older */}
            {filteredOlder.length > 0 && (
              <div>
                <div className="px-2.5 py-1 text-[10px] font-semibold text-stone-600 uppercase tracking-wider">
                  Older
                </div>
                <div className="space-y-0.5 mt-0.5">
                  {filteredOlder.map((sess) => (
                    <SessionItem
                      key={sess.id}
                      session={sess}
                      isActive={activeSessionId === sess.id && currentView === 'chat'}
                      onSelect={() => {
                        onSelectSession(sess.id);
                        onViewChange('chat');
                        onCloseMobile();
                      }}
                      onDelete={() => onDeleteSession(sess.id)}
                    />
                  ))}
                </div>
              </div>
            )}

            {filteredToday.length === 0 &&
              filteredYesterday.length === 0 &&
              filteredOlder.length === 0 && (
                <div className="px-3 py-6 text-center text-stone-600">
                  <p className="text-xs">No conversations found.</p>
                </div>
              )}
          </>
        ) : (
          <div className="flex flex-col items-center py-2 space-y-2">
            <button
              onClick={() => {
                onViewChange('chat');
                onCloseMobile();
              }}
              className={cn(
                'p-2 rounded-xl transition-colors cursor-pointer',
                currentView === 'chat' ? 'bg-[#FDF6F3] text-[#C25E43]' : 'text-stone-600 hover:bg-[#F2EDE4]'
              )}
              title="Conversations"
            >
              <MessageSquare className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Navigation Footer (Knowledge, Memory, Settings, Health) */}
      <div className="p-2 border-t border-[#E7E2DA]/80 bg-[#FAF8F5] space-y-1 text-xs">
        {/* Knowledge Link */}
        <button
          onClick={() => {
            onViewChange('knowledge');
            onCloseMobile();
          }}
          className={cn(
            'w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg font-medium transition-colors cursor-pointer',
            currentView === 'knowledge'
              ? 'bg-[#FDF6F3] text-[#C25E43]'
              : 'text-stone-700 hover:bg-[#F2EDE4] hover:text-stone-900',
            isCollapsed && 'justify-center px-0'
          )}
          title="Document Library & Ingestion"
        >
          <FileText className="w-4 h-4 flex-shrink-0" />
          {!isCollapsed && <span>Knowledge</span>}
        </button>

        {/* Memory Link */}
        <button
          onClick={() => {
            onViewChange('memory');
            onCloseMobile();
          }}
          className={cn(
            'w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg font-medium transition-colors cursor-pointer',
            currentView === 'memory'
              ? 'bg-[#FDF6F3] text-[#C25E43]'
              : 'text-stone-700 hover:bg-[#F2EDE4] hover:text-stone-900',
            isCollapsed && 'justify-center px-0'
          )}
          title="Explicit Long-Term Memory"
        >
          <Brain className="w-4 h-4 flex-shrink-0" />
          {!isCollapsed && <span>Memory</span>}
        </button>

        {/* Settings Link */}
        <button
          onClick={() => {
            onViewChange('settings');
            onCloseMobile();
          }}
          className={cn(
            'w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg font-medium transition-colors cursor-pointer',
            currentView === 'settings'
              ? 'bg-[#FDF6F3] text-[#C25E43]'
              : 'text-stone-700 hover:bg-[#F2EDE4] hover:text-stone-900',
            isCollapsed && 'justify-center px-0'
          )}
          title="Preferences & Advanced Agent Controls"
        >
          <Settings className="w-4 h-4 flex-shrink-0" />
          {!isCollapsed && <span>Settings</span>}
        </button>

        {/* Backend Health Pill */}
        <div className="pt-2">
          <div
            onClick={() => setShowHealthDetails(!showHealthDetails)}
            className={cn(
              'flex items-center gap-2 px-2.5 py-1.5 rounded-lg border text-[11px] font-mono cursor-pointer transition-colors',
              isHealthy
                ? 'bg-[#F4F6F0] text-[#5F7143] border-[#DCE4D0]'
                : isDegraded
                ? 'bg-[#FDF9F2] text-[#C07D32] border-[#F5E5CF]'
                : 'bg-[#FCF3F2] text-[#BA3C2A] border-[#F7D5D1]',
              isCollapsed && 'justify-center px-1'
            )}
            title="Backend Health Status (Click to inspect dependencies)"
          >
            <span
              className={cn(
                'w-2 h-2 rounded-full flex-shrink-0',
                isHealthy ? 'bg-[#5F7143]' : isDegraded ? 'bg-[#C07D32]' : 'bg-[#BA3C2A]'
              )}
            />
            {!isCollapsed && (
              <span className="truncate">
                {isHealthy ? 'API Healthy' : isDegraded ? 'Degraded' : 'Unreachable'}
              </span>
            )}
          </div>

          {/* Health Popover */}
          {showHealthDetails && !isCollapsed && health && (
            <div className="mt-1.5 p-2.5 rounded-lg border border-[#E7E2DA] bg-white shadow-sm text-[11px] font-mono space-y-1">
              <div className="font-semibold text-stone-800 text-[10px] uppercase">
                v{health.version} Services
              </div>
              {Object.entries(health.dependencies || {}).map(([dep, st]) => (
                <div key={dep} className="flex items-center justify-between text-stone-600">
                  <span>{dep}:</span>
                  <span className={st === 'healthy' ? 'text-[#5F7143]' : 'text-[#C07D32]'}>
                    {st}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <nav
        aria-label="Main Navigation"
        className={cn(
          'hidden md:block h-full transition-all duration-200 flex-shrink-0',
          isCollapsed ? 'w-16' : 'w-[270px]'
        )}
      >
        {sidebarContent}
      </nav>

      {/* Mobile Drawer Overlay */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div
            className="fixed inset-0 bg-stone-900/30 backdrop-blur-xs transition-opacity"
            onClick={onCloseMobile}
          />
          <nav aria-label="Mobile Navigation" className="relative w-[280px] h-full z-10 animate-in slide-in-from-left duration-200">
            {sidebarContent}
          </nav>
        </div>
      )}
    </>
  );
};

interface SessionItemProps {
  session: LocalSessionMeta;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}

const SessionItem: React.FC<SessionItemProps> = ({ session, isActive, onSelect, onDelete }) => {
  return (
    <div
      onClick={onSelect}
      className={cn(
        'group flex items-center justify-between px-2.5 py-2 rounded-lg cursor-pointer transition-colors text-xs',
        isActive
          ? 'bg-white border border-[#E7E2DA] text-stone-900 font-medium shadow-2xs'
          : 'text-stone-700 hover:bg-[#F2EDE4]/70 hover:text-stone-900'
      )}
    >
      <div className="flex items-center gap-2 min-w-0 pr-1">
        <MessageSquare className={cn('w-3.5 h-3.5 flex-shrink-0', isActive ? 'text-[#C25E43]' : 'text-stone-400')} />
        <span className="truncate">{session.title || 'Untitled Session'}</span>
      </div>

      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        className="opacity-0 group-hover:opacity-100 p-1 text-stone-400 hover:text-[#BA3C2A] rounded transition-opacity"
        title="Delete conversation"
      >
        <Trash2 className="w-3 h-3" />
      </button>
    </div>
  );
};

