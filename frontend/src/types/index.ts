export interface Alert {
  id: string;
  timestamp: string;
  violation_type: string;
  confidence: number;
  frame_thumbnail: string;
}

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
