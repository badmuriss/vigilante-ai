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
    <div className="rounded-lg border border-gray-200 bg-gray-50">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3">
        <h3 className="text-sm font-semibold">EPIs Monitorados:</h3>
        {error && (
          <p className="text-xs text-red-400">{error}</p>
        )}
        {epis.map((epi) => (
          <label
            key={epi.key}
            className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-200"
          >
            <input
              type="checkbox"
              checked={epi.active}
              onChange={() => handleToggle(epi.key)}
              className="h-4 w-4 rounded border-gray-300 bg-white text-green-500 accent-green-500"
            />
            {epi.label}
          </label>
        ))}
        {epis.length === 0 && !error && (
          <p className="text-xs text-gray-500">Carregando EPIs...</p>
        )}
      </div>
    </div>
  );
}
