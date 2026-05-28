"use client";

import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Download, FileText, Image as ImageIcon, X } from "lucide-react";

interface ExportPdfDialogProps {
  open: boolean;
  alertCount: number;
  onClose: () => void;
  onExport: (opts: { includeImages: boolean }) => Promise<void> | void;
}

export default function ExportPdfDialog({
  open,
  alertCount,
  onClose,
  onExport,
}: ExportPdfDialogProps) {
  const [includeImages, setIncludeImages] = useState(false);
  const [busy, setBusy] = useState(false);

  async function handleExport() {
    setBusy(true);
    try {
      await onExport({ includeImages });
      onClose();
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && !busy && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-bg-overlay backdrop-blur-sm data-[state=open]:animate-fade-in" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(94vw,460px)] -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-lg bg-bg-elevated shadow-overlay outline-none data-[state=open]:animate-slide-up">
          <div className="flex items-start justify-between gap-4 border-b border-border px-6 py-4">
            <div>
              <p className="eyebrow">Exportar relatório</p>
              <Dialog.Title className="mt-1 text-base font-semibold text-text">
                Configurar exportação em PDF
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-xs text-text-muted">
                {alertCount.toLocaleString("pt-BR")} alertas serão incluídos no documento.
              </Dialog.Description>
            </div>
            <Dialog.Close
              aria-label="Fechar"
              disabled={busy}
              className="grid h-9 w-9 place-items-center rounded-md text-text-muted transition hover:bg-bg-sunken hover:text-text disabled:opacity-50"
            >
              <X size={16} strokeWidth={1.8} />
            </Dialog.Close>
          </div>

          <div className="space-y-3 px-6 py-5">
            <p className="text-xs font-medium uppercase tracking-wider text-text-muted">
              Conteúdo
            </p>
            <label
              className={`flex cursor-pointer items-start gap-3 rounded-lg border p-4 transition ${
                !includeImages
                  ? "border-text bg-bg-sunken"
                  : "border-border hover:bg-bg-sunken"
              }`}
            >
              <input
                type="radio"
                name="pdf-mode"
                className="mt-0.5"
                checked={!includeImages}
                onChange={() => setIncludeImages(false)}
              />
              <div className="flex-1">
                <div className="flex items-center gap-2 text-sm font-medium text-text">
                  <FileText size={14} strokeWidth={1.8} />
                  Somente texto
                </div>
                <p className="mt-1 text-xs text-text-muted">
                  PDF mais leve, com indicadores, tabelas e a lista de alertas sem
                  miniaturas. Recomendado para envio por e-mail.
                </p>
              </div>
            </label>

            <label
              className={`flex cursor-pointer items-start gap-3 rounded-lg border p-4 transition ${
                includeImages
                  ? "border-text bg-bg-sunken"
                  : "border-border hover:bg-bg-sunken"
              }`}
            >
              <input
                type="radio"
                name="pdf-mode"
                className="mt-0.5"
                checked={includeImages}
                onChange={() => setIncludeImages(true)}
              />
              <div className="flex-1">
                <div className="flex items-center gap-2 text-sm font-medium text-text">
                  <ImageIcon size={14} strokeWidth={1.8} />
                  Com imagens dos alertas
                </div>
                <p className="mt-1 text-xs text-text-muted">
                  Inclui a miniatura de cada ocorrência ao lado da linha. O arquivo
                  pode ficar maior e demorar mais para gerar.
                </p>
              </div>
            </label>
          </div>

          <div className="flex items-center justify-end gap-2 border-t border-border bg-bg-sunken px-6 py-3">
            <button
              type="button"
              className="btn-ghost text-sm"
              onClick={onClose}
              disabled={busy}
            >
              Cancelar
            </button>
            <button
              type="button"
              className="btn-primary text-sm"
              onClick={handleExport}
              disabled={busy}
            >
              <Download size={14} strokeWidth={1.8} />
              {busy ? "Gerando…" : "Exportar PDF"}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
