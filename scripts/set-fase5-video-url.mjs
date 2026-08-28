import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "..");
const phaseDir = path.join(
  repoRoot,
  "docs/01-academico/startup-one/fase-05-mercado-mvp",
);
const videoUrl = process.env.VIGILANTE_VIDEO_URL;

if (!videoUrl) {
  throw new Error("VIGILANTE_VIDEO_URL não informado");
}

const operations = [
  {
    target: path.join(phaseDir, "Documento_Fase5_Mercado_MVP_VigilanteAI.md"),
    replacements: [["{{YOUTUBE_URL}}", videoUrl]],
  },
  {
    target: path.join(phaseDir, "entrega/pacote-fiap/3_LINKS.txt"),
    replacements: [["{{YOUTUBE_URL}}", videoUrl]],
  },
  {
    target: path.join(phaseDir, "entrega/pacote-fiap/README.md"),
    replacements: [
      [
        "Este é um pacote pronto para a gravação. A implementação, o domínio público, o banco AWS e os PDFs estão concluídos. Não envie na FIAP ON enquanto o marcador do YouTube permanecer em `3_LINKS.txt`.",
        "Este é o pacote final para envio. A implementação, o domínio público, o banco AWS, os PDFs e o link do vídeo estão consolidados.",
      ],
      [
        "Quando o vídeo estiver publicado como não listado, execute `scripts/finalize-fase5.sh URL_DO_YOUTUBE`. O comando atualiza o documento e o arquivo de links, gera os PDFs, testa o ZIP e produz `VigilanteAI_Fase5_ENTREGA_FINAL.zip`. Depois, teste o link em uma janela anônima.",
        "O comando `scripts/finalize-fase5.sh` atualizou o documento e o arquivo de links, gerou os PDFs, testou o ZIP e produziu `VigilanteAI_Fase5_ENTREGA_FINAL.zip`. Antes do envio, teste o link do vídeo em uma janela anônima.",
      ],
    ],
  },
  {
    target: path.join(phaseDir, "entrega/pacote-fiap/4_CHECKLIST_FINAL.md"),
    replacements: [
      [
        "- [ ] Link do YouTube não listado inserido no documento e em `3_LINKS.txt`.",
        "- [x] Link do YouTube não listado inserido no documento e em `3_LINKS.txt`.",
      ],
      [
        "- [ ] ZIP final regenerado com `scripts/finalize-fase5.sh URL_DO_YOUTUBE`.",
        "- [x] ZIP final regenerado com `scripts/finalize-fase5.sh URL_DO_YOUTUBE`.",
      ],
    ],
  },
];

const originals = operations.map(({ target, replacements }) => ({
  target,
  replacements,
  content: fs.readFileSync(target, "utf8"),
}));
const missingMarkers = originals
  .flatMap(({ target, replacements, content }) =>
    replacements
      .filter(([from]) => !content.includes(from))
      .map(() => path.relative(repoRoot, target)),
  );

if (missingMarkers.length > 0) {
  throw new Error(
    `Marcador de finalização ausente em: ${[...new Set(missingMarkers)].join(", ")}. ` +
      "Nenhum arquivo foi alterado.",
  );
}

for (const { target, replacements, content } of originals) {
  const updated = replacements.reduce(
    (current, [from, to]) => current.replaceAll(from, to),
    content,
  );
  fs.writeFileSync(target, updated);
}
