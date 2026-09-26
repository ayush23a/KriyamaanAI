import {
  ClientCreditInfo,
  DocumentItem,
  ExecutionBudgets,
  HealthStatus,
  MemoryItem,
  RunEvent,
  RunResponse,
  Session,
  SessionDetail,
  TestKeysResponse,
} from '../types';
import { getClientId, getUserSettings } from './storage';

export function getApiBaseUrl(): string {
  if (typeof window !== 'undefined') {
    const custom = localStorage.getItem('kriyaman_api_base_url');
    if (custom && custom.trim()) {
      return custom.trim().replace(/\/$/, '');
    }
  }
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && envUrl.trim()) {
    return envUrl.trim().replace(/\/$/, '');
  }
  return 'http://localhost:8000/api/v1';
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  const headers = new Headers(options.headers || {});
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  // Inject Client ID and BYOK headers if available in browser
  if (typeof window !== 'undefined') {
    const clientId = getClientId();
    headers.set('X-Client-Id', clientId);

    const settings = getUserSettings();
    if (settings.byok) {
      headers.set('X-Key-Mode', settings.byok.keyMode || 'default');
      if (settings.byok.keyMode === 'byok') {
        if (settings.byok.geminiApiKey) headers.set('X-Gemini-Api-Key', settings.byok.geminiApiKey.trim());
        if (settings.byok.groqApiKey) headers.set('X-Groq-Api-Key', settings.byok.groqApiKey.trim());
        if (settings.byok.groqSecondaryApiKey) headers.set('X-Groq-Secondary-Api-Key', settings.byok.groqSecondaryApiKey.trim());
        if (settings.byok.tavilyApiKey) headers.set('X-Tavily-Api-Key', settings.byok.tavilyApiKey.trim());
      }
    }
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status} ${response.statusText}`;
    try {
      const errorJson = await response.json();
      if (errorJson?.error?.message) {
        errorDetail = errorJson.error.message;
      } else if (errorJson?.detail) {
        errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // ignore non-json error
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------
export async function checkHealth(): Promise<HealthStatus> {
  return request<HealthStatus>('/health');
}

// ---------------------------------------------------------------------------
// Sessions
// ---------------------------------------------------------------------------
export async function createSession(title?: string, metadata: Record<string, any> = {}): Promise<Session> {
  return request<Session>('/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: title || 'New Research', metadata }),
  });
}

export async function getSession(sessionId: string): Promise<SessionDetail> {
  return request<SessionDetail>(`/sessions/${encodeURIComponent(sessionId)}`);
}

// ---------------------------------------------------------------------------
// Runs & Events
// ---------------------------------------------------------------------------
export interface CreateRunPayload {
  query: string;
  budgets?: Partial<ExecutionBudgets>;
  response_mode?: 'concise' | 'detailed';
  enable_web_search?: boolean;
}

export async function createRun(sessionId: string, payload: CreateRunPayload): Promise<RunResponse> {
  return request<RunResponse>(`/sessions/${encodeURIComponent(sessionId)}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: payload.query,
      response_mode: payload.response_mode || 'concise',
      enable_web_search: !!payload.enable_web_search,
      budgets: payload.budgets,
    }),
  });
}

export async function getRun(runId: string): Promise<RunResponse> {
  return request<RunResponse>(`/runs/${encodeURIComponent(runId)}`);
}

export async function getRunEvents(runId: string): Promise<RunEvent[]> {
  const data = await request<{ run_id: string; events: RunEvent[] }>(`/runs/${encodeURIComponent(runId)}/events`);
  return data.events || [];
}

// ---------------------------------------------------------------------------
// Documents (Session Knowledge)
// ---------------------------------------------------------------------------
export async function uploadDocument(sessionId: string, file: File, signal?: AbortSignal): Promise<DocumentItem> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/sessions/${encodeURIComponent(sessionId)}/documents`;

  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(url, {
    method: 'POST',
    body: formData,
    signal,
  });

  if (!response.ok) {
    let errorDetail = `Upload failed with HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson?.error?.message) errorDetail = errJson.error.message;
      else if (errJson?.detail) errorDetail = errJson.detail;
    } catch {}
    throw new Error(errorDetail);
  }

  return response.json();
}

export async function listDocuments(sessionId: string): Promise<DocumentItem[]> {
  const data = await request<{ documents: DocumentItem[] }>(`/sessions/${encodeURIComponent(sessionId)}/documents`);
  return data.documents || [];
}

export async function deleteDocument(documentId: string): Promise<{ success: boolean; message: string }> {
  return request<{ success: boolean; message: string }>(`/documents/${encodeURIComponent(documentId)}`, {
    method: 'DELETE',
  });
}

// ---------------------------------------------------------------------------
// Explicit Memories
// ---------------------------------------------------------------------------
export async function createMemory(
  sessionId: string,
  content: string,
  kind: string = 'user_preference'
): Promise<MemoryItem> {
  return request<MemoryItem>(`/sessions/${encodeURIComponent(sessionId)}/memories`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, kind }),
  });
}

export async function listMemories(sessionId: string): Promise<MemoryItem[]> {
  const data = await request<{ memories: MemoryItem[] }>(`/sessions/${encodeURIComponent(sessionId)}/memories`);
  return data.memories || [];
}

export async function deleteMemory(memoryId: string): Promise<{ success: boolean; message: string }> {
  return request<{ success: boolean; message: string }>(`/memories/${encodeURIComponent(memoryId)}`, {
    method: 'DELETE',
  });
}

// ---------------------------------------------------------------------------
// Credits & BYOK Key Verification
// ---------------------------------------------------------------------------
export async function getClientCredits(): Promise<ClientCreditInfo> {
  return request<ClientCreditInfo>('/client/credits');
}

export interface TestKeysPayload {
  gemini_api_key?: string;
  groq_api_key?: string;
  groq_api_key_secondary?: string;
  tavily_api_key?: string;
}

export async function testApiKeys(payload: TestKeysPayload): Promise<TestKeysResponse> {
  return request<TestKeysResponse>('/health/test-keys', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}


