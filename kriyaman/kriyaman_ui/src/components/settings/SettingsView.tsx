'use client';

import React, { useState, useEffect } from 'react';
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
  Key,
  Lock,
  Eye,
  EyeOff,
  CheckCircle2,
  XCircle,
  Loader2,
  Coins,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react';
import { ClientCreditInfo, ProviderKeyStatus, UserSettings } from '../../types';
import { DEFAULT_SETTINGS, saveUserSettings } from '../../lib/storage';
import { testApiKeys } from '../../lib/api';
import { cn } from '../../lib/utils';

interface SettingsViewProps {
  settings: UserSettings;
  onUpdateSettings: (newSettings: UserSettings) => void;
  onBack?: () => void;
  clientCredits?: ClientCreditInfo | null;
  onRefreshCredits?: () => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  settings,
  onUpdateSettings,
  onBack,
  clientCredits,
  onRefreshCredits,
}) => {
  const [activeTab, setActiveTab] = useState<'general' | 'appearance' | 'agent' | 'developer'>('general');
  const [formData, setFormData] = useState<UserSettings>(() => ({
    ...settings,
    byok: settings.byok || DEFAULT_SETTINGS.byok,
  }));
  const [savedNotice, setSavedNotice] = useState(false);
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  const [testingKey, setTestingKey] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, ProviderKeyStatus>>({});
  const [testSummaryError, setTestSummaryError] = useState<string | null>(null);

  useEffect(() => {
    setFormData({
      ...settings,
      byok: settings.byok || DEFAULT_SETTINGS.byok,
    });
  }, [settings]);

  const toggleSecret = (field: string) => {
    setShowSecrets((prev) => ({ ...prev, [field]: !prev[field] }));
  };

  const handleTestKey = async (provider: 'gemini' | 'groq' | 'groq_secondary' | 'tavily') => {
    setTestingKey(provider);
    setTestSummaryError(null);
    try {
      const payload: any = {};
      if (provider === 'gemini') payload.gemini_api_key = formData.byok.geminiApiKey;
      if (provider === 'groq') payload.groq_api_key = formData.byok.groqApiKey;
      if (provider === 'groq_secondary') payload.groq_api_key_secondary = formData.byok.groqSecondaryApiKey;
      if (provider === 'tavily') payload.tavily_api_key = formData.byok.tavilyApiKey;

      const res = await testApiKeys(payload);
      if (provider === 'gemini' && res.gemini) {
        setTestResults((prev) => ({ ...prev, gemini: res.gemini! }));
      } else if (provider === 'groq' && res.groq) {
        setTestResults((prev) => ({ ...prev, groq: res.groq! }));
      } else if (provider === 'groq_secondary' && res.groq_secondary) {
        setTestResults((prev) => ({ ...prev, groq_secondary: res.groq_secondary! }));
      } else if (provider === 'tavily' && res.tavily) {
        setTestResults((prev) => ({ ...prev, tavily: res.tavily! }));
      }
    } catch (err: any) {
      setTestResults((prev) => ({
        ...prev,
        [provider]: { valid: false, message: err?.message || 'Connection test failed' },
      }));
    } finally {
      setTestingKey(null);
    }
  };

  const handleTestAllKeys = async () => {
    setTestingKey('all');
    setTestSummaryError(null);
    try {
      const payload = {
        gemini_api_key: formData.byok.geminiApiKey || undefined,
        groq_api_key: formData.byok.groqApiKey || undefined,
        groq_api_key_secondary: formData.byok.groqSecondaryApiKey || undefined,
        tavily_api_key: formData.byok.tavilyApiKey || undefined,
      };
      const res = await testApiKeys(payload);
      const results: Record<string, ProviderKeyStatus> = {};
      if (res.gemini) results.gemini = res.gemini;
      if (res.groq) results.groq = res.groq;
      if (res.groq_secondary) results.groq_secondary = res.groq_secondary;
      if (res.tavily) results.tavily = res.tavily;
      setTestResults(results);
    } catch (err: any) {
      setTestSummaryError(err?.message || 'Failed to verify API keys');
    } finally {
      setTestingKey(null);
    }
  };

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
          <div className="space-y-6">
            {/* Backend Connection & Response Mode */}
            <div className="rounded-2xl border border-[#E7E2DA] bg-white p-5 space-y-4 shadow-2xs">
              <h3 className="text-sm font-semibold text-stone-900">Backend Connection & Response Mode</h3>

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

            {/* Credit & Budget Overview Card */}
            <div className="rounded-2xl border border-[#E7E2DA] bg-white p-5 space-y-4 shadow-2xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Coins className="w-4 h-4 text-[#C07D32]" />
                  <h3 className="text-sm font-semibold text-stone-900">
                    {formData.byok.keyMode === 'byok'
                      ? 'Personal Keys Expenditure Tracker'
                      : 'Free Platform Credit Usage ($5.00 Trial)'}
                  </h3>
                </div>
                {onRefreshCredits && (
                  <button
                    type="button"
                    onClick={onRefreshCredits}
                    className="flex items-center gap-1 text-xs text-stone-500 hover:text-stone-800 transition-colors cursor-pointer"
                    title="Refresh credit balance"
                  >
                    <RefreshCw className="w-3 h-3" />
                    <span>Refresh</span>
                  </button>
                )}
              </div>

              {formData.byok.keyMode === 'default' ? (
                <div className="space-y-3">
                  <div className="flex items-baseline justify-between">
                    <div>
                      <span className="text-2xl font-bold font-mono text-stone-900">
                        ${(clientCredits?.default_spent_usd ?? 0).toFixed(4)}
                      </span>
                      <span className="text-xs text-stone-500 ml-1.5">
                        / ${(clientCredits?.credit_limit_usd ?? 5.0).toFixed(2)} USD used
                      </span>
                    </div>
                    <div className="text-right">
                      <span
                        className={cn(
                          'text-xs font-semibold font-mono',
                          (clientCredits?.remaining_credit_usd ?? 5.0) <= 0.5 ? 'text-red-600' : 'text-[#5F7143]'
                        )}
                      >
                        ${(clientCredits?.remaining_credit_usd ?? 5.0).toFixed(4)} USD
                      </span>
                      <div className="text-[11px] text-stone-400">remaining credit</div>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="w-full bg-[#F2EDE4] h-2 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        'h-full rounded-full transition-all duration-500',
                        clientCredits?.is_capped
                          ? 'bg-red-500'
                          : (clientCredits?.remaining_credit_usd ?? 5.0) <= 1.0
                          ? 'bg-amber-500'
                          : 'bg-[#C25E43]'
                      )}
                      style={{
                        width: `${Math.min(
                          100,
                          Math.max(
                            2,
                            ((clientCredits?.default_spent_usd ?? 0) / (clientCredits?.credit_limit_usd ?? 5.0)) * 100
                          )
                        )}%`,
                      }}
                    />
                  </div>

                  {clientCredits?.is_capped ? (
                    <div className="flex items-start gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs">
                      <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                      <div>
                        <div className="font-semibold">Free Credit Limit Reached ($5.00)</div>
                        <div className="text-[11px] text-red-600 mt-0.5">
                          You have exhausted your free trial quota. Switch your Key Mode to &quot;BYOK&quot; below and configure your personal API keys to continue unlimited queries.
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-[11px] text-stone-500">
                      Every query and retrieval run deducts from this $5.00 trial quota based on exact token usage.
                    </p>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-baseline justify-between">
                    <div>
                      <span className="text-2xl font-bold font-mono text-stone-900">
                        ${(clientCredits?.byok_spent_usd ?? 0).toFixed(4)}
                      </span>
                      <span className="text-xs text-stone-500 ml-1.5">USD personal spend tracked</span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-[#F4F6F0] text-[#5F7143] border border-[#DCE4D0]">
                      Unlimited Quota
                    </span>
                  </div>

                  <p className="text-[11px] text-stone-500">
                    In BYOK mode, calls are dispatched using your personal provider keys. Requests bypass Kriyamaan&apos;s $5.00 limit. Cumulative expenditure is tracked here using standard provider token rates for transparent accounting.
                  </p>
                </div>
              )}
            </div>

            {/* Mode Selector */}
            <div className="rounded-2xl border border-[#E7E2DA] bg-white p-5 space-y-4 shadow-2xs">
              <div className="flex items-center gap-2">
                <Key className="w-4 h-4 text-[#C25E43]" />
                <div>
                  <h3 className="text-sm font-semibold text-stone-900">API Key Operation Mode</h3>
                  <p className="text-[11px] text-stone-500 mt-0.5">
                    Select whether to consume managed platform credits or supply your own keys.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() =>
                    setFormData({
                      ...formData,
                      byok: { ...formData.byok, keyMode: 'default' },
                    })
                  }
                  className={cn(
                    'p-3.5 rounded-xl border text-left cursor-pointer transition-all flex flex-col justify-between',
                    formData.byok.keyMode === 'default'
                      ? 'border-[#C25E43] bg-[#FDF6F3] ring-1 ring-[#C25E43]/20 shadow-xs'
                      : 'border-[#E7E2DA] hover:bg-stone-50'
                  )}
                >
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <div className="font-semibold text-xs text-stone-900">Default Platform Keys</div>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-stone-100 text-stone-600">
                        $5.00 Free Trial
                      </span>
                    </div>
                    <div className="text-[11px] text-stone-500 leading-relaxed">
                      Uses pre-configured server environment keys. Perfect for trying out Kriyamaan without setting up provider accounts.
                    </div>
                  </div>
                  <div className="text-[10px] text-[#C25E43] font-medium mt-3 flex items-center gap-1">
                    {formData.byok.keyMode === 'default' && <Check className="w-3 h-3" />}
                    <span>{formData.byok.keyMode === 'default' ? 'Active Mode' : 'Click to select'}</span>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() =>
                    setFormData({
                      ...formData,
                      byok: { ...formData.byok, keyMode: 'byok' },
                    })
                  }
                  className={cn(
                    'p-3.5 rounded-xl border text-left cursor-pointer transition-all flex flex-col justify-between',
                    formData.byok.keyMode === 'byok'
                      ? 'border-[#C25E43] bg-[#FDF6F3] ring-1 ring-[#C25E43]/20 shadow-xs'
                      : 'border-[#E7E2DA] hover:bg-stone-50'
                  )}
                >
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <div className="font-semibold text-xs text-stone-900">Bring Your Own Key (BYOK)</div>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-[#F4F6F0] text-[#5F7143]">
                        Unlimited
                      </span>
                    </div>
                    <div className="text-[11px] text-stone-500 leading-relaxed">
                      Provide your own Gemini, Groq, and Tavily keys stored securely in your browser. Unlimited queries.
                    </div>
                  </div>
                  <div className="text-[10px] text-[#C25E43] font-medium mt-3 flex items-center gap-1">
                    {formData.byok.keyMode === 'byok' && <Check className="w-3 h-3" />}
                    <span>{formData.byok.keyMode === 'byok' ? 'Active Mode' : 'Click to select'}</span>
                  </div>
                </button>
              </div>
            </div>

            {/* Provider API Credentials Card */}
            <div className="rounded-2xl border border-[#E7E2DA] bg-white p-5 space-y-4 shadow-2xs">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <Lock className="w-4 h-4 text-[#5F7143]" />
                  <div>
                    <h3 className="text-sm font-semibold text-stone-900">Provider API Credentials</h3>
                    <p className="text-[11px] text-stone-500 mt-0.5">
                      Keys are stored in your browser&apos;s local storage and passed securely via request headers. Never persisted on server disk or database.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleTestAllKeys}
                  disabled={testingKey !== null}
                  className="px-3 py-1.5 rounded-lg border border-[#E7E2DA] bg-[#FAF8F5] text-stone-700 hover:bg-[#F2EDE4] hover:text-stone-900 text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                >
                  {testingKey === 'all' ? (
                    <Loader2 className="w-3 h-3 animate-spin text-[#C25E43]" />
                  ) : (
                    <Sparkles className="w-3 h-3 text-[#C25E43]" />
                  )}
                  <span>Test All Connections</span>
                </button>
              </div>

              {testSummaryError && (
                <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{testSummaryError}</span>
                </div>
              )}

              <div className="space-y-4 pt-1">
                {/* Google Gemini */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-medium text-stone-800 flex items-center gap-1.5">
                      <span>Google Gemini API Key</span>
                      {formData.byok.keyMode === 'byok' && (
                        <span className="text-[10px] text-red-500 font-normal">*required for BYOK</span>
                      )}
                    </label>
                    {testResults.gemini && (
                      <span
                        className={cn(
                          'text-[11px] font-medium flex items-center gap-1',
                          testResults.gemini.valid ? 'text-[#5F7143]' : 'text-red-600'
                        )}
                      >
                        {testResults.gemini.valid ? (
                          <>
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Valid ({testResults.gemini.latency_ms ?? 0}ms)</span>
                          </>
                        ) : (
                          <>
                            <XCircle className="w-3 h-3" />
                            <span>Invalid</span>
                          </>
                        )}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <input
                        type={showSecrets.gemini ? 'text' : 'password'}
                        value={formData.byok.geminiApiKey}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            byok: { ...formData.byok, geminiApiKey: e.target.value },
                          })
                        }
                        placeholder="AIzaSy..."
                        className="w-full text-xs p-2.5 pr-8 rounded-xl border border-[#E7E2DA] bg-[#FAF8F5] text-stone-900 focus:outline-none focus:border-[#C25E43] focus:bg-white font-mono"
                      />
                      <button
                        type="button"
                        onClick={() => toggleSecret('gemini')}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-700 cursor-pointer"
                        title={showSecrets.gemini ? 'Hide key' : 'Show key'}
                      >
                        {showSecrets.gemini ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleTestKey('gemini')}
                      disabled={!formData.byok.geminiApiKey || testingKey !== null}
                      className="px-3 py-2 rounded-xl border border-[#E7E2DA] bg-[#FAF8F5] text-stone-700 hover:bg-[#F2EDE4] hover:text-stone-900 text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-40"
                    >
                      {testingKey === 'gemini' ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-[#C25E43]" />
                      ) : (
                        <span>Test</span>
                      )}
                    </button>
                  </div>
                  <p className="text-[11px] text-stone-400 mt-1">
                    Powers Gemini 3.6 Flash for synthesis, evidence evaluation, and final answers.
                  </p>
                  {testResults.gemini && !testResults.gemini.valid && (
                    <p className="text-[11px] text-red-600 mt-1">{testResults.gemini.message}</p>
                  )}
                </div>

                {/* Groq Primary */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-medium text-stone-800 flex items-center gap-1.5">
                      <span>Groq Primary API Key</span>
                      {formData.byok.keyMode === 'byok' && (
                        <span className="text-[10px] text-red-500 font-normal">*required for BYOK</span>
                      )}
                    </label>
                    {testResults.groq && (
                      <span
                        className={cn(
                          'text-[11px] font-medium flex items-center gap-1',
                          testResults.groq.valid ? 'text-[#5F7143]' : 'text-red-600'
                        )}
                      >
                        {testResults.groq.valid ? (
                          <>
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Valid ({testResults.groq.latency_ms ?? 0}ms)</span>
                          </>
                        ) : (
                          <>
                            <XCircle className="w-3 h-3" />
                            <span>Invalid</span>
                          </>
                        )}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <input
                        type={showSecrets.groq ? 'text' : 'password'}
                        value={formData.byok.groqApiKey}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            byok: { ...formData.byok, groqApiKey: e.target.value },
                          })
                        }
                        placeholder="gsk_..."
                        className="w-full text-xs p-2.5 pr-8 rounded-xl border border-[#E7E2DA] bg-[#FAF8F5] text-stone-900 focus:outline-none focus:border-[#C25E43] focus:bg-white font-mono"
                      />
                      <button
                        type="button"
                        onClick={() => toggleSecret('groq')}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-700 cursor-pointer"
                        title={showSecrets.groq ? 'Hide key' : 'Show key'}
                      >
                        {showSecrets.groq ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleTestKey('groq')}
                      disabled={!formData.byok.groqApiKey || testingKey !== null}
                      className="px-3 py-2 rounded-xl border border-[#E7E2DA] bg-[#FAF8F5] text-stone-700 hover:bg-[#F2EDE4] hover:text-stone-900 text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-40"
                    >
                      {testingKey === 'groq' ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-[#C25E43]" />
                      ) : (
                        <span>Test</span>
                      )}
                    </button>
                  </div>
                  <p className="text-[11px] text-stone-400 mt-1">
                    Powers fast query planning and acquisition reasoning via Qwen 3.8-27B.
                  </p>
                  {testResults.groq && !testResults.groq.valid && (
                    <p className="text-[11px] text-red-600 mt-1">{testResults.groq.message}</p>
                  )}
                </div>

                {/* Groq Secondary */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-medium text-stone-800 flex items-center gap-1.5">
                      <span>Groq Secondary API Key</span>
                      <span className="text-[10px] text-stone-400 font-normal">optional fallback</span>
                    </label>
                    {testResults.groq_secondary && (
                      <span
                        className={cn(
                          'text-[11px] font-medium flex items-center gap-1',
                          testResults.groq_secondary.valid ? 'text-[#5F7143]' : 'text-red-600'
                        )}
                      >
                        {testResults.groq_secondary.valid ? (
                          <>
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Valid ({testResults.groq_secondary.latency_ms ?? 0}ms)</span>
                          </>
                        ) : (
                          <>
                            <XCircle className="w-3 h-3" />
                            <span>Invalid</span>
                          </>
                        )}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <input
                        type={showSecrets.groq_secondary ? 'text' : 'password'}
                        value={formData.byok.groqSecondaryApiKey || ''}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            byok: { ...formData.byok, groqSecondaryApiKey: e.target.value },
                          })
                        }
                        placeholder="gsk_..."
                        className="w-full text-xs p-2.5 pr-8 rounded-xl border border-[#E7E2DA] bg-[#FAF8F5] text-stone-900 focus:outline-none focus:border-[#C25E43] focus:bg-white font-mono"
                      />
                      <button
                        type="button"
                        onClick={() => toggleSecret('groq_secondary')}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-700 cursor-pointer"
                        title={showSecrets.groq_secondary ? 'Hide key' : 'Show key'}
                      >
                        {showSecrets.groq_secondary ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleTestKey('groq_secondary')}
                      disabled={!formData.byok.groqSecondaryApiKey || testingKey !== null}
                      className="px-3 py-2 rounded-xl border border-[#E7E2DA] bg-[#FAF8F5] text-stone-700 hover:bg-[#F2EDE4] hover:text-stone-900 text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-40"
                    >
                      {testingKey === 'groq_secondary' ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-[#C25E43]" />
                      ) : (
                        <span>Test</span>
                      )}
                    </button>
                  </div>
                  <p className="text-[11px] text-stone-400 mt-1">
                    Backup Groq key for automatic load balancing and fallback when the primary key encounters 429 rate limits.
                  </p>
                  {testResults.groq_secondary && !testResults.groq_secondary.valid && (
                    <p className="text-[11px] text-red-600 mt-1">{testResults.groq_secondary.message}</p>
                  )}
                </div>

                {/* Tavily Web Search */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-medium text-stone-800 flex items-center gap-1.5">
                      <span>Tavily Search API Key</span>
                      <span className="text-[10px] text-stone-400 font-normal">optional fallback</span>
                    </label>
                    {testResults.tavily && (
                      <span
                        className={cn(
                          'text-[11px] font-medium flex items-center gap-1',
                          testResults.tavily.valid ? 'text-[#5F7143]' : 'text-red-600'
                        )}
                      >
                        {testResults.tavily.valid ? (
                          <>
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Valid ({testResults.tavily.latency_ms ?? 0}ms)</span>
                          </>
                        ) : (
                          <>
                            <XCircle className="w-3 h-3" />
                            <span>Invalid</span>
                          </>
                        )}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <input
                        type={showSecrets.tavily ? 'text' : 'password'}
                        value={formData.byok.tavilyApiKey || ''}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            byok: { ...formData.byok, tavilyApiKey: e.target.value },
                          })
                        }
                        placeholder="tvly-..."
                        className="w-full text-xs p-2.5 pr-8 rounded-xl border border-[#E7E2DA] bg-[#FAF8F5] text-stone-900 focus:outline-none focus:border-[#C25E43] focus:bg-white font-mono"
                      />
                      <button
                        type="button"
                        onClick={() => toggleSecret('tavily')}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-700 cursor-pointer"
                        title={showSecrets.tavily ? 'Hide key' : 'Show key'}
                      >
                        {showSecrets.tavily ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleTestKey('tavily')}
                      disabled={!formData.byok.tavilyApiKey || testingKey !== null}
                      className="px-3 py-2 rounded-xl border border-[#E7E2DA] bg-[#FAF8F5] text-stone-700 hover:bg-[#F2EDE4] hover:text-stone-900 text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-40"
                    >
                      {testingKey === 'tavily' ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-[#C25E43]" />
                      ) : (
                        <span>Test</span>
                      )}
                    </button>
                  </div>
                  <p className="text-[11px] text-stone-400 mt-1">
                    Used for real-time web search fallback when document coverage is insufficient.
                  </p>
                  {testResults.tavily && !testResults.tavily.valid && (
                    <p className="text-[11px] text-red-600 mt-1">{testResults.tavily.message}</p>
                  )}
                </div>
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

