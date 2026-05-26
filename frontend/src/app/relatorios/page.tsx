"use client";

import { useEffect, useMemo, useState } from "react";
import { Download, BarChart3 } from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from "recharts";

import { AppShell } from "@/components/AppShell";
import AlertDetailsModal from "@/components/AlertDetailsModal";
import DailyAlertsModal from "@/components/DailyAlertsModal";
import ExportPdfDialog from "@/components/ExportPdfDialog";
import { listCameras, listCameraAlerts, getCameraStats, getMe, type AlertStatusFilter } from "@/lib/api";
import { exportReportPdf } from "@/lib/exportReportPdf";
import type { Camera, Alert, SessionStats, User } from "@/types";

interface CameraAggregate {
  camera: Camera;
  alerts: Alert[];
  stats: SessionStats | null;
}

interface AlertWithCamera extends Alert {
  cameraName: string;
}

const PERIODS = [
  { value: "7", label: "Últimos 7 dias" },
  { value: "30", label: "Últimos 30 dias" },
  { value: "all", label: "Todo o período" },
] as const;

const REPORT_ALERT_PAGE_SIZE = 200;
const REVIEWER_ROLES: User["role"][] = ["admin", "supervisor"];

function dateKey(iso: string): string {
  return new Date(iso).toISOString().slice(0, 10);
}

function formatDayLabel(key: string): string {
  return key.slice(8, 10) + "/" + key.slice(5, 7);
}

