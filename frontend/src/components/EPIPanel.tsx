"use client";

import { useEffect, useState, useCallback } from "react";
import type { EPIItem } from "@/types";
import { getEPIConfig, updateEPIConfig } from "@/lib/api";

export default function EPIPanel() {
  const [epis, setEpis] = useState<EPIItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEPIConfig()
      .then((config) => setEpis(config.epis))
      .catch((err) => setError(err.message));
  }, []);

  const handleToggle = useCallback(
    async (key: string) => {
      const updated = epis.map((epi) =>
        epi.key === key ? { ...epi, active: !epi.active } : epi
      );
      setEpis(updated);

      const activeKeys = updated.filter((e) => e.active).map((e) => e.key);

      try {
        const config = await updateEPIConfig(activeKeys);
        setEpis(config.epis);
      } catch (err) {
        // Revert on failure
        setEpis(epis);
        setError(err instanceof Error ? err.message : "Erro ao atualizar EPIs");
      }
    },
    [epis]
  );

  return (
    <section className="surface-card p-5">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <div>
          <p className="eyebrow">Configuração</p>
          <h3 className="mt-1 text-base font-semibold text-[var(--foreground)]">EPIs monitorados</h3>
        </div>
        {error && (
          <p className="rounded-full bg-rose-100 px-3 py-1 text-xs font-medium text-rose-700">{error}</p>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        {epis.map((epi) => (
          <label
            key={epi.key}
            className={`flex cursor-pointer items-center gap-3 rounded-full border px-4 py-2.5 text-sm transition ${
              epi.active
                ? "border-[var(--accent-strong)] bg-emerald-50 text-[var(--foreground)]"
                : "border-[var(--border)] bg-white/80 text-[var(--muted-strong)] hover:border-[var(--border-strong)]"
            }`}
          >
            <input
              type="checkbox"
              checked={epi.active}
              onChange={() => handleToggle(epi.key)}
              className="h-4 w-4 rounded border-[var(--border-strong)] bg-white text-[var(--accent-strong)] accent-[var(--accent-strong)]"
            />
            {epi.label}
          </label>
        ))}
        {epis.length === 0 && !error && (
          <p className="text-sm text-[var(--muted)]">Carregando EPIs...</p>
        )}
      </div>
    </section>
  );
}
