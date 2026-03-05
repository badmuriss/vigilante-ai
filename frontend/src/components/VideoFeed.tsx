"use client";

import { useState } from "react";

const STREAM_URL = "http://localhost:8000/api/stream";

export default function VideoFeed() {
  const [hasError, setHasError] = useState(false);

  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-lg border border-gray-800 bg-gray-900">
      {hasError ? (
        <div className="flex h-full items-center justify-center">
          <p className="text-sm text-gray-500">
            Feed indisponivel. Inicie o monitoramento.
          </p>
        </div>
      ) : (
        <img
          src={STREAM_URL}
          alt="Video feed de monitoramento"
          className="h-full w-full object-contain"
          onError={() => setHasError(true)}
          onLoad={() => setHasError(false)}
        />
      )}
    </div>
  );
}
