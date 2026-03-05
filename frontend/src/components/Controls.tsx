"use client";

import { useState } from "react";
import { startStream, stopStream } from "@/lib/api";

export default function Controls() {
  const [loading, setLoading] = useState(false);

  async function handleStart() {
    setLoading(true);
    try {
      await startStream();
    } finally {
      setLoading(false);
    }
  }

  async function handleStop() {
    setLoading(true);
    try {
      await stopStream();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex gap-3">
      <button
        onClick={handleStart}
        disabled={loading}
        className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-green-700 disabled:opacity-50"
      >
        Iniciar
      </button>
      <button
        onClick={handleStop}
        disabled={loading}
        className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:opacity-50"
      >
        Parar
      </button>
    </div>
  );
}
