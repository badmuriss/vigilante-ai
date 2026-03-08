"use client";

import { Activity, Cpu, LoaderCircle, TimerReset } from "lucide-react";
import type { MonitorState, SystemStatus } from "@/types";

interface StatusBarProps {
  status: SystemStatus | null;
  monitorState: MonitorState;
}

const STATE_LABELS: Record<MonitorState, string> = {
  stopped: "Parado",
  starting: "Inicializando",
  running: "Monitorando",
};

export default function StatusBar({ status, monitorState }: StatusBarProps) {
  const isRunning = monitorState === "running";
  const isStarting = monitorState === "starting";

  return (
    <div className="flex flex-wrap items-center gap-2 text-sm text-[var(--muted-strong)]">
      <div className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-white/70 px-3 py-2">
        {isStarting ? (
          <LoaderCircle className="h-4 w-4 animate-spin text-[var(--accent-strong)]" />
        ) : (
          <Activity
            className={`h-4 w-4 ${isRunning ? "text-[var(--accent-strong)]" : "text-slate-400"}`}
          />
        )}
        <span className="font-medium text-[var(--foreground)]">{STATE_LABELS[monitorState]}</span>
      </div>

      <div className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-white/70 px-3 py-2">
        <Cpu className="h-4 w-4 text-slate-500" />
        <span>{status?.model_loaded ? "Modelo pronto" : "Modelo pendente"}</span>
      </div>

      <div className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-white/70 px-3 py-2">
        <TimerReset className="h-4 w-4 text-slate-500" />
        <span>{isRunning && status ? `${status.fps.toFixed(1)} FPS` : "Aguardando feed"}</span>
      </div>
    </div>
  );
}
