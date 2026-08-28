const fs = require("fs");
const path = require("path");
const {
  AlignmentType,
  BorderStyle,
  Document,
  Footer,
  HeadingLevel,
  ImageRun,
  LevelFormat,
  Packer,
  PageBreak,
  PageNumber,
  Paragraph,
  ShadingType,
  Table,
  TableCell,
  TableRow,
  TextRun,
  WidthType,
} = require("docx");

const phaseDir = path.resolve(__dirname, "..");
const repoRoot = path.resolve(__dirname, "../../../../..");
const inputPath = path.join(phaseDir, "Documento_Fase5_Mercado_MVP_VigilanteAI.md");
const outputPath = path.join(phaseDir, "entrega", "Documento_Fase5_Mercado_MVP_VigilanteAI.docx");
const logoPath = path.join(repoRoot, "assets", "logo-black.png");

const markdown = fs.readFileSync(inputPath, "utf8");
const lines = markdown.split(/\r?\n/);
const contentWidth = 9026;
const orange = "F97316";
const ink = "16202A";
const muted = "64748B";
const pale = "FFF4E8";

function textRuns(value, options = {}) {
  const clean = value
    .replace(/<([^>]+)>/g, "$1")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1 ($2)");
  const parts = clean.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean);
  return parts.map((part) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return new TextRun({ text: part.slice(2, -2), bold: true, ...options });
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return new TextRun({ text: part.slice(1, -1), font: "Consolas", color: "334155", ...options });
    }
    return new TextRun({ text: part, ...options });
  });
}

function paragraph(value, options = {}) {
  return new Paragraph({
    children: textRuns(value),
    keepLines: true,
    spacing: { after: 150, line: 300 },
    ...options,
  });
}

function boxedBlock({ children, fill }) {
  const none = { style: BorderStyle.NONE, size: 0, color: fill };
  return new Table({
    width: { size: contentWidth - 360, type: WidthType.DXA },
    columnWidths: [contentWidth - 360],
    indent: { size: 180, type: WidthType.DXA },
    borders: {
      top: none,
      bottom: none,
      right: none,
      left: { style: BorderStyle.SINGLE, size: 16, color: orange },
      insideHorizontal: none,
      insideVertical: none,
    },
    rows: [
      new TableRow({
        cantSplit: true,
        children: [
          new TableCell({
            width: { size: contentWidth - 360, type: WidthType.DXA },
            shading: { fill, type: ShadingType.CLEAR },
            margins: { top: 130, bottom: 130, left: 180, right: 160 },
            children: [
              new Paragraph({
                keepLines: true,
                spacing: { before: 0, after: 0, line: 280 },
                children,
              }),
            ],
          }),
        ],
      }),
    ],
  });
}

