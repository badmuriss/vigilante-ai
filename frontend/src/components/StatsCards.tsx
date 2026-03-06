"use client";

import type { SessionStats } from "@/types";

interface StatsCardsProps {
  stats: SessionStats | null;
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

const cards = [
  {
    label: "Total de Violacoes",
    getValue: (s: SessionStats) => s.total_violations.toString(),
    color: "text-red-400",
    bg: "bg-red-500/10 border-red-500/20",
  },
  {
    label: "Tempo de Monitoramento",
    getValue: (s: SessionStats) => formatDuration(s.session_duration_seconds),
    color: "text-blue-400",
    bg: "bg-blue-500/10 border-blue-500/20",
  },
] as const;

export default function StatsCards({ stats }: StatsCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`rounded-lg border p-4 ${card.bg}`}
        >
          <p className="text-sm text-gray-600">{card.label}</p>
          <p className={`mt-1 text-2xl font-bold ${card.color}`}>
            {stats ? card.getValue(stats) : "--"}
          </p>
        </div>
      ))}
    </div>
  );
}
