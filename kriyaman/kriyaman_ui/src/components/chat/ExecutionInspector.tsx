'use client';

import React, { useState, useEffect } from 'react';
import {
  X,
  Activity,
  Cpu,
  Clock,
  Coins,
  ShieldCheck,
  Database,
  Repeat,
  Layers,
  FileCheck2,
  AlertCircle,
  Zap,
} from 'lucide-react';
import { ChatMessage, RunEvent } from '../../types';
import { getRunEvents } from '../../lib/api';
import { formatCost, formatLatency, formatTokens } from '../../lib/utils';

interface ExecutionInspectorProps {
  message: ChatMessage | null;
  onClose: () => void;
}

export const ExecutionInspector: React.FC<ExecutionInspectorProps> = ({ message, onClose }) => {
  const [activeTab, setActiveTab] = useState<'metrics' | 'events' | 'assessment'>('metrics');
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(false);

  useEffect(() => {
    if (message?.runId) {
      setLoadingEvents(true);
      getRunEvents(message.runId)
        .then((evs) => setEvents(evs))
        .catch(() => setEvents([]))
        .finally(() => setLoadingEvents(false));
    } else {
      setEvents(message?.events || []);
    }
  }, [message?.runId, message?.events]);

  if (!message) return null;

  const metrics = message.metrics || {};
  const budgets = message.budgets;
  const assessment = message.assessment;
  const evidence = message.evidence || [];
  const citations = message.citations || [];

  const citedCount = evidence.filter((e) => citations.includes(e.evidence_id)).length;
  const vectorSources = evidence.filter((e) => e.retrieval_method !== 'web');
  const webSources = evidence.filter((e) => e.retrieval_method === 'web');

  return (
    <aside className="w-full sm:w-[380px] lg:w-[400px] h-full flex flex-col border-l border-[#E7E2DA] bg-[#FAF8F5] text-stone-900 shadow-sm z-20">
      {/* Inspector Header */}
      <div className="flex items-center justify-between px-4 py-3.5 border-b border-[#E7E2DA] bg-white">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#C25E43]" />
          <h3 className="text-sm font-semibold text-stone-900 font-sans">Execution Inspector</h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-md text-stone-400 hover:text-stone-700 hover:bg-stone-100 transition-colors cursor-pointer"
          title="Close inspector"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center border-b border-[#E7E2DA] bg-[#F7F4EE] px-4 text-xs font-medium text-stone-600">
        <button
          onClick={() => setActiveTab('metrics')}
          className={`py-2.5 px-2 border-b-2 transition-colors cursor-pointer ${
            activeTab === 'metrics'
              ? 'border-[#C25E43] text-[#C25E43] font-semibold'
              : 'border-transparent hover:text-stone-900'
          }`}
        >
          Telemetry
        </button>
        <button
          onClick={() => setActiveTab('events')}
          className={`py-2.5 px-2 border-b-2 transition-colors cursor-pointer ${
            activeTab === 'events'
              ? 'border-[#C25E43] text-[#C25E43] font-semibold'
              : 'border-transparent hover:text-stone-900'
          }`}
        >
          Event Replay ({events.length})
        </button>
        {assessment && (
          <button
            onClick={() => setActiveTab('assessment')}
            className={`py-2.5 px-2 border-b-2 transition-colors cursor-pointer ${
              activeTab === 'assessment'
                ? 'border-[#C25E43] text-[#C25E43] font-semibold'
                : 'border-transparent hover:text-stone-900'
            }`}
          >
            Evidence Judge
          </button>
        )}
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
        {activeTab === 'metrics' && (
          <>
            {/* Run Identity & Status */}
            <div className="rounded-xl border border-[#E7E2DA] bg-white p-3.5 shadow-2xs space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-stone-500 font-medium">Terminal Gate Status</span>
                <span className="px-2 py-0.5 rounded font-mono font-medium text-[11px] bg-[#F4F6F0] text-[#5F7143] border border-[#DCE4D0]">
                  {message.status?.toUpperCase() || 'ANSWER'}
                </span>
              </div>
              {message.runId && (
                <div className="flex items-center justify-between text-[11px] pt-1 border-t border-[#E7E2DA]/60">
                  <span className="text-stone-500 font-mono">Run ID</span>
                  <span className="font-mono text-stone-700 select-all">{message.runId.slice(0, 16)}...</span>
                </div>
              )}
            </div>

            {/* Performance Grid */}
            <div className="grid grid-cols-2 gap-2.5">
              {/* Latency */}
              <div className="rounded-xl border border-[#E7E2DA] bg-white p-3 shadow-2xs">
                <div className="flex items-center gap-1.5 text-stone-500 mb-1">
                  <Clock className="w-3.5 h-3.5 text-[#C25E43]" />
                  <span className="font-medium">Total Latency</span>
                </div>
                <div className="text-base font-semibold font-mono text-stone-900">
                  {formatLatency(metrics.total_latency_ms)}
                </div>
                <span className="text-[10px] text-stone-400">Budget: {budgets?.max_latency_ms || 30000}ms</span>
              </div>

              {/* Cost */}
              <div className="rounded-xl border border-[#E7E2DA] bg-white p-3 shadow-2xs">
                <div className="flex items-center gap-1.5 text-stone-500 mb-1">
                  <Coins className="w-3.5 h-3.5 text-[#C07D32]" />
                  <span className="font-medium">Estimated Cost</span>
                </div>
                <div className="text-base font-semibold font-mono text-stone-900">
                  {formatCost(metrics.estimated_cost_usd)}
                </div>
                <span className="text-[10px] text-stone-400">USD per query</span>
              </div>

              {/* Tokens */}
              <div className="rounded-xl border border-[#E7E2DA] bg-white p-3 shadow-2xs">
                <div className="flex items-center gap-1.5 text-stone-500 mb-1">
                  <Cpu className="w-3.5 h-3.5 text-stone-600" />
                  <span className="font-medium">Prompt Tokens</span>
                </div>
                <div className="text-base font-semibold font-mono text-stone-900">
                  {formatTokens(metrics.prompt_tokens)}
                </div>
                <span className="text-[10px] text-stone-400">Completion: {formatTokens(metrics.completion_tokens)}</span>
              </div>

              {/* Cache */}
              <div className="rounded-xl border border-[#E7E2DA] bg-white p-3 shadow-2xs">
                <div className="flex items-center gap-1.5 text-stone-500 mb-1">
                  <Zap className="w-3.5 h-3.5 text-[#5F7143]" />
                  <span className="font-medium">Semantic Cache</span>
                </div>
                <div className="text-base font-semibold font-mono text-stone-900">
                  {metrics.cache_hit ? 'HIT' : 'MISS'}
                </div>
                <span className="text-[10px] text-stone-400">Redis / L1 In-Memory</span>
              </div>
            </div>

            {/* Retrieval & Tool Budget Telemetry */}
            <div className="rounded-xl border border-[#E7E2DA] bg-white p-3.5 shadow-2xs space-y-3">
              <div className="flex items-center gap-2 font-medium text-stone-800">
                <Repeat className="w-3.5 h-3.5 text-[#C25E43]" />
                <span>Agent Iterations & Budgets</span>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-stone-600">Retrieval Loops Used</span>
                  <span className="font-mono font-semibold text-stone-900">
                    1 / {budgets?.max_retrieval_iterations || 3}
                  </span>
                </div>
                <div className="w-full bg-[#F2EDE4] h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-[#C25E43] h-full rounded-full"
                    style={{ width: `${(1 / (budgets?.max_retrieval_iterations || 3)) * 100}%` }}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-stone-600">Tool Calls Dispatched</span>
                  <span className="font-mono font-semibold text-stone-900">
                    {metrics.tool_calls_count || 1} / {budgets?.max_tool_calls || 3}
                  </span>
                </div>
                <div className="w-full bg-[#F2EDE4] h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-[#5F7143] h-full rounded-full"
                    style={{
                      width: `${((metrics.tool_calls_count || 1) / (budgets?.max_tool_calls || 3)) * 100}%`,
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Acquisition Breakdown */}
            <div className="rounded-xl border border-[#E7E2DA] bg-white p-3.5 shadow-2xs space-y-2.5">
              <div className="flex items-center gap-2 font-medium text-stone-800">
                <Database className="w-3.5 h-3.5 text-[#C25E43]" />
                <span>Acquisition Sources ({evidence.length})</span>
              </div>

              <div className="divide-y divide-[#E7E2DA]/70 text-[11px]">
                <div className="flex items-center justify-between py-1.5">
                  <span className="text-stone-600">Local Vector Embeddings</span>
                  <span className="font-mono font-medium text-stone-900">{vectorSources.length} chunks</span>
                </div>
                <div className="flex items-center justify-between py-1.5">
                  <span className="text-stone-600">Web Search Fallback</span>
                  <span className="font-mono font-medium text-stone-900">{webSources.length} results</span>
                </div>
                <div className="flex items-center justify-between py-1.5">
                  <span className="text-stone-600">Verified & Cited by Gate</span>
                  <span className="font-mono font-medium text-[#5F7143]">{citedCount} items</span>
                </div>
              </div>
            </div>
          </>
        )}

        {activeTab === 'events' && (
          <div className="space-y-2.5">
            {loadingEvents ? (
              <div className="p-4 text-center text-stone-500">Loading structured events...</div>
            ) : events.length === 0 ? (
              <div className="p-4 text-center text-stone-500">No events recorded for this turn.</div>
            ) : (
              events.map((ev, i) => (
                <div key={i} className="p-3 rounded-lg border border-[#E7E2DA] bg-white space-y-1.5">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-mono font-bold text-[#C25E43]">
                      Step {ev.sequence || i + 1}
                    </span>
                    <span className="px-1.5 py-0.2 rounded bg-[#F2EDE4] font-mono text-stone-700">
                      {ev.event_type}
                    </span>
                  </div>
                  {ev.payload && Object.keys(ev.payload).length > 0 && (
                    <pre className="p-2 rounded bg-[#FAF8F5] border border-[#E7E2DA] overflow-x-auto text-[10px] text-stone-700 font-mono">
                      {JSON.stringify(ev.payload, null, 2)}
                    </pre>
                  )}
                  {ev.timestamp && (
                    <div className="text-[10px] text-stone-400">
                      {new Date(ev.timestamp).toLocaleTimeString()}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'assessment' && assessment && (
          <div className="rounded-xl border border-[#E7E2DA] bg-white p-3.5 space-y-3">
            <div className="flex items-center gap-2 font-medium text-stone-800">
              <ShieldCheck className="w-4 h-4 text-[#5F7143]" />
              <span>Evidence Judge Assessment</span>
            </div>
            <pre className="p-2.5 rounded-lg bg-[#FAF8F5] border border-[#E7E2DA] text-[11px] font-mono text-stone-800 overflow-x-auto">
              {JSON.stringify(assessment, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </aside>
  );
};

