"use client";

import Image from "next/image";
import { ChevronRight, Clock3, Eye } from "lucide-react";
import type { Alert } from "@/types";

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function parseViolation(violationType: string): { epiName: string; suffix: string } {
  const parts = violationType.split(" ");
  const suffix = parts.pop() ?? "";
  const epiName = parts.join(" ") || violationType;
  return { epiName, suffix };
}

interface AlertCardProps {
  alert: Alert;
  onSelect: (alert: Alert) => void;
}

export default function AlertCard({ alert, onSelect }: AlertCardProps) {
  const { epiName, suffix } = parseViolation(alert.violation_type);
  const confidence = Math.round(alert.confidence * 100);
  const previewMissing = alert.missing_epis.slice(0, 2);

  return (
    <button
      type="button"
      onClick={() => onSelect(alert)}
      className="group flex w-full items-center gap-3 rounded-[20px] border border-[var(--border)] bg-white/[0.88] p-3 text-left transition hover:-translate-y-0.5 hover:border-[var(--border-strong)] hover:shadow-[0_18px_35px_-28px_rgba(15,23,42,0.65)]"
    >
      {alert.frame_thumbnail ? (
        <Image
          src={`data:image/jpeg;base64,${alert.frame_thumbnail}`}
          alt="Miniatura da violação"
          width={96}
          height={80}
          unoptimized
          className="h-20 w-24 flex-shrink-0 rounded-2xl border border-[var(--border)] object-cover"
        />
      ) : (
        <div className="flex h-20 w-24 flex-shrink-0 items-center justify-center rounded-2xl border border-dashed border-[var(--border)] bg-[var(--panel)] text-[var(--muted)]">
          <Eye className="h-5 w-5" />
        </div>
      )}

      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-[var(--foreground)]">{epiName}</p>
            <div className="mt-1 flex flex-wrap gap-2">
              <span className="rounded-full bg-amber-100 px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-amber-700">
                {suffix}
              </span>
              {previewMissing.map((item) => (
                <span
                  key={item}
                  className="rounded-full border border-rose-200 bg-rose-50 px-2 py-1 text-[11px] font-medium text-rose-700"
                >
                  {item}
                </span>
              ))}
            </div>
          </div>

          <ChevronRight className="mt-0.5 h-4 w-4 flex-shrink-0 text-[var(--muted)] transition group-hover:translate-x-0.5 group-hover:text-[var(--foreground)]" />
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--muted)]">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--panel)] px-2.5 py-1">
            <Clock3 className="h-3.5 w-3.5" />
            {formatTimestamp(alert.timestamp)}
          </span>
          {confidence > 0 && (
            <span className="rounded-full bg-[var(--panel-strong)] px-2.5 py-1 text-[11px] font-medium text-[var(--muted-strong)]">
              {confidence}%
            </span>
          )}
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--panel)] px-2.5 py-1 text-[var(--foreground)]">
            <Eye className="h-3.5 w-3.5" />
            Ver detalhes
          </span>
        </div>
      </div>
    </button>
  );
}
