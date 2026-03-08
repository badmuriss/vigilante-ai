"use client";

import { useState, useEffect, useRef } from "react";
import { LoaderCircle, Radar, ShieldAlert } from "lucide-react";
import type { MonitorState } from "@/types";

const FRAME_URL = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/stream/frame`;
const FRAME_REFRESH_MS = 180;

interface VideoFeedProps {
  monitorState: MonitorState;
  fps: number;
}

export default function VideoFeed({ monitorState, fps }: VideoFeedProps) {
  const [hasError, setHasError] = useState(false);
  const [frameReady, setFrameReady] = useState(false);
  const [frameSrc, setFrameSrc] = useState("");
  const [streamKey, setStreamKey] = useState(0);
  const prevStateRef = useRef(monitorState);
  const lastFrameAtRef = useRef<number>(0);

  const isStopped = monitorState === "stopped";
  const streamReady = monitorState === "running" && fps > 0;
  const showLoading = !isStopped && !hasError && !frameReady;

  useEffect(() => {
    if (monitorState !== "stopped" && prevStateRef.current === "stopped") {
      setHasError(false);
      setFrameReady(false);
      setStreamKey((k) => k + 1);
    }

    if (monitorState === "stopped") {
      setHasError(false);
      setFrameReady(false);
      setFrameSrc("");
    }

    prevStateRef.current = monitorState;
  }, [monitorState]);

  useEffect(() => {
    if (isStopped) {
      return;
    }

    const refreshFrame = () => {
      setFrameSrc(`${FRAME_URL}?k=${streamKey}&t=${Date.now()}`);
    };

    refreshFrame();
    const intervalId = window.setInterval(refreshFrame, FRAME_REFRESH_MS);

    return () => window.clearInterval(intervalId);
  }, [isStopped, streamKey]);

  useEffect(() => {
    if (isStopped || !streamReady) {
      return;
    }

    const watchdogId = window.setInterval(() => {
      if (lastFrameAtRef.current === 0) {
        return;
      }

      if (Date.now() - lastFrameAtRef.current > 3000) {
        setHasError(true);
      }
    }, 1000);

    return () => window.clearInterval(watchdogId);
  }, [isStopped, streamReady]);

  return (
    <section className="surface-card overflow-hidden p-4 sm:p-5">
      <div className="mb-4 flex items-center justify-between gap-4">
        <div>
          <p className="eyebrow">Transmissão</p>
          <h3 className="mt-1 text-lg font-semibold text-[var(--foreground)]">Câmera operacional</h3>
        </div>
        <div className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--panel)] px-3 py-2 text-xs font-medium text-[var(--muted-strong)]">
          <Radar className="h-4 w-4 text-[var(--accent-strong)]" />
          Feed em tempo real
        </div>
      </div>

      <div className="relative aspect-video overflow-hidden rounded-[22px] border border-[var(--border)] bg-[radial-gradient(circle_at_top,rgba(18,103,66,0.08),transparent_48%),linear-gradient(180deg,#fbfcfb_0%,#eef3f1_100%)]">
        {isStopped ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 px-6 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full border border-[var(--border)] bg-white/90 shadow-sm">
              <ShieldAlert className="h-7 w-7 text-[var(--accent-strong)]" />
            </div>
            <div className="space-y-2">
              <p className="text-base font-medium text-[var(--foreground)]">
                A câmera está pronta para iniciar.
              </p>
              <p className="mx-auto max-w-md text-sm text-[var(--muted)]">
                Inicie o monitoramento para carregar o stream e começar a registrar violações de EPI.
              </p>
            </div>
          </div>
        ) : hasError ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
            <ShieldAlert className="h-8 w-8 text-[var(--danger)]" />
            <p className="text-sm font-medium text-[var(--foreground)]">Erro ao carregar o feed de vídeo.</p>
            <p className="max-w-sm text-sm text-[var(--muted)]">
              Aguarde alguns segundos ou reinicie o monitoramento para tentar novamente.
            </p>
          </div>
        ) : (
          <>
            {/* eslint-disable-next-line @next/next/no-img-element -- Live preview is refreshed with plain JPEG frames, which is not compatible with next/image optimization. */}
            <img
              key={streamKey}
              src={frameSrc}
              alt="Feed de vídeo de monitoramento"
              className="h-full w-full object-contain"
              onLoad={() => {
                lastFrameAtRef.current = Date.now();
                setFrameReady(true);
                setHasError(false);
              }}
              onError={() => {
                if (streamReady) {
                  setHasError(true);
                }
              }}
            />

            {showLoading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-[linear-gradient(180deg,rgba(248,250,249,0.84),rgba(236,242,239,0.94))] backdrop-blur-sm">
                <div className="flex h-16 w-16 items-center justify-center rounded-full border border-[var(--border)] bg-white/90 shadow-sm">
                  <LoaderCircle className="h-7 w-7 animate-spin text-[var(--accent-strong)]" />
                </div>
                <div className="space-y-1 text-center">
                  <p className="text-base font-medium text-[var(--foreground)]">
                    {monitorState === "starting" ? "Inicializando câmera" : "Carregando stream"}
                  </p>
                  <p className="text-sm text-[var(--muted)]">
                    O modelo e a captura estão sendo preparados.
                  </p>
                </div>
              </div>
            )}
          </>
        )}

        {!isStopped && !hasError && (
          <div className="absolute left-4 top-4 inline-flex items-center gap-2 rounded-full bg-slate-950/70 px-3 py-1.5 text-xs font-medium text-white shadow-lg">
            <span className={`h-2.5 w-2.5 rounded-full ${showLoading ? "bg-amber-400" : "bg-emerald-400"}`} />
            {showLoading ? "Preparando stream" : "Ao vivo"}
          </div>
        )}
      </div>
    </section>
  );
}
