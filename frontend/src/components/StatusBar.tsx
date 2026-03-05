"use client";

import { useEffect, useState } from "react";
import { getStatus } from "@/lib/api";
import type { SystemStatus } from "@/types";

export default function StatusBar() {
  const [status, setStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    const fetchStatus = () => {
      getStatus().then(setStatus).catch(() => setStatus(null));
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  const isOnline = status?.camera_active ?? false;

  return (
    <div className="flex items-center gap-4 rounded-lg border border-gray-800 bg-gray-900 px-4 py-2 text-sm">
      <div className="flex items-center gap-2">
        <span
          className={`inline-block h-2.5 w-2.5 rounded-full ${isOnline ? "bg-green-500" : "bg-red-500"}`}
        />
        <span className="text-gray-300">
          {isOnline ? "Online" : "Offline"}
        </span>
      </div>
      {status && (
        <div className="text-gray-500">
          {status.fps.toFixed(1)} FPS
        </div>
      )}
    </div>
  );
}
