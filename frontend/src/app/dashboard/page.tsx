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
      <section className="surface-card p-6 sm:p-7">
        <p className="eyebrow">Resumo</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tight text-[var(--foreground)]">
          Dashboard operacional
        </h2>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--muted)] sm:text-base">
          Consolide o histórico da sessão atual e acompanhe o volume de violações ao longo do tempo.
        </p>
      </section>

      <StatsCards stats={stats} />
      <ViolationsChart timeline={stats?.violations_timeline ?? []} />
    </div>
  );
}
