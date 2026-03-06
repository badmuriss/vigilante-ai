"use client";

import type { SystemStatus } from "@/types";

interface StatusBarProps {
  status: SystemStatus | null;
  isRunning: boolean;
}

export default function StatusBar({ status, isRunning }: StatusBarProps) {
  return (
    <div className="flex items-center gap-4 text-sm">
      <div className="flex items-center gap-2">
        <span
          className={`inline-block h-2.5 w-2.5 rounded-full ${isRunning ? "bg-green-500" : "bg-gray-500"}`}
        />
        <span className="text-gray-600">
          {isRunning ? "Monitorando" : "Parado"}
        </span>
      </div>
      {isRunning && status && (
        <div className="text-gray-500">
          {status.fps.toFixed(1)} FPS
        </div>
      )}
    </div>
  );
}
