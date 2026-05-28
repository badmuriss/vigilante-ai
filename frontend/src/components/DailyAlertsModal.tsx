"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Clock3, ShieldAlert, X } from "lucide-react";
import type { Alert } from "@/types";

interface DailyAlertEntry extends Alert {
  cameraName: string;
}

interface DailyAlertsModalProps {
  open: boolean;
  dateLabel: string;
  alerts: DailyAlertEntry[];
  onClose: () => void;
  onSelectAlert: (alert: DailyAlertEntry) => void;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function DailyAlertsModal({
  open,
  dateLabel,
  alerts,
  onClose,
  onSelectAlert,
}: DailyAlertsModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-bg-overlay backdrop-blur-sm data-[state=open]:animate-fade-in" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 flex max-h-[88vh] w-[min(94vw,820px)] -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-lg bg-bg-elevated shadow-overlay outline-none data-[state=open]:animate-slide-up">
          <div className="flex items-start justify-between gap-4 border-b border-border px-6 py-4">
            <div>
              <p className="eyebrow">Alertas do dia</p>
              <Dialog.Title className="mt-1 text-lg font-semibold text-text">
                {dateLabel}
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-xs text-text-muted">
                {alerts.length === 0
                  ? "Nenhum alerta registrado nesse dia."
                  : `${alerts.length} ${alerts.length === 1 ? "ocorrência" : "ocorrências"} encontradas. Clique para ver os detalhes.`}
              </Dialog.Description>
            </div>
            <Dialog.Close
              aria-label="Fechar"
              className="grid h-9 w-9 place-items-center rounded-md text-text-muted transition hover:bg-bg-sunken hover:text-text"
            >
              <X size={16} strokeWidth={1.8} />
            </Dialog.Close>
          </div>

          <div className="overflow-y-auto">
            {alerts.length === 0 ? (
              <div className="flex flex-col items-center gap-2 px-6 py-16 text-center">
                <ShieldAlert size={28} className="text-text-muted" />
                <p className="text-sm font-medium text-text">Sem registros neste dia.</p>
                <p className="text-xs text-text-muted">
                  As barras vazias correspondem a dias sem ocorrências.
                </p>
              </div>
            ) : (
              <ul className="divide-y divide-border">
                {alerts.map((alert) => {
                  const confidence = Math.round(alert.confidence * 100);
                  return (
                    <li key={alert.id}>
                      <button
                        type="button"
                        onClick={() => onSelectAlert(alert)}
                        className="flex w-full items-center gap-4 px-6 py-3 text-left transition hover:bg-bg-sunken"
                      >
                        {alert.frame_thumbnail ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={`data:image/jpeg;base64,${alert.frame_thumbnail}`}
                            alt="thumb"
                            className="h-12 w-16 flex-none rounded object-cover"
                          />
                        ) : (
                          <div className="grid h-12 w-16 flex-none place-items-center rounded bg-bg-sunken">
                            <ShieldAlert size={14} className="text-text-subtle" />
                          </div>
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-text">
                            {alert.violation_type}
                          </p>
                          <p className="mt-0.5 truncate text-xs text-text-muted">
                            {alert.cameraName}
                          </p>
                        </div>
                        <div className="hidden text-right sm:block">
                          <p className="text-xs text-text-muted mono-num inline-flex items-center gap-1">
                            <Clock3 size={12} strokeWidth={1.8} />
                            {formatTime(alert.timestamp)}
                          </p>
                          <p className="mt-0.5 text-xs text-text-subtle mono-num">
                            {confidence > 0 ? `${confidence}% confiança` : "—"}
                          </p>
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
