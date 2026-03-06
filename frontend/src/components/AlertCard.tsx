"use client";

import type { Alert } from "@/types";

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function parseViolation(violationType: string): { epiName: string; suffix: string } {
  // violation_type comes as "Capacete ausente", "Luvas ausentes", etc.
  const parts = violationType.split(" ");
  const suffix = parts.pop() ?? "";
  const epiName = parts.join(" ") || violationType;
  return { epiName, suffix };
}

export default function AlertCard({ alert }: { alert: Alert }) {
  const { epiName, suffix } = parseViolation(alert.violation_type);
  const confidence = Math.round(alert.confidence * 100);

  return (
    <div className="flex gap-3 rounded-lg border border-gray-200 bg-white p-3">
      {alert.frame_thumbnail && (
        <img
          src={`data:image/jpeg;base64,${alert.frame_thumbnail}`}
          alt="Thumbnail da violacao"
          className="h-16 w-20 flex-shrink-0 rounded object-cover"
        />
      )}
      <div className="flex flex-col justify-center gap-1 overflow-hidden">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-800">{epiName}</span>
          <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-600">
            {suffix}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">
            {formatTimestamp(alert.timestamp)}
          </span>
          {confidence > 0 && (
            <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">
              {confidence}%
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
