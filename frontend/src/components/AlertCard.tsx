"use client";

import type { Alert } from "@/types";

const VIOLATION_LABELS: Record<string, string> = {
  no_safety_glasses: "Sem oculos",
  no_hardhat: "Sem capacete",
};

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function AlertCard({ alert }: { alert: Alert }) {
  const label = VIOLATION_LABELS[alert.violation_type] ?? alert.violation_type;
  const confidence = Math.round(alert.confidence * 100);

  return (
    <div className="flex gap-3 rounded-lg border border-gray-800 bg-gray-900 p-3">
      {alert.frame_thumbnail && (
        <img
          src={`data:image/jpeg;base64,${alert.frame_thumbnail}`}
          alt="Thumbnail da violacao"
          className="h-16 w-20 flex-shrink-0 rounded object-cover"
        />
      )}
      <div className="flex flex-col justify-center gap-1 overflow-hidden">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-red-400">{label}</span>
          <span className="rounded bg-gray-800 px-1.5 py-0.5 text-xs text-gray-400">
            {confidence}%
          </span>
        </div>
        <span className="text-xs text-gray-500">
          {formatTimestamp(alert.timestamp)}
        </span>
      </div>
    </div>
  );
}
