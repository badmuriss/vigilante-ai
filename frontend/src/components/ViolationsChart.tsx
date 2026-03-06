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
      <div className="flex h-64 items-center justify-center rounded-lg border border-gray-200 bg-gray-50 text-gray-500">
        Sem dados de violacoes ainda
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
      <h3 className="mb-4 text-sm font-medium text-gray-600">
        Violacoes ao longo do tempo (ultimos 30 min)
      </h3>
      <ResponsiveContainer width="100%" height={256}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="time" stroke="#6b7280" fontSize={12} />
          <YAxis stroke="#6b7280" fontSize={12} allowDecimals={false} />
          <Tooltip
            contentStyle={{
              backgroundColor: "#ffffff",
              border: "1px solid #e5e7eb",
              borderRadius: "0.5rem",
              color: "#374151",
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
