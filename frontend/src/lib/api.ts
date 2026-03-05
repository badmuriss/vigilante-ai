import type { Alert, SystemStatus, SessionStats } from "@/types";

const API_BASE = "http://localhost:8000";

export async function getStatus(): Promise<SystemStatus> {
  const res = await fetch(`${API_BASE}/api/status`);
  return res.json();
}

export async function getAlerts(): Promise<Alert[]> {
  const res = await fetch(`${API_BASE}/api/alerts`);
  const data = await res.json();
  return data.alerts;
}

export async function clearAlerts(): Promise<{ cleared: boolean }> {
  const res = await fetch(`${API_BASE}/api/alerts`, { method: "DELETE" });
  return res.json();
}

export async function getStats(): Promise<SessionStats> {
  const res = await fetch(`${API_BASE}/api/stats`);
  return res.json();
}

export async function startStream(): Promise<void> {
  await fetch(`${API_BASE}/api/stream/start`, { method: "POST" });
}

export async function stopStream(): Promise<void> {
  await fetch(`${API_BASE}/api/stream/stop`, { method: "POST" });
}
