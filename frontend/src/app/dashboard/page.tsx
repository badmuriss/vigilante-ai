"use client";

import { useEffect, useState, useCallback } from "react";
import type { SessionStats } from "@/types";
import { getStats } from "@/lib/api";
import StatsCards from "@/components/StatsCards";
import ViolationsChart from "@/components/ViolationsChart";

export default function DashboardPage() {
  const [stats, setStats] = useState<SessionStats | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      const data = await getStats();
      setStats(data);
    } catch {
      // Backend may be offline
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">Dashboard</h2>
      <StatsCards stats={stats} />
      <ViolationsChart timeline={stats?.violations_timeline ?? []} />
    </div>
  );
}
