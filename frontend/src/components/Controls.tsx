"use client";

import { useState } from "react";
import { startStream, stopStream } from "@/lib/api";

interface ControlsProps {
  isRunning: boolean;
  onStart: () => void;
  onStop: () => void;
}

export default function Controls({ isRunning, onStart, onStop }: ControlsProps) {
  const [loading, setLoading] = useState(false);

  async function handleStart() {
    setLoading(true);
    try {
      // Solicita permissão da câmera no navegador
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        // Fecha o stream imediatamente pois o processamento ocorre no backend
        stream.getTracks().forEach(track => track.stop());
      } catch (err) {
        console.error("Permissão da câmera negada:", err);
        alert("Para iniciar o monitoramento, você precisa permitir o acesso à câmera no navegador.");
        return;
      }

      await startStream();
      onStart();
    } catch {
      // Error handled silently; status poll will update state
    } finally {
      setLoading(false);
    }
  }

  async function handleStop() {
    setLoading(true);
    try {
      await stopStream();
      onStop();
    } catch {
      // Error handled silently; status poll will update state
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex gap-3">
      <button
        onClick={handleStart}
        disabled={loading || isRunning}
        className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-green-700 disabled:opacity-50"
      >
        Iniciar
      </button>
      <button
        onClick={handleStop}
        disabled={loading || !isRunning}
        className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:opacity-50"
      >
        Parar
      </button>
    </div>
  );
}
