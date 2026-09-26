import { LocalSessionMeta, UserSettings } from '../types';

const CONVERSATIONS_KEY = 'kriyaman_local_conversations';
const SETTINGS_KEY = 'kriyaman_user_settings';
const CLIENT_ID_KEY = 'kriyaman_client_id';

export function getClientId(): string {
  if (typeof window === 'undefined') return 'default-client';
  try {
    let id = localStorage.getItem(CLIENT_ID_KEY);
    if (!id) {
      id = typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : 'client-' + Math.random().toString(36).substring(2, 15);
      localStorage.setItem(CLIENT_ID_KEY, id);
    }
    return id;
  } catch {
    return 'default-client';
  }
}

export const DEFAULT_SETTINGS: UserSettings = {
  apiBaseUrl: 'http://localhost:8000/api/v1',
  responseMode: 'concise',
  enableWebFallback: false,
  budgets: {
    max_retrieval_iterations: 3,
    max_tool_calls: 3,
    max_latency_ms: 30000,
    max_input_tokens: 12000,
    max_output_tokens: 2000,
  },
  density: 'comfortable',
  showTelemetryByDefault: false,
  byok: {
    keyMode: 'default',
    geminiApiKey: '',
    groqApiKey: '',
    groqSecondaryApiKey: '',
    tavilyApiKey: '',
  },
};

export function getLocalSessions(): LocalSessionMeta[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(CONVERSATIONS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.sort(
      (a, b) => new Date(b.updatedAt || b.createdAt).getTime() - new Date(a.updatedAt || a.createdAt).getTime()
    );
  } catch {
    return [];
  }
}

export function saveLocalSession(meta: LocalSessionMeta): void {
  if (typeof window === 'undefined') return;
  try {
    const existing = getLocalSessions();
    const index = existing.findIndex((s) => s.id === meta.id);
    if (index >= 0) {
      existing[index] = {
        ...existing[index],
        ...meta,
        updatedAt: meta.updatedAt || new Date().toISOString(),
      };
    } else {
      existing.unshift({
        ...meta,
        createdAt: meta.createdAt || new Date().toISOString(),
        updatedAt: meta.updatedAt || new Date().toISOString(),
      });
    }
    localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(existing));
  } catch (err) {
    console.error('Failed to save session to local storage', err);
  }
}

export function updateLocalSessionTitle(id: string, title: string): void {
  if (typeof window === 'undefined') return;
  try {
    const existing = getLocalSessions();
    const item = existing.find((s) => s.id === id);
    if (item) {
      item.title = title;
      item.updatedAt = new Date().toISOString();
      localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(existing));
    }
  } catch {}
}

export function deleteLocalSession(id: string): void {
  if (typeof window === 'undefined') return;
  try {
    const existing = getLocalSessions();
    const filtered = existing.filter((s) => s.id !== id);
    localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(filtered));
  } catch {}
}

export interface GroupedSessions {
  today: LocalSessionMeta[];
  yesterday: LocalSessionMeta[];
  older: LocalSessionMeta[];
}

export function groupSessionsByDate(sessions: LocalSessionMeta[]): GroupedSessions {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startOfYesterday = startOfToday - 24 * 60 * 60 * 1000;

  const result: GroupedSessions = {
    today: [],
    yesterday: [],
    older: [],
  };

  for (const session of sessions) {
    const date = new Date(session.updatedAt || session.createdAt).getTime();
    if (date >= startOfToday) {
      result.today.push(session);
    } else if (date >= startOfYesterday) {
      result.yesterday.push(session);
    } else {
      result.older.push(session);
    }
  }

  return result;
}

export function getUserSettings(): UserSettings {
  if (typeof window === 'undefined') return DEFAULT_SETTINGS;
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(raw);
    return {
      ...DEFAULT_SETTINGS,
      ...parsed,
      budgets: {
        ...DEFAULT_SETTINGS.budgets,
        ...(parsed.budgets || {}),
      },
      byok: {
        ...DEFAULT_SETTINGS.byok,
        ...(parsed.byok || {}),
      },
    };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function saveUserSettings(partial: Partial<UserSettings>): UserSettings {
  if (typeof window === 'undefined') return DEFAULT_SETTINGS;
  try {
    const current = getUserSettings();
    const updated: UserSettings = {
      ...current,
      ...partial,
      budgets: {
        ...current.budgets,
        ...(partial.budgets || {}),
      },
      byok: {
        ...current.byok,
        ...(partial.byok || {}),
      },
    };
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(updated));
    if (partial.apiBaseUrl) {
      localStorage.setItem('kriyaman_api_base_url', partial.apiBaseUrl.trim());
    }
    return updated;
  } catch {
    return DEFAULT_SETTINGS;
  }
}

