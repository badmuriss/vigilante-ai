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
    <div className="flex h-full flex-col rounded-lg border border-gray-800 bg-gray-900/50">
      <div className="border-b border-gray-800 px-4 py-3">
        <h3 className="text-sm font-semibold">EPIs Monitorados</h3>
      </div>
      <div className="flex-1 space-y-1 p-3">
        {error && (
          <p className="mb-2 text-xs text-red-400">{error}</p>
        )}
        {epis.map((epi) => (
          <label
            key={epi.key}
            className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm text-gray-300 transition-colors hover:bg-gray-800"
          >
            <input
              type="checkbox"
              checked={epi.active}
              onChange={() => handleToggle(epi.key)}
              className="h-4 w-4 rounded border-gray-600 bg-gray-800 text-green-500 accent-green-500"
            />
            {epi.label}
          </label>
        ))}
        {epis.length === 0 && !error && (
          <p className="py-4 text-center text-xs text-gray-500">
            Carregando EPIs...
          </p>
        )}
      </div>
    </div>
  );
}
