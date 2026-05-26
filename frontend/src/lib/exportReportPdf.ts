import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

export interface ReportKpi {
  label: string;
  value: string;
}

export interface ReportDailyCount {
  day: string;
  count: number;
}

export interface ReportAlertRow {
  date: string;
  time: string;
  camera: string;
  type: string;
  confidence: number;
  thumbnail?: string | null;
}

export interface ReportData {
  periodLabel: string;
  generatedAt: Date;
  kpis: ReportKpi[];
  byDay: ReportDailyCount[];
  distribution: Array<[string, number]>;
  topCameras: Array<[string, number]>;
  alerts: ReportAlertRow[];
  includeImages: boolean;
}

const MARGIN_X = 14;
const PAGE_W = 210;
const PAGE_H = 297;

function ensureSpace(doc: jsPDF, cursorY: number, needed: number): number {
  if (cursorY + needed > PAGE_H - 14) {
    doc.addPage();
    return 18;
  }
  return cursorY;
}

function sectionTitle(doc: jsPDF, text: string, y: number): number {
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(10, 10, 10);
  doc.text(text, MARGIN_X, y);
  return y + 5;
}

function drawKpis(doc: jsPDF, kpis: ReportKpi[], y: number): number {
  const cardW = (PAGE_W - MARGIN_X * 2 - 6) / 4;
  const cardH = 20;
  kpis.slice(0, 4).forEach((kpi, idx) => {
    const x = MARGIN_X + idx * (cardW + 2);
    doc.setDrawColor(232, 231, 228);
    doc.setFillColor(255, 255, 255);
    doc.roundedRect(x, y, cardW, cardH, 2, 2, "FD");
    doc.setFont("helvetica", "normal");
    doc.setFontSize(7);
    doc.setTextColor(74, 74, 74);
    doc.text(kpi.label.toUpperCase(), x + 3, y + 5);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(14);
    doc.setTextColor(10, 10, 10);
    doc.text(kpi.value, x + 3, y + 14);
  });
  return y + cardH + 6;
}

function drawDailyBars(doc: jsPDF, data: ReportDailyCount[], y: number): number {
  const chartH = 50;
  const chartW = PAGE_W - MARGIN_X * 2;
  const baseY = y + chartH;
  const max = Math.max(1, ...data.map((d) => d.count));
  doc.setDrawColor(232, 231, 228);
  doc.line(MARGIN_X, baseY, MARGIN_X + chartW, baseY);

  if (data.length === 0) {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor(118, 118, 118);
    doc.text("Sem dados no período.", MARGIN_X, y + chartH / 2);
    return y + chartH + 4;
  }

  const barSlot = chartW / data.length;
  const barW = Math.max(1, Math.min(barSlot * 0.7, 6));
  doc.setFillColor(17, 17, 17);
  data.forEach((d, i) => {
    const h = (d.count / max) * (chartH - 6);
    const cx = MARGIN_X + i * barSlot + (barSlot - barW) / 2;
    doc.rect(cx, baseY - h, barW, h, "F");
  });

  // labels (first, middle, last)
  doc.setFont("helvetica", "normal");
  doc.setFontSize(7);
  doc.setTextColor(118, 118, 118);
  const labelIdxs = data.length > 6 ? [0, Math.floor(data.length / 2), data.length - 1] : data.map((_, i) => i);
  for (const i of labelIdxs) {
    const cx = MARGIN_X + i * barSlot + barSlot / 2;
    doc.text(data[i].day, cx, baseY + 4, { align: "center" });
  }
  return y + chartH + 8;
}

