"use client";

import { useState } from "react";
import { LoaderCircle, Play, Square } from "lucide-react";
import { startStream, stopStream } from "@/lib/api";
import type { MonitorState } from "@/types";

interface ControlsProps {
  monitorState: MonitorState;
  onStartPending: () => void;
  onStartSuccess: () => void;
  onStartError: (message: string) => void;
  onStop: () => void;
}

export default function Controls({
  monitorState,
  onStartPending,
  onStartSuccess,
  onStartError,
  onStop,
}: ControlsProps) {
  const [loading, setLoading] = useState(false);
  const isStopped = monitorState === "stopped";
  const isStarting = monitorState === "starting";

  async function handleStart() {
    setLoading(true);
    onStartPending();

    try {
      try {
        if (!navigator.mediaDevices?.getUserMedia) {
          throw new Error("Seu navegador não oferece suporte ao acesso à câmera.");
        }
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        stream.getTracks().forEach((track) => track.stop());
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Permita o acesso à câmera para iniciar o monitoramento.";
        onStartError(message);
        return;
      }

      await startStream();
      onStartSuccess();
    } catch (err) {
      onStartError(
        err instanceof Error
          ? err.message
          : "Não foi possível iniciar o monitoramento."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleStop() {
    setLoading(true);
    try {
      await stopStream();
      onStop();
    } catch (err) {
      onStartError(
        err instanceof Error
          ? err.message
          : "Não foi possível parar o monitoramento."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-wrap gap-3">
      <button
        onClick={handleStart}
        disabled={loading || !isStopped}
        className="inline-flex min-w-36 items-center justify-center gap-2 rounded-full bg-[var(--accent-strong)] px-5 py-3 text-sm font-medium text-white shadow-[0_18px_40px_-24px_rgba(18,103,66,0.95)] transition hover:bg-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-55"
      >
        {isStarting ? (
          <LoaderCircle className="h-4 w-4 animate-spin" />
        ) : (
          <Play className="h-4 w-4" />
        )}
        {isStarting ? "Iniciando..." : "Iniciar"}
      </button>
      <button
        onClick={handleStop}
        disabled={loading || isStopped}
        className="inline-flex min-w-32 items-center justify-center gap-2 rounded-full border border-[var(--border-strong)] bg-white/[0.85] px-5 py-3 text-sm font-medium text-[var(--foreground)] transition hover:border-[var(--danger)] hover:text-[var(--danger)] disabled:cursor-not-allowed disabled:opacity-55"
      >
        <Square className="h-4 w-4" />
        Parar
      </button>
    </div>
  );
}
