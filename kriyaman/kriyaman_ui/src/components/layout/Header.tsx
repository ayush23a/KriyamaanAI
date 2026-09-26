'use client';

import React, { useState } from 'react';
import {
  Menu,
  Activity,
  Globe,
  Database,
  Check,
  Edit2,
  Sparkles,
  Files,
} from 'lucide-react';
import { AppNavView } from '../../types';
import { cn } from '../../lib/utils';

interface HeaderProps {
  currentView: AppNavView;
  sessionTitle: string;
  onUpdateSessionTitle?: (newTitle: string) => void;
  onToggleInspector?: () => void;
  isInspectorOpen?: boolean;
  onToggleArtifacts?: () => void;
  isArtifactsOpen?: boolean;
  onOpenMobileSidebar?: () => void;
  documentCount?: number;
  enableWebSearch?: boolean;
  hasRunMetrics?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  currentView,
  sessionTitle,
  onUpdateSessionTitle,
  onToggleInspector,
  isInspectorOpen = false,
  onToggleArtifacts,
  isArtifactsOpen = false,
  onOpenMobileSidebar,
  documentCount = 0,
  enableWebSearch = false,
  hasRunMetrics = false,
}) => {
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [titleInput, setTitleInput] = useState(sessionTitle);

  const handleSaveTitle = () => {
    if (titleInput.trim() && onUpdateSessionTitle) {
      onUpdateSessionTitle(titleInput.trim());
    }
    setIsEditingTitle(false);
  };

  const getHeading = () => {
    switch (currentView) {
      case 'knowledge':
        return 'Knowledge Base & Ingestion';
      case 'memory':
        return 'Explicit Long-term Memory';
      case 'settings':
        return 'Settings & Agent Configuration';
      default:
        return sessionTitle || 'New Research Session';
    }
  };

  return (
    <header className="h-14 border-b border-[#E7E2DA] bg-white flex items-center justify-between px-4 sm:px-6 flex-shrink-0 z-10">
      {/* Left side: Hamburger (mobile) + Title */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onOpenMobileSidebar}
          className="md:hidden p-1.5 rounded-lg text-stone-600 hover:text-stone-900 hover:bg-[#F2EDE4] transition-colors cursor-pointer"
          title="Open sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Title display or inline editing */}
        {currentView === 'chat' && isEditingTitle ? (
          <div className="flex items-center gap-1.5">
            <input
              type="text"
              value={titleInput}
              onChange={(e) => setTitleInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSaveTitle()}
              autoFocus
              className="px-2 py-1 text-sm font-medium text-stone-900 border border-[#C25E43] rounded-md focus:outline-none focus:ring-1 focus:ring-[#C25E43]"
            />
            <button
              onClick={handleSaveTitle}
              className="p-1 text-[#5F7143] hover:bg-[#F4F6F0] rounded"
            >
              <Check className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2 min-w-0 group">
            <h1 className="text-sm sm:text-base font-semibold text-stone-900 truncate tracking-tight font-sans">
              {getHeading()}
            </h1>
            {currentView === 'chat' && (
              <button
                onClick={() => {
                  setTitleInput(sessionTitle);
                  setIsEditingTitle(true);
                }}
                className="opacity-0 group-hover:opacity-100 p-1 text-stone-400 hover:text-stone-700 transition-opacity"
                title="Rename conversation"
              >
                <Edit2 className="w-3 h-3" />
              </button>
            )}
          </div>
        )}
      </div>

      {/* Right side: Knowledge scope pill + Inspector toggle */}
      <div className="flex items-center gap-2.5">
        {currentView === 'chat' && (
          <>
            {/* Artifacts Drawer Toggle Button (Replaces static docs pill) */}
            <button
              type="button"
              onClick={onToggleArtifacts}
              className={cn(
                'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium transition-colors cursor-pointer',
                isArtifactsOpen
                  ? 'bg-[#FDF6F3] text-[#C25E43] border-[#F1D6CE] shadow-2xs'
                  : 'bg-[#FAF8F5] text-stone-700 border-[#E7E2DA] hover:text-stone-900 hover:border-stone-400'
              )}
              title="View session artifacts & uploaded documents"
            >
              <Files className="w-3.5 h-3.5 text-[#C25E43]" />
              {/* Artifacts icon */}
              <span className="ml-0.5 px-1.5 py-0.2 rounded-full bg-stone-200/80 text-[10px] font-mono text-stone-700 font-semibold">
                {documentCount}
              </span>
            </button>

            {/* Web fallback indicator if active */}
            {enableWebSearch && (
              <div className="hidden md:flex items-center gap-1 px-2 py-1 rounded-lg bg-[#FAF8F5] border border-[#E7E2DA] text-xs font-mono text-[#C25E43]">
                <Globe className="w-3 h-3" />
                <span>Web fallback</span>
              </div>
            )}

            {/* Inspector Toggle Button (Icon-only professional design) */}
            {onToggleInspector && (
              <button
                type="button"
                onClick={onToggleInspector}
                className={cn(
                  'flex items-center justify-center p-2 rounded-lg border transition-colors cursor-pointer relative',
                  isInspectorOpen
                    ? 'bg-[#FDF6F3] text-[#C25E43] border-[#F1D6CE] shadow-2xs'
                    : 'bg-white text-stone-600 border-[#E7E2DA] hover:text-stone-900 hover:border-stone-400'
                )}
                title="Execution Inspector"
                aria-label="Execution Inspector"
              >
                <Activity className="w-3.5 h-3.5 text-[#C25E43]" />
                {hasRunMetrics && !isInspectorOpen && (
                  <span className="w-1.5 h-1.5 rounded-full bg-[#C25E43] absolute top-1 right-1" />
                )}
              </button>
            )}
          </>
        )}
      </div>
    </header>
  );
};

