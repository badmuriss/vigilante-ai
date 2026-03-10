"use client";

import { useState, useEffect, useCallback } from "react";
import VideoFeed from "@/components/VideoFeed";
import StatusBar from "@/components/StatusBar";
import Controls from "@/components/Controls";
import AlertPanel from "@/components/AlertPanel";
import EPIPanel from "@/components/EPIPanel";
import { getStatus } from "@/lib/api";
import type { MonitorState, SystemStatus } from "@/types";

export default function Home() {
  const [monitorState, setMonitorState] = useState<MonitorState>("stopped");
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStatus = () => {
      getStatus()
        .then((s) => {
          setStatus(s);
          setMonitorState((current) =>
            s.camera_active ? "running" : current === "starting" ? "starting" : "stopped"
          );
        })
        .catch(() => {
          setStatus(null);
          setMonitorState((current) => (current === "starting" ? current : "stopped"));
        });
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (monitorState !== "starting") {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setMonitorState("stopped");
      setActionError("A câmera demorou demais para responder. Verifique se o backend e a webcam estão disponíveis.");
    }, 15000);

    return () => window.clearTimeout(timeoutId);
  }, [monitorState]);

  const handleStartPending = useCallback(() => {
    setActionError(null);
    setMonitorState("starting");
  }, []);

  const handleStartSuccess = useCallback(() => {
    setActionError(null);
    setMonitorState("running");
  }, []);

  const handleActionError = useCallback((message: string) => {
    setActionError(message);
    setMonitorState("stopped");
  }, []);

  const handleStop = useCallback(() => {
    setActionError(null);
    setMonitorState("stopped");
  }, []);

  return (
    <div className="space-y-6">
      <section className="surface-card relative overflow-hidden p-6 sm:p-7">
        <div className="relative flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="space-y-4">
            <div>
              <p className="eyebrow">Centro de monitoramento</p>
              <h2 className="mt-2 max-w-3xl text-3xl font-semibold tracking-tight text-[var(--foreground)] sm:text-4xl">
                Operação em tempo real com feedback visual claro desde o primeiro segundo.
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--muted)] sm:text-base">
                Acompanhe o feed, o desempenho do processamento e os incidentes recentes sem perder contexto quando a câmera ainda estiver inicializando.
              </p>
            </div>

            <StatusBar status={status} monitorState={monitorState} />

            {actionError && (
              <div className="inline-flex rounded-full border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-medium text-rose-700">
                {actionError}
              </div>
            )}
          </div>

          <Controls
            monitorState={monitorState}
            onStartPending={handleStartPending}
            onStartSuccess={handleStartSuccess}
            onStartError={handleActionError}
            onStop={handleStop}
          />
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.65fr)_360px]">
        <div className="min-w-0 space-y-6">
          <VideoFeed monitorState={monitorState} fps={status?.fps ?? 0} />
          <EPIPanel />
        </div>
        <div className="min-w-0 xl:sticky xl:top-6 xl:h-[calc(100vh-8.5rem)]">
          <AlertPanel />
        </div>
      </div>
    </div>
  );
}
