'use client';

import React, { useState } from 'react';
import {
  Settings,
  Sliders,
  Terminal,
  Database,
  Brain,
  Palette,
  Globe,
  Save,
  Check,
  RotateCcw,
  Sparkles,
  ArrowLeft,
} from 'lucide-react';
import { UserSettings } from '../../types';
import { DEFAULT_SETTINGS, saveUserSettings } from '../../lib/storage';
import { cn } from '../../lib/utils';

interface SettingsViewProps {
  settings: UserSettings;
  onUpdateSettings: (newSettings: UserSettings) => void;
  onBack?: () => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ settings, onUpdateSettings, onBack }) => {
  const [activeTab, setActiveTab] = useState<'general' | 'appearance' | 'agent' | 'developer'>('general');
  const [formData, setFormData] = useState<UserSettings>(settings);
  const [savedNotice, setSavedNotice] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    const updated = saveUserSettings(formData);
    onUpdateSettings(updated);
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 2500);
  };

  const handleResetDefaults = () => {
    setFormData(DEFAULT_SETTINGS);
    const updated = saveUserSettings(DEFAULT_SETTINGS);
    onUpdateSettings(updated);
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 2500);
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-8 max-w-4xl mx-auto w-full space-y-6">
      <div className="flex items-center justify-between">
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
              Settings & Agent Configuration
            </h2>
            <p className="text-xs sm:text-sm text-stone-600 mt-1">
              Customize connection parameters, warm editorial typography, response modes, and monotonic execution budgets.
            </p>
          </div>
        </div>

        {savedNotice && (
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#F4F6F0] text-[#5F7143] border border-[#DCE4D0] text-xs font-medium animate-in fade-in">
            <Check className="w-3.5 h-3.5" />
            <span>Settings saved</span>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-[#E7E2DA] pb-2 text-xs font-medium">
        {[
          { id: 'general', label: 'General & API', icon: Globe },
          { id: 'appearance', label: 'Editorial Theme', icon: Palette },
          { id: 'agent', label: 'Agent & Budgets', icon: Sliders },
          { id: 'developer', label: 'Developer Mode', icon: Terminal },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-2 rounded-lg transition-colors cursor-pointer',
                activeTab === tab.id
                  ? 'bg-stone-900 text-white'
                  : 'text-stone-600 hover:bg-[#F2EDE4] hover:text-stone-900'
              )}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* General Tab */}
        {activeTab === 'general' && (
          <div className="rounded-2xl border border-[#E7E2DA] bg-white p-5 space-y-4 shadow-2xs">
            <h3 className="text-sm font-semibold text-stone-900">Backend Connection</h3>

            <div>
              <label className="block text-xs font-medium text-stone-700 mb-1">
                FastAPI Server Base URL
              </label>
              <input
                type="url"
                value={formData.apiBaseUrl}
                onChange={(e) => setFormData({ ...formData, apiBaseUrl: e.target.value })}
                placeholder="http://localhost:8000/api/v1"
                required
                className="w-full text-xs p-2.5 rounded-xl border border-[#E7E2DA] bg-[#FAF8F5] text-stone-900 focus:outline-none focus:border-[#C25E43] focus:bg-white font-mono"
              />
              <p className="text-[11px] text-stone-400 mt-1">
                Points to the FastAPI runtime service endpoints.
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium text-stone-700 mb-1">
                Response Generation Mode
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, responseMode: 'concise' })}
                  className={cn(
                    'p-3 rounded-xl border text-left cursor-pointer transition-colors',
                    formData.responseMode === 'concise'
                      ? 'border-[#C25E43] bg-[#FDF6F3]'
                      : 'border-[#E7E2DA] hover:bg-stone-50'
                  )}
                >
                  <div className="font-semibold text-xs text-stone-900">Concise</div>
                  <div className="text-[11px] text-stone-500 mt-0.5">
                    Direct answers backed strictly by verified citations without superfluous prose.
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, responseMode: 'detailed' })}
                  className={cn(
                    'p-3 rounded-xl border text-left cursor-pointer transition-colors',
                    formData.responseMode === 'detailed'
                      ? 'border-[#C25E43] bg-[#FDF6F3]'
                      : 'border-[#E7E2DA] hover:bg-stone-50'
                  )}
                >
                  <div className="font-semibold text-xs text-stone-900">Detailed & Exhaustive</div>
                  <div className="text-[11px] text-stone-500 mt-0.5">
                    Thorough comparative breakdowns including conflicting evidence and gap analysis.
                  </div>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Appearance Tab */}
        {activeTab === 'appearance' && (
          <div className="rounded-2xl border border-[#E7E2DA] bg-white p-5 space-y-4 shadow-2xs">
            <h3 className="text-sm font-semibold text-stone-900">Warm Editorial Light Aesthetic</h3>

            <div className="p-4 rounded-xl bg-[#FAF8F5] border border-[#E7E2DA] space-y-3">
              <div className="text-xs font-medium text-stone-800">Visual Palette Constraints</div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center text-xs">
                <div className="p-3 rounded-lg bg-[#FAF8F5] border border-[#E7E2DA]">
                  <div className="w-4 h-4 rounded-full bg-[#FAF8F5] border border-stone-300 mx-auto mb-1" />
                  <span className="text-[11px] text-stone-600">Warm Ivory</span>
                </div>
                <div className="p-3 rounded-lg bg-white border border-[#E7E2DA]">
                  <div className="w-4 h-4 rounded-full bg-white border border-stone-300 mx-auto mb-1" />
                  <span className="text-[11px] text-stone-600">Clean White</span>
                </div>
                <div className="p-3 rounded-lg bg-[#FDF6F3] border border-[#F1D6CE]">
                  <div className="w-4 h-4 rounded-full bg-[#C25E43] mx-auto mb-1" />
                  <span className="text-[11px] text-[#C25E43] font-medium">Terracotta</span>
                </div>
                <div className="p-3 rounded-lg bg-[#F4F6F0] border border-[#DCE4D0]">
                  <div className="w-4 h-4 rounded-full bg-[#5F7143] mx-auto mb-1" />
                  <span className="text-[11px] text-[#5F7143] font-medium">Olive Success</span>
                </div>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-stone-700 mb-1">
                Layout Density
              </label>
              <div className="flex gap-3">
                {['comfortable', 'compact'].map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setFormData({ ...formData, density: d as any })}
                    className={cn(
                      'px-4 py-2 rounded-xl text-xs font-medium border capitalize cursor-pointer transition-colors',
                      formData.density === d
                        ? 'border-[#C25E43] bg-[#FDF6F3] text-[#C25E43]'
                        : 'border-[#E7E2DA] text-stone-700 hover:bg-stone-50'
                    )}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Agent & Budgets Tab */}
        {activeTab === 'agent' && (
          <div className="rounded-2xl border border-[#E7E2DA] bg-white p-5 space-y-5 shadow-2xs">
            <div>
              <h3 className="text-sm font-semibold text-stone-900">Monotonic Execution Budgets</h3>
              <p className="text-xs text-stone-500 mt-0.5">
                Guardrails enforcing latency and iteration caps across controller and retrieval agent nodes.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-stone-700 mb-1">
                  Max Retrieval Iterations ({formData.budgets.max_retrieval_iterations})
                </label>
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={formData.budgets.max_retrieval_iterations}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      budgets: { ...formData.budgets, max_retrieval_iterations: parseInt(e.target.value) },
                    })
                  }
                  className="w-full accent-[#C25E43]"
                />
                <div className="flex justify-between text-[10px] text-stone-400">
                  <span>1 (Strict)</span>
                  <span>3 (Default)</span>
                  <span>5 (Thorough)</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-stone-700 mb-1">
                  Max Tool Calls ({formData.budgets.max_tool_calls})
                </label>
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={formData.budgets.max_tool_calls}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      budgets: { ...formData.budgets, max_tool_calls: parseInt(e.target.value) },
                    })
                  }
                  className="w-full accent-[#C25E43]"
                />
                <div className="flex justify-between text-[10px] text-stone-400">
                  <span>1</span>
                  <span>3</span>
                  <span>5</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-stone-700 mb-1">
                  Max Latency Budget (ms)
                </label>
                <input
                  type="number"
                  step="5000"
                  min="5000"
                  max="120000"
                  value={formData.budgets.max_latency_ms}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      budgets: { ...formData.budgets, max_latency_ms: parseInt(e.target.value) || 30000 },
                    })
                  }
                  className="w-full text-xs p-2 rounded-xl border border-[#E7E2DA] bg-[#FAF8F5] text-stone-900 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-stone-700 mb-1">
                  Max Output Tokens
                </label>
                <input
                  type="number"
                  step="500"
                  min="500"
                  max="8000"
                  value={formData.budgets.max_output_tokens}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      budgets: { ...formData.budgets, max_output_tokens: parseInt(e.target.value) || 2000 },
                    })
                  }
                  className="w-full text-xs p-2 rounded-xl border border-[#E7E2DA] bg-[#FAF8F5] text-stone-900 font-mono"
                />
              </div>
            </div>
          </div>
        )}

        {/* Developer Mode Tab */}
        {activeTab === 'developer' && (
          <div className="rounded-2xl border border-[#E7E2DA] bg-white p-5 space-y-4 shadow-2xs">
            <div>
              <h3 className="text-sm font-semibold text-stone-900">Developer Diagnostics</h3>
              <p className="text-xs text-stone-500 mt-0.5">
                Advanced debug tools, event stream telemetry replay, and raw response inspection.
              </p>
            </div>

            <div className="flex items-center justify-between p-3.5 rounded-xl bg-[#FAF8F5] border border-[#E7E2DA]">
              <div>
                <div className="text-xs font-medium text-stone-900">Open Execution Inspector by default</div>
                <div className="text-[11px] text-stone-500">Automatically expands right telemetry drawer on every query.</div>
              </div>
              <input
                type="checkbox"
                checked={formData.showTelemetryByDefault}
                onChange={(e) => setFormData({ ...formData, showTelemetryByDefault: e.target.checked })}
                className="w-4 h-4 accent-[#C25E43]"
              />
            </div>

            <div className="flex items-center justify-between p-3.5 rounded-xl bg-[#FAF8F5] border border-[#E7E2DA]">
              <div>
                <div className="text-xs font-medium text-stone-900">Enable Web Search fallback by default</div>
                <div className="text-[11px] text-stone-500">Enables ADK Google Search fallback when local knowledge is insufficient.</div>
              </div>
              <input
                type="checkbox"
                checked={formData.enableWebFallback}
                onChange={(e) => setFormData({ ...formData, enableWebFallback: e.target.checked })}
                className="w-4 h-4 accent-[#C25E43]"
              />
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-2">
          <button
            type="button"
            onClick={handleResetDefaults}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-[#E7E2DA] text-xs text-stone-600 hover:bg-stone-50 transition-colors cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Defaults</span>
          </button>

          <button
            type="submit"
            className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl bg-[#C25E43] text-white hover:bg-[#B04E35] text-xs font-medium transition-colors shadow-xs cursor-pointer"
          >
            <Save className="w-4 h-4" />
            <span>Save Settings</span>
          </button>
        </div>
      </form>
    </div>
  );
};