export async function exportReportPdf(data: ReportData): Promise<void> {
  const doc = new jsPDF({ unit: "mm", format: "a4" });

  // Header
  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.setTextColor(10, 10, 10);
  doc.text("Vigilante.AI", MARGIN_X, 18);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.setTextColor(74, 74, 74);
  doc.text("Relatório de alertas e indicadores", MARGIN_X, 23);

  const generated = data.generatedAt.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  doc.setFontSize(8);
  doc.setTextColor(118, 118, 118);
  doc.text(data.periodLabel, PAGE_W - MARGIN_X, 18, { align: "right" });
  doc.text(`Gerado em ${generated}`, PAGE_W - MARGIN_X, 23, { align: "right" });

  doc.setDrawColor(232, 231, 228);
  doc.line(MARGIN_X, 28, PAGE_W - MARGIN_X, 28);

  let cursorY = 36;
  cursorY = sectionTitle(doc, "Indicadores", cursorY);
  cursorY = drawKpis(doc, data.kpis, cursorY);

  cursorY = ensureSpace(doc, cursorY, 70);
  cursorY = sectionTitle(doc, "Alertas por dia", cursorY);
  cursorY = drawDailyBars(doc, data.byDay, cursorY);

  // Distribution
  if (data.distribution.length > 0) {
    cursorY = ensureSpace(doc, cursorY, 30);
    cursorY = sectionTitle(doc, "Distribuição por tipo de violação", cursorY);
    autoTable(doc, {
      startY: cursorY,
      margin: { left: MARGIN_X, right: MARGIN_X },
      head: [["Tipo de violação", "Ocorrências"]],
      body: data.distribution.map(([t, c]) => [t, String(c)]),
      styles: { fontSize: 9, cellPadding: 2.5, textColor: 20 },
      headStyles: { fillColor: [244, 244, 243], textColor: 74, fontStyle: "bold" },
      alternateRowStyles: { fillColor: [250, 250, 249] },
      theme: "plain",
    });
    cursorY = (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 8;
  }

  // Top cameras
  if (data.topCameras.length > 0) {
    cursorY = ensureSpace(doc, cursorY, 30);
    cursorY = sectionTitle(doc, "Câmeras com mais ocorrências", cursorY);
    autoTable(doc, {
      startY: cursorY,
      margin: { left: MARGIN_X, right: MARGIN_X },
      head: [["Câmera", "Ocorrências"]],
      body: data.topCameras.map(([n, c]) => [n, String(c)]),
      styles: { fontSize: 9, cellPadding: 2.5, textColor: 20 },
      headStyles: { fillColor: [244, 244, 243], textColor: 74, fontStyle: "bold" },
      alternateRowStyles: { fillColor: [250, 250, 249] },
      theme: "plain",
    });
    cursorY = (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 8;
  }

  // Alerts detail
  if (data.alerts.length > 0) {
    cursorY = ensureSpace(doc, cursorY, 30);
    cursorY = sectionTitle(
      doc,
      `Detalhe dos alertas (${data.alerts.length})`,
      cursorY,
    );

    const head = data.includeImages
      ? [["Data", "Hora", "Câmera", "Tipo", "Conf.", "Imagem"]]
      : [["Data", "Hora", "Câmera", "Tipo", "Conf."]];
    const body = data.alerts.map((a) =>
      data.includeImages
        ? [a.date, a.time, a.camera, a.type, `${Math.round(a.confidence * 100)}%`, ""]
        : [a.date, a.time, a.camera, a.type, `${Math.round(a.confidence * 100)}%`],
    );

    const imageColIndex = 5;
    const imgW = 22;
    const imgH = 16;

    autoTable(doc, {
      startY: cursorY,
      margin: { left: MARGIN_X, right: MARGIN_X },
      head,
      body,
      styles: {
        fontSize: 8,
        cellPadding: 2,
        textColor: 20,
        minCellHeight: data.includeImages ? imgH + 2 : undefined,
        valign: "middle",
      },
      headStyles: { fillColor: [244, 244, 243], textColor: 74, fontStyle: "bold" },
      alternateRowStyles: { fillColor: [250, 250, 249] },
      columnStyles: data.includeImages
        ? { 5: { cellWidth: imgW + 4, halign: "center" } }
        : undefined,
      theme: "plain",
      didDrawCell: (cell) => {
        if (!data.includeImages) return;
        if (cell.section !== "body" || cell.column.index !== imageColIndex) return;
        const row = data.alerts[cell.row.index];
        if (!row?.thumbnail) return;
        try {
          const x = cell.cell.x + (cell.cell.width - imgW) / 2;
          const yPos = cell.cell.y + (cell.cell.height - imgH) / 2;
          doc.addImage(
            `data:image/jpeg;base64,${row.thumbnail}`,
            "JPEG",
            x,
            yPos,
            imgW,
            imgH,
          );
        } catch {
          // ignore broken images
        }
      },
    });
  }

  // Footer page numbers
  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(7);
    doc.setTextColor(140, 140, 140);
    doc.text(
      `Página ${i} de ${pageCount}`,
      PAGE_W - MARGIN_X,
      PAGE_H - 8,
      { align: "right" },
    );
    doc.text("Vigilante.AI · gerado automaticamente", MARGIN_X, PAGE_H - 8);
  }

  const stamp = data.generatedAt.toISOString().slice(0, 19).replace(/[:T]/g, "-");
  doc.save(`vigilante-relatorio-${stamp}.pdf`);
}
