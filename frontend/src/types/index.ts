export type ViolationType = "no_safety_glasses" | "no_hardhat";

export interface Alert {
  id: string;
  timestamp: string;
  violation_type: ViolationType;
  confidence: number;
  frame_thumbnail: string;
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