function tableFrom(rows) {
  const columnCount = Math.max(...rows.map((row) => row.length));
  const base = Math.floor(contentWidth / columnCount);
  const widths = Array.from({ length: columnCount }, (_, index) =>
    index === columnCount - 1 ? contentWidth - base * (columnCount - 1) : base,
  );
  const border = { style: BorderStyle.SINGLE, size: 2, color: "D7DEE7" };
  const borders = { top: border, bottom: border, left: border, right: border };

  return new Table({
    width: { size: contentWidth, type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((row, rowIndex) =>
      new TableRow({
        tableHeader: rowIndex === 0,
        cantSplit: true,
        children: widths.map((width, columnIndex) =>
          new TableCell({
            width: { size: width, type: WidthType.DXA },
            borders,
            shading: rowIndex === 0 ? { fill: ink, type: ShadingType.CLEAR } : undefined,
            margins: { top: 105, bottom: 105, left: 130, right: 130 },
            children: [
              new Paragraph({
                spacing: { after: 0, line: 270 },
                keepNext: rowIndex < rows.length - 1,
                children: textRuns(row[columnIndex] || "", {
                  bold: rowIndex === 0,
                  color: rowIndex === 0 ? "FFFFFF" : ink,
                  size: columnCount >= 6 ? 16 : 18,
                }),
              }),
            ],
          }),
        ),
      }),
    ),
  });
}

function parseBody() {
  const children = [];
  const pageBreakHeadings = [
    "3. Parte 1:",
    "4. Parte 2:",
    "4.4 Estratégia de preço",
    "5. Análise financeira",
    "5.5 Breakeven e métricas unitárias",
    "6. Parte 3:",
    "6.3 Banco de dados em nuvem",
    "6.6 Estado de conclusão",
    "7. Riscos e mitigação",
    "8. Referências",
  ];
  let index = lines.findIndex((line) => line.startsWith("## 1. Equipe"));
  let inCode = false;
  let inReferences = false;
  let codeLines = [];

  while (index < lines.length) {
    const line = lines[index];

    if (line.startsWith("```")) {
      if (!inCode) {
        inCode = true;
        codeLines = [];
      } else {
        children.push(new Paragraph({ keepNext: true, spacing: { after: 80 } }));
        children.push(
          boxedBlock({
            fill: "F1F5F9",
            children: codeLines.map((codeLine, lineIndex) =>
              new TextRun({ text: codeLine || " ", break: lineIndex === 0 ? 0 : 1, font: "Consolas", size: 18 }),
            ),
          }),
        );
        children.push(new Paragraph({ spacing: { after: 150 } }));
        inCode = false;
      }
      index += 1;
      continue;
    }

    if (inCode) {
      codeLines.push(line);
      index += 1;
      continue;
    }

    if (line.startsWith("|") && lines[index + 1]?.match(/^\|[\s:|-]+\|$/)) {
      const tableRows = [];
      tableRows.push(line.split("|").slice(1, -1).map((cell) => cell.trim()));
      index += 2;
      while (index < lines.length && lines[index].startsWith("|")) {
        tableRows.push(lines[index].split("|").slice(1, -1).map((cell) => cell.trim()));
        index += 1;
      }
      children.push(new Paragraph({ keepNext: true, spacing: { after: 75 } }));
      children.push(tableFrom(tableRows));
      children.push(new Paragraph({ spacing: { after: 170 } }));
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      const levels = {
        1: HeadingLevel.HEADING_1,
        2: HeadingLevel.HEADING_1,
        3: HeadingLevel.HEADING_2,
      };
      inReferences = heading[2].startsWith("8. Referências");
      children.push(
        new Paragraph({
          heading: levels[heading[1].length],
          pageBreakBefore: pageBreakHeadings.some((prefix) => heading[2].startsWith(prefix)),
          keepNext: true,
          children: [new TextRun(heading[2])],
        }),
      );
      index += 1;
      continue;
    }

    if (/^-\s+/.test(line)) {
      children.push(
        new Paragraph({
          numbering: { reference: "bullets", level: 0 },
          keepLines: true,
          spacing: inReferences ? { after: 40, line: 240 } : { after: 70, line: 285 },
          children: textRuns(line.replace(/^-\s+/, ""), inReferences ? { size: 18 } : {}),
        }),
      );
      index += 1;
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      children.push(
        new Paragraph({
          spacing: { after: 70, line: 285 },
          indent: { left: 360, hanging: 260 },
          keepLines: true,
          children: textRuns(line),
        }),
      );
      index += 1;
      continue;
    }

    if (line.startsWith("> ")) {
      children.push(new Paragraph({ keepNext: true, spacing: { after: 70 } }));
      children.push(
        boxedBlock({
          fill: pale,
          children: textRuns(line.slice(2)),
        }),
      );
      children.push(new Paragraph({ spacing: { after: 150 } }));
      index += 1;
      continue;
    }

    if (line.trim() && line !== "---") {
      let combined = line.trim();
      while (
        index + 1 < lines.length &&
        lines[index + 1].trim() &&
        !lines[index + 1].match(/^(#{1,3})\s|^\||^-\s|^\d+\.\s|^```|^>\s|^---$/)
      ) {
        combined += ` ${lines[index + 1].trim()}`;
        index += 1;
      }
      children.push(paragraph(combined));
    }
    index += 1;
  }

  return children;
}

const cover = [
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 720, after: 280, line: 2400, lineRule: "atLeast" },
    children: [
      new ImageRun({
        type: "png",
        data: fs.readFileSync(logoPath),
        transformation: { width: 116, height: 121 },
        altText: {
          title: "Vigilante.AI",
          description: "Logo do Vigilante.AI",
          name: "Logo Vigilante.AI",
        },
      }),
    ],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 170 },
    children: [new TextRun({ text: "Vigilante.AI", bold: true, size: 58, color: ink })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 420, line: 330 },
    children: [new TextRun({ text: "Estratégia de mercado, viabilidade financeira e evolução do MVP", size: 28, color: muted })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 520, after: 120 },
    children: [new TextRun({ text: "Startup One, Fase 5", bold: true, size: 24, color: orange })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "FIAP, agosto de 2026", size: 22, color: muted })],
  }),
  new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Sumário")] }),
  paragraph("1. Equipe"),
  paragraph("2. Resumo executivo"),
  paragraph("3. Parte 1: versão atual do projeto"),
  paragraph("4. Parte 2: Go to Market Canvas"),
  paragraph("5. Análise financeira"),
  paragraph("6. Parte 3: protótipo funcional de alta fidelidade"),
  paragraph("7. Riscos e mitigação"),
  paragraph("8. Referências"),
  new Paragraph({ children: [new PageBreak()] }),
];

const doc = new Document({
  creator: "Grupo Vigilante.AI",
  title: "Vigilante.AI, Estratégia de mercado, viabilidade financeira e evolução do MVP",
  description: "Entrega Startup One, Fase 5",
  styles: {
    default: {
      document: { run: { font: "Arial", size: 21, color: ink } },
    },
    paragraphStyles: [
      {
        id: "Heading1",
        name: "Heading 1",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { font: "Arial", size: 32, bold: true, color: ink },
        paragraph: { spacing: { before: 320, after: 180, line: 360 }, outlineLevel: 0 },
      },
      {
        id: "Heading2",
        name: "Heading 2",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { font: "Arial", size: 26, bold: true, color: orange },
        paragraph: { spacing: { before: 250, after: 125, line: 320 }, outlineLevel: 1 },
      },
    ],
  },
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [
          {
            level: 0,
            format: LevelFormat.BULLET,
            text: "•",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 620, hanging: 280 } } },
          },
        ],
      },
      {
        reference: "steps",
        levels: [
          {
            level: 0,
            format: LevelFormat.DECIMAL,
            text: "%1.",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 620, hanging: 280 } } },
          },
        ],
      },
    ],
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: 11906, height: 16838 },
          margin: { top: 1080, right: 1440, bottom: 1220, left: 1440, header: 540, footer: 620 },
        },
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              alignment: AlignmentType.RIGHT,
              spacing: { before: 80, after: 0 },
              border: { top: { style: BorderStyle.SINGLE, size: 4, color: "D7DEE7" } },
              children: [
                new TextRun({ text: "Vigilante.AI  |  FIAP  |  ", color: muted, size: 17 }),
                new TextRun({ children: [PageNumber.CURRENT], color: muted, size: 17 }),
              ],
            }),
          ],
        }),
      },
      children: [...cover, ...parseBody()],
    },
  ],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(outputPath, buffer);
  process.stdout.write(`${outputPath}\n`);
});
