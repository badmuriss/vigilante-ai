"use client";

import type { ViolationTimelineEntry } from "@/types";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface ViolationsChartProps {
  timeline: ViolationTimelineEntry[];
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

export default function ViolationsChart({ timeline }: ViolationsChartProps) {
  const data = timeline.map((entry) => ({
    time: formatTime(entry.timestamp),
    violacoes: entry.count,
  }));

  if (data.length === 0) {
    return (
      <div className="surface-card flex h-64 items-center justify-center text-[var(--muted)]">
        Sem dados de violações ainda
      </div>
    );
  }

  return (
    <div className="surface-card p-5">
      <p className="eyebrow">Histórico</p>
      <h3 className="mb-4 mt-1 text-base font-semibold text-[var(--foreground)]">
        Violações ao longo do tempo
      </h3>
      <ResponsiveContainer width="100%" height={256}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#d6dfdb" />
          <XAxis dataKey="time" stroke="#6b7280" fontSize={12} />
          <YAxis stroke="#6b7280" fontSize={12} allowDecimals={false} />
          <Tooltip
            contentStyle={{
              backgroundColor: "#ffffff",
              border: "1px solid #d6dfdb",
              borderRadius: "1rem",
              color: "#374151",
              boxShadow: "0 20px 45px -30px rgba(15, 23, 42, 0.55)",
            }}
          />
          <Line
            type="monotone"
            dataKey="violacoes"
            stroke="#d44444"
            strokeWidth={2}
            dot={{ fill: "#d44444", r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
