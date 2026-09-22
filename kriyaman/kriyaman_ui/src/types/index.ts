export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  dependencies: Record<string, string>;
}

export interface Session {
  session_id: string;
  memory_principal_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  metadata: Record<string, any>;
}

export interface Answer {
  answer_text: string;
  citation_ids: string[];
  confidence: number;
  needs_follow_up: boolean;
}

export interface Turn {
  turn_id: string;
  run_id: string;
  user_query: string;
  answer: Answer | null;
  status: string;
  created_at: string;
}

export interface SessionDetail extends Session {
  turns: Turn[];
}

export interface EvidenceItem {
  evidence_id: string;
  source_type: string;
  source_id: string;
  content: string;
  retrieval_method: string;
  retrieval_score: number | null;
}

export interface ExecutionBudgets {
  max_retrieval_iterations: number;
  max_tool_calls: number;
  max_latency_ms: number;
  max_input_tokens: number;
  max_output_tokens: number;
}

export interface ExecutionUsage {
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  total_latency_ms?: number;
  estimated_cost_usd?: number | string;
  cache_hit?: boolean;
  [key: string]: any;
}

export interface RunResponse {
  run_id: string;
  session_id: string;
  status: string;
  poll_url: string;
  events_url: string;
  answer?: Answer | null;
  evidence: EvidenceItem[];
  evidence_assessment?: Record<string, any> | null;
  budgets?: Record<string, any> | null;
  usage?: ExecutionUsage | null;
  failure?: Record<string, any> | null;
  created_at?: string;
  completed_at?: string;
}

export interface RunEvent {
  sequence: number;
  event_type: string;
  payload: Record<string, any>;
  timestamp: string;
}

export interface DocumentItem {
  document_id: string;
  session_id?: string | null;
  name: string;
  mime_type: string;
  sha256: string;
  status: string;
  chunk_count: number;
  created_at: string;
}

export interface MemoryItem {
  memory_id: string;
  memory_principal_id: string;
  kind: string;
  content: string;
  status: string;
  created_at: string;
}

export type AppNavView = 'chat' | 'knowledge' | 'memory' | 'settings';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  runId?: string;
  evidence?: EvidenceItem[];
  citations?: string[];
  metrics?: ExecutionUsage;
  budgets?: ExecutionBudgets;
  status?: string;
  assessment?: Record<string, any> | null;
  isStreaming?: boolean;
  liveStatus?: string;
  events?: RunEvent[];
}

export interface LocalSessionMeta {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  previewText?: string;
}

export interface UserSettings {
  apiBaseUrl: string;
  responseMode: 'concise' | 'detailed';
  enableWebFallback: boolean;
  budgets: ExecutionBudgets;
  density: 'comfortable' | 'compact';
  showTelemetryByDefault: boolean;
}

