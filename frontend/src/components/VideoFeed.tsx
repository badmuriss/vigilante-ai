"use client";

import { useState, useEffect, useRef } from "react";

const STREAM_URL = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/stream`;

interface VideoFeedProps {
  isRunning: boolean;
}

export default function VideoFeed({ isRunning }: VideoFeedProps) {
  const [hasError, setHasError] = useState(false);
  const [streamKey, setStreamKey] = useState(0);
  const prevRunningRef = useRef(isRunning);

  useEffect(() => {
    if (isRunning && !prevRunningRef.current) {
      setHasError(false);
      setStreamKey((k) => k + 1);
    }
    prevRunningRef.current = isRunning;
  }, [isRunning]);

  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-lg border border-gray-200 bg-gray-100">
      {!isRunning ? (
        <div className="flex h-full items-center justify-center">
          <p className="px-4 text-center text-sm text-gray-400">
            Clique em Iniciar para comecar o monitoramento
          </p>
        </div>
      ) : hasError ? (
        <div className="flex h-full items-center justify-center">
          <p className="text-sm text-red-400">
            Erro ao carregar o feed de video.
          </p>
        </div>
      ) : (
        <img
          key={streamKey}
          src={`${STREAM_URL}?t=${Date.now()}`}
          alt="Video feed de monitoramento"
          className="h-full w-full object-contain"
          onError={() => setHasError(true)}
        />
      )}
    </div>
  );
}
