"use client";

import * as Dialog from "@radix-ui/react-dialog";
import Image from "next/image";
import { Clock3, ShieldAlert, X } from "lucide-react";
import type { Alert } from "@/types";

interface AlertDetailsModalProps {
  alert: Alert | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function formatDateTime(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function AlertDetailsModal({
  alert,
  open,
  onOpenChange,
}: AlertDetailsModalProps) {
  if (!alert) return null;

  const imageData = alert.frame_image || alert.frame_thumbnail;
  const missingItems = alert.missing_epis.length > 0 ? alert.missing_epis : [alert.violation_type];
  const confidence = Math.round(alert.confidence * 100);

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-slate-950/45 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,980px)] -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-[28px] border border-white/[0.65] bg-[#f8faf8] shadow-[0_40px_120px_-45px_rgba(15,23,42,0.9)] focus:outline-none">
          <div className="flex items-start justify-between gap-4 border-b border-[var(--border)] px-5 py-4 sm:px-6">
            <div>
              <p className="eyebrow">Detalhes do alerta</p>
              <Dialog.Title className="mt-1 text-xl font-semibold text-[var(--foreground)]">
                {alert.violation_type}
              </Dialog.Title>
              <Dialog.Description className="mt-2 text-sm text-[var(--muted)]">
                Inspecione a imagem capturada, os EPIs ausentes e o horário exato do registro.
              </Dialog.Description>
            </div>

            <Dialog.Close className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[var(--border)] bg-white/[0.85] text-[var(--muted-strong)] transition hover:border-[var(--border-strong)] hover:text-[var(--foreground)]">
              <X className="h-4 w-4" />
            </Dialog.Close>
          </div>

          <div className="grid gap-6 p-5 sm:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.9fr)] sm:p-6">
            <div className="overflow-hidden rounded-[24px] border border-[var(--border)] bg-[var(--panel)]">
              {imageData ? (
                <Image
                  src={`data:image/jpeg;base64,${imageData}`}
                  alt="Registro do alerta"
                  width={960}
                  height={540}
                  unoptimized
                  className="h-full max-h-[70vh] w-full object-contain"
                />
              ) : (
                <div className="flex h-80 items-center justify-center text-sm text-[var(--muted)]">
                  Imagem indisponível para este alerta.
                </div>
              )}
            </div>

            <div className="space-y-4">
              <div className="rounded-[24px] border border-[var(--border)] bg-white/[0.82] p-5">
                <p className="text-sm font-semibold text-[var(--foreground)]">EPIs faltantes</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {missingItems.map((item) => (
                    <span
                      key={item}
                      className="inline-flex items-center gap-2 rounded-full border border-rose-200 bg-rose-50 px-3 py-1.5 text-sm font-medium text-rose-700"
                    >
                      <ShieldAlert className="h-4 w-4" />
                      {item}
                    </span>
                  ))}
                </div>
              </div>

              <div className="rounded-[24px] border border-[var(--border)] bg-white/[0.82] p-5">
                <p className="text-sm font-semibold text-[var(--foreground)]">Momento do registro</p>
                <div className="mt-3 inline-flex items-center gap-2 rounded-full bg-[var(--panel)] px-3 py-2 text-sm text-[var(--muted-strong)]">
                  <Clock3 className="h-4 w-4" />
                  {formatDateTime(alert.timestamp)}
                </div>
              </div>

              <div className="rounded-[24px] border border-[var(--border)] bg-white/[0.82] p-5">
                <p className="text-sm font-semibold text-[var(--foreground)]">Sinal de detecção</p>
                <p className="mt-3 text-3xl font-semibold text-[var(--foreground)]">
                  {confidence > 0 ? `${confidence}%` : "Não disponível"}
                </p>
                <p className="mt-2 text-sm text-[var(--muted)]">
                  Valor representativo da inferência no momento em que a violação foi registrada.
                </p>
              </div>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}