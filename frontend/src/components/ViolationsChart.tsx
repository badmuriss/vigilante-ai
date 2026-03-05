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
      <div className="flex h-64 items-center justify-center rounded-lg border border-gray-800 bg-gray-900 text-gray-500">
        Sem dados de violacoes ainda
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
      <h3 className="mb-4 text-sm font-medium text-gray-400">
        Violacoes ao longo do tempo (ultimos 30 min)
      </h3>
      <ResponsiveContainer width="100%" height={256}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="time" stroke="#9ca3af" fontSize={12} />
          <YAxis stroke="#9ca3af" fontSize={12} allowDecimals={false} />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1f2937",
              border: "1px solid #374151",
              borderRadius: "0.5rem",
              color: "#f3f4f6",
            }}
          />
          <Line
            type="monotone"
            dataKey="violacoes"
            stroke="#ef4444"
            strokeWidth={2}
            dot={{ fill: "#ef4444", r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
