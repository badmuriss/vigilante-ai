"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { Alert } from "@/types";
import { getAlerts, clearAlerts } from "@/lib/api";
import AlertCard from "./AlertCard";

export default function AlertPanel() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const prevCountRef = useRef(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const playNotification = useCallback(() => {
    if (!audioRef.current) {
      const ctx = new AudioContext();
      const oscillator = ctx.createOscillator();
      const gain = ctx.createGain();
      oscillator.connect(gain);
      gain.connect(ctx.destination);
      oscillator.frequency.value = 880;
      gain.gain.value = 0.3;
      oscillator.start();
      oscillator.stop(ctx.currentTime + 0.15);
    }
  }, []);

  useEffect(() => {
    let active = true;

    async function poll() {
      try {
        const data = await getAlerts();
        if (!active) return;
        setAlerts(data);

        if (soundEnabled && data.length > prevCountRef.current) {
          playNotification();
        }
        prevCountRef.current = data.length;
      } catch {
        // ignore fetch errors
      }
    }

    poll();
    const interval = setInterval(poll, 2000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [soundEnabled, playNotification]);

  async function handleClear() {
    await clearAlerts();
    setAlerts([]);
    prevCountRef.current = 0;
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-gray-800 bg-gray-900/50">
      <div className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold">Alertas</h3>
          {alerts.length > 0 && (
            <span className="rounded-full bg-red-500/20 px-2 py-0.5 text-xs font-medium text-red-400">
              {alerts.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSoundEnabled((v) => !v)}
            className="rounded p-1 text-xs text-gray-400 hover:bg-gray-800 hover:text-gray-200"
            title={soundEnabled ? "Desativar som" : "Ativar som"}
          >
            {soundEnabled ? "🔔" : "🔕"}
          </button>
          <button
            onClick={handleClear}
            className="rounded px-2 py-1 text-xs text-gray-400 hover:bg-gray-800 hover:text-gray-200"
          >
            Limpar
          </button>
        </div>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {alerts.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-500">
            Nenhum alerta registrado.
          </p>
        ) : (
          alerts.map((alert) => <AlertCard key={alert.id} alert={alert} />)
        )}
      </div>
    </div>
  );
}