function formatFullDate(key: string): string {
  const d = new Date(`${key}T00:00:00`);
  return d.toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

export default function RelatoriosPage() {
  const [data, setData] = useState<CameraAggregate[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<typeof PERIODS[number]["value"]>("30");
  const [alertStatus, setAlertStatus] = useState<AlertStatusFilter>("confirmed");
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [exportOpen, setExportOpen] = useState(false);

  async function load() {
    try {
      const user = await getMe();
      const status: AlertStatusFilter = REVIEWER_ROLES.includes(user.role) ? "all" : "confirmed";
      setAlertStatus(status);
      const cameras = await listCameras();
      const results = await Promise.all(
        cameras.map(async (camera) => {
          const [alerts, stats] = await Promise.all([
            listCameraAlerts(camera.id, 1, REPORT_ALERT_PAGE_SIZE, status).catch(() => []),
            getCameraStats(camera.id).catch(() => null),
          ]);
          return { camera, alerts, stats };
        }),
      );
      setData(results);
    } catch {
      // noop
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  const cutoff = useMemo(() => {
    if (period === "all") return 0;
    const days = parseInt(period, 10);
    return Date.now() - days * 86400_000;
  }, [period]);

  const filteredAlerts = useMemo<AlertWithCamera[]>(() => {
    return data.flatMap((d) =>
      d.alerts
        .filter((a) => new Date(a.timestamp).getTime() >= cutoff)
        .map((a) => ({ ...a, cameraName: d.camera.name })),
    );
  }, [data, cutoff]);

  // KPIs
  const totalAlerts = filteredAlerts.length;
  const pendingAlerts = filteredAlerts.filter((a) => a.status === "pending" || a.feedback === null).length;
  const confirmedAlerts = filteredAlerts.filter((a) => a.status === "confirmed" || a.feedback === "correct").length;
  const activeCameras = data.filter((d) => d.camera.health.online && d.camera.is_running).length;
  const totalCameras = data.length;
  const averageCompliance = useMemo(() => {
    const valid = data.map((d) => d.stats?.compliance_rate ?? null).filter((v): v is number => v !== null);
    if (valid.length === 0) return null;
    return valid.reduce((a, b) => a + b, 0) / valid.length;
  }, [data]);
  const reviewKpi =
    alertStatus === "all"
      ? { label: "Pendentes de revisão", value: pendingAlerts.toString() }
      : { label: "Violações confirmadas", value: confirmedAlerts.toString() };

  // Bar chart: alerts per day — keep the ISO key for click navigation.
  const alertsByDay = useMemo(() => {
    const map = new Map<string, number>();
    const days = period === "all" ? 30 : parseInt(period, 10);
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      map.set(dateKey(d.toISOString()), 0);
    }
    for (const a of filteredAlerts) {
      const key = dateKey(a.timestamp);
      if (map.has(key)) map.set(key, (map.get(key) ?? 0) + 1);
    }
    return Array.from(map.entries()).map(([key, count]) => ({
      key,
      day: formatDayLabel(key),
      count,
    }));
  }, [filteredAlerts, period]);

  // Distribution by violation type
  const distribution = useMemo(() => {
    const map = new Map<string, number>();
    for (const a of filteredAlerts) {
      map.set(a.violation_type, (map.get(a.violation_type) ?? 0) + 1);
    }
    return Array.from(map.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6);
  }, [filteredAlerts]);

  // Top cameras
  const topCameras = useMemo(() => {
    const map = new Map<string, number>();
    for (const a of filteredAlerts) {
      map.set(a.cameraName, (map.get(a.cameraName) ?? 0) + 1);
    }
    return Array.from(map.entries()).sort((a, b) => b[1] - a[1]).slice(0, 5);
  }, [filteredAlerts]);

  const dailyAlerts = useMemo<AlertWithCamera[]>(() => {
    if (!selectedDay) return [];
    return filteredAlerts
      .filter((a) => dateKey(a.timestamp) === selectedDay)
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }, [filteredAlerts, selectedDay]);

  const periodLabel = PERIODS.find((p) => p.value === period)?.label ?? "Período";

  async function handleExport({ includeImages }: { includeImages: boolean }) {
    const sortedAlerts = [...filteredAlerts].sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
    );
    await exportReportPdf({
      periodLabel,
      generatedAt: new Date(),
      includeImages,
      kpis: [
        { label: "Total de alertas", value: totalAlerts.toString() },
        {
          label: "Conformidade média",
          value: averageCompliance !== null ? `${formatRate(averageCompliance)}%` : "—",
        },
        { label: reviewKpi.label, value: reviewKpi.value },
        { label: "Câmeras ativas", value: `${activeCameras}/${totalCameras}` },
      ],
      byDay: alertsByDay.map(({ day, count }) => ({ day, count })),
      distribution,
      topCameras,
      alerts: sortedAlerts.map((a) => {
        const d = new Date(a.timestamp);
        return {
          date: d.toLocaleDateString("pt-BR"),
          time: d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }),
          camera: a.cameraName,
          type: a.violation_type,
          confidence: a.confidence,
          thumbnail: includeImages ? a.frame_thumbnail || null : null,
        };
      }),
    });
  }

  return (
    <AppShell
      title="Relatórios e indicadores"
      subtitle={`Visão consolidada · ${periodLabel.toLowerCase()}`}
      actions={
        <>
          <select value={period} onChange={(e) => setPeriod(e.target.value as typeof PERIODS[number]["value"])} className="input">
            {PERIODS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
          <button
            type="button"
            className="btn-secondary text-sm"
            onClick={() => setExportOpen(true)}
            disabled={loading || totalAlerts === 0}
            title={totalAlerts === 0 ? "Nenhum alerta no período para exportar" : "Exportar relatório em PDF"}
          >
            <Download size={14} strokeWidth={1.8} />
            Exportar PDF
          </button>
        </>
      }
    >
      {loading ? (
        <p className="text-sm text-text-muted">Carregando relatórios…</p>
      ) : (
        <div className="space-y-6">
          {/* KPI cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KPI label="Total de alertas" value={totalAlerts.toString()} />
            <KPI
              label="Conformidade média"
              value={averageCompliance !== null ? `${formatRate(averageCompliance)}%` : "—"}
            />
            <KPI label={reviewKpi.label} value={reviewKpi.value} />
            <KPI label="Câmeras ativas" value={`${activeCameras}/${totalCameras}`} />
          </div>

          {/* Bar chart */}
          <div className="card p-5">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="eyebrow">Atividade</p>
                <h3 className="mt-1 text-base font-semibold text-text">Alertas por dia</h3>
                <p className="mt-1 text-xs text-text-muted">
                  Clique em uma barra para ver os alertas do dia.
                </p>
              </div>
              <BarChart3 size={18} className="text-text-muted" />
            </div>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={alertsByDay} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e8e7e4" vertical={false} />
                <XAxis dataKey="day" stroke="#8a8a8a" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="#8a8a8a" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip
                  cursor={{ fill: "rgba(17,17,17,0.04)" }}
                  contentStyle={{
                    backgroundColor: "#ffffff",
                    border: "1px solid #e8e7e4",
                    borderRadius: 10,
                    fontSize: 12,
                  }}
                  formatter={(value) => {
                    const n = Number(value ?? 0);
                    return [`${n} ${n === 1 ? "alerta" : "alertas"}`, "Ocorrências"];
                  }}
                  labelFormatter={(label) => `Dia ${label ?? ""}`}
                />
                <Bar
                  dataKey="count"
                  fill="#111111"
                  radius={[4, 4, 0, 0]}
                  cursor="pointer"
                  onClick={(entry) => {
                    const payload = entry as unknown as { key?: string; payload?: { key?: string } };
                    const key = payload.key ?? payload.payload?.key;
                    if (key) setSelectedDay(key);
                  }}
                >
                  {alertsByDay.map((entry) => (
                    <Cell
                      key={entry.key}
                      fill={selectedDay === entry.key ? "#dc2626" : "#111111"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Distribution + ranking */}
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="card p-5">
              <p className="eyebrow">Distribuição</p>
              <h3 className="mt-1 text-base font-semibold text-text">Por tipo de violação</h3>
              <ul className="mt-4 space-y-2">
                {distribution.length === 0 ? (
                  <li className="py-4 text-center text-sm text-text-muted">Sem dados.</li>
                ) : (
                  distribution.map(([type, count]) => {
                    const pct = totalAlerts > 0 ? Math.round((count / totalAlerts) * 100) : 0;
                    return (
                      <li key={type}>
                        <div className="mb-1 flex items-center justify-between text-sm">
                          <span className="text-text">{type}</span>
                          <span className="text-text-muted mono-num">
                            {count} ({pct}%)
                          </span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded-full bg-bg-sunken">
                          <div className="h-full bg-text" style={{ width: `${pct}%` }} />
                        </div>
                      </li>
                    );
                  })
                )}
              </ul>
            </div>

            <div className="card p-5">
              <p className="eyebrow">Ranking</p>
              <h3 className="mt-1 text-base font-semibold text-text">Câmeras com mais ocorrências</h3>
              <ul className="mt-4 space-y-2">
                {topCameras.length === 0 ? (
                  <li className="py-4 text-center text-sm text-text-muted">Sem dados.</li>
                ) : (
                  topCameras.map(([name, count]) => {
                    const max = topCameras[0][1];
                    const pct = max > 0 ? Math.round((count / max) * 100) : 0;
                    return (
                      <li key={name}>
                        <div className="mb-1 flex items-center justify-between text-sm">
                          <span className="truncate text-text">{name}</span>
                          <span className="text-text-muted mono-num">{count}</span>
                        </div>
                        <div className="h-1.5 overflow-hidden rounded-full bg-bg-sunken">
                          <div className="h-full bg-text" style={{ width: `${pct}%` }} />
                        </div>
                      </li>
                    );
                  })
                )}
              </ul>
            </div>
          </div>
        </div>
      )}

      <DailyAlertsModal
        open={selectedDay !== null}
        dateLabel={selectedDay ? formatFullDate(selectedDay) : ""}
        alerts={dailyAlerts}
        onClose={() => setSelectedDay(null)}
        onSelectAlert={(alert) => setSelectedAlert(alert)}
      />

      {selectedAlert && (
        <AlertDetailsModal
          alert={selectedAlert}
          onClose={() => setSelectedAlert(null)}
        />
      )}

      <ExportPdfDialog
        open={exportOpen}
        alertCount={totalAlerts}
        onClose={() => setExportOpen(false)}
        onExport={handleExport}
      />
    </AppShell>
  );
}

function formatRate(v: number): string {
  const pct = v <= 1 ? v * 100 : v;
  return Math.max(0, Math.min(100, pct)).toFixed(0);
}

function KPI({ label, value }: { label: string; value: string }) {
  return (
    <div className="card p-5">
      <p className="eyebrow">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-text mono-num">{value}</p>
    </div>
  );
}
