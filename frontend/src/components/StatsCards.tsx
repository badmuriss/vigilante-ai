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
    label: "Total de violações",
    getValue: (s: SessionStats) => s.total_violations.toString(),
    color: "text-rose-700",
    bg: "bg-rose-50 border-rose-100",
  },
  {
    label: "Tempo de monitoramento",
    getValue: (s: SessionStats) => formatDuration(s.session_duration_seconds),
    color: "text-sky-700",
    bg: "bg-sky-50 border-sky-100",
  },
] as const;

export default function StatsCards({ stats }: StatsCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`rounded-[22px] border p-5 shadow-[0_18px_35px_-30px_rgba(15,23,42,0.6)] ${card.bg}`}
        >
          <p className="text-sm text-[var(--muted-strong)]">{card.label}</p>
          <p className={`mt-1 text-2xl font-bold ${card.color}`}>
            {stats ? card.getValue(stats) : "--"}
          </p>
        </div>
      ))}
    </div>
  );
}
