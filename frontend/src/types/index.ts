export type AlertFeedback = "correct" | "false_positive" | null;

export type AlertStatus = "pending" | "confirmed" | "rejected";

export interface Alert {
  id: string;
  timestamp: string;
  violation_type: string;
  confidence: number;
  frame_thumbnail: string;
  frame_image: string;
  // Raw (un-annotated) frame, only populated when the API caller is an
  // admin or supervisor. Used in the lightbox so reviewers can see what
  // the model actually saw.
  frame_raw_image?: string;
  missing_epis: string[];
  feedback?: AlertFeedback;
  feedback_at?: string | null;
  status?: AlertStatus;
}

export type MonitorState = "stopped" | "starting" | "running";

export interface EPIItem {
  key: string;
  label: string;
  active: boolean;
}

export interface EPIConfig {
  epis: EPIItem[];
}

export interface SystemStatus {
  camera_active: boolean;
  model_loaded: boolean;
  fps: number;
  uptime: number;
}

export interface ViolationTimelineEntry {
  timestamp: string;
  count: number;
}

export interface SessionStats {
  total_violations: number;
  session_duration_seconds: number;
  compliance_rate: number;
  violations_timeline: ViolationTimelineEntry[];
}

// --- Auth ---

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  role: "admin" | "supervisor" | "viewer";
  tenant_id: string;
  created_at: string;
}

// --- Cameras ---

export type SourceKind = "local" | "rtsp";

export interface CameraHealth {
  online: boolean;
  last_frame_at: number | null;
  consecutive_failures: number;
  reconnect_count: number;
  last_error: string | null;
}

export interface Camera {
  id: string;
  name: string;
  source_kind: SourceKind;
  rtsp_url: string | null;
  local_index: number | null;
  location: string | null;
  created_at: string;
  is_running: boolean;
  health: CameraHealth;
}

export interface CameraCreatePayload {
  name: string;
  source_kind: SourceKind;
  rtsp_url?: string | null;
  local_index?: number | null;
  location?: string | null;
}

export interface CameraUpdatePayload {
  name?: string;
  location?: string;
}

export interface ProbeResponse {
  ok: boolean;
  message: string;
}

// --- Notifications ---

export interface WhatsAppOperator {
  id: string;
  phone: string;
  name: string | null;
  enabled: boolean;
}

export interface WhatsAppConfig {
  enabled: boolean;
  include_image: boolean;
  // Whether the platform's shared Meta number is configured server-side (env).
  connected: boolean;
  operators: WhatsAppOperator[];
}

export interface WhatsAppConfigUpdate {
  enabled: boolean;
  include_image: boolean;
}

export interface WhatsAppTestResult {
  ok: boolean;
  message_id?: string | null;
  error?: string | null;
}

export interface TeamsConfig {
  enabled: boolean;
  has_webhook_url: boolean;
  channel_name: string | null;
  notify_on_confirmed: boolean;
}

export interface TeamsConfigUpdate {
  enabled: boolean;
  // `null` keeps the existing webhook URL, "" clears it, any string replaces it.
  webhook_url: string | null;
  channel_name: string | null;
  notify_on_confirmed: boolean;
}

export interface TeamsTestResult {
  ok: boolean;
  status_code?: number | null;
  error?: string | null;
}

// --- Chat / Assistente ---

export interface Citation {
  idx: number;
  doc_title: string;
  snippet: string;
  document_id?: string | null;
}

export interface ToolCallSummary {
  tool: string;
  args: Record<string, unknown>;
}

export type ChatRole = "user" | "assistant" | "tool";

export interface ChartPoint {
  label: string;
  value: number;
}

export interface ChartArtifact {
  kind: "chart";
  chart_type: "bar" | "line" | "pie";
  title: string;
  data: ChartPoint[];
}

export interface ChatMessage {
  role: ChatRole;
  content: string;
  citations?: Citation[];
  tool_calls?: ToolCallSummary[];
  charts?: ChartArtifact[];
}

export interface ConversationSummary {
  id: string;
  title: string | null;
  channel: "ui" | "whatsapp";
  updated_at: string;
  last_message_preview: string;
}

export interface ConversationDetail {
  id: string;
  title: string | null;
  channel: "ui" | "whatsapp";
  updated_at: string;
  messages: ChatMessage[];
}

export interface SendChatResponse {
  conversation_id: string;
  assistant_message: {
    role: "assistant";
    content: string;
    citations: Citation[];
    tool_calls: ToolCallSummary[];
    charts: ChartArtifact[];
  };
  latency_ms: number;
}
