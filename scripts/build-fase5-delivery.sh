#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PHASE_DIR="${REPO_ROOT}/docs/01-academico/startup-one/fase-05-mercado-mvp"
DELIVERY_DIR="${PHASE_DIR}/entrega"
PACKAGE_DIR="${DELIVERY_DIR}/pacote-fiap"
DOCX_PATH="${DELIVERY_DIR}/Documento_Fase5_Mercado_MVP_VigilanteAI.docx"
DOC_PDF="${DELIVERY_DIR}/Documento_Fase5_Mercado_MVP_VigilanteAI.pdf"
SLIDES_PDF="${DELIVERY_DIR}/Apresentacao_Fase5_VigilanteAI.pdf"
SLIDES_URL="file://${PHASE_DIR}/slides-fase5.html"

for command_name in node libreoffice google-chrome-stable pdfinfo rg zip unzip; do
  command -v "${command_name}" >/dev/null 2>&1 || {
    printf 'Comando necessário ausente: %s\n' "${command_name}" >&2
    exit 1
  }
done

node "${PHASE_DIR}/build/build_document.js"
libreoffice --headless --convert-to pdf --outdir "${DELIVERY_DIR}" "${DOCX_PATH}" >/dev/null
google-chrome-stable \
  --headless=new \
  --no-sandbox \
  --disable-gpu \
  --no-pdf-header-footer \
  --print-to-pdf="${SLIDES_PDF}" \
  "${SLIDES_URL}" >/dev/null 2>&1

cp "${DOC_PDF}" "${PACKAGE_DIR}/1_Documentacao_Fase5_VigilanteAI.pdf"
cp "${SLIDES_PDF}" "${PACKAGE_DIR}/2_Apresentacao_Fase5_VigilanteAI.pdf"
cp "${PHASE_DIR}/Roteiro_Pitch_5min_VigilanteAI.md" "${PACKAGE_DIR}/5_ROTEIRO_PITCH_5MIN.txt"

doc_pages="$(pdfinfo "${DOC_PDF}" | awk '/^Pages:/ {print $2}')"
slide_pages="$(pdfinfo "${SLIDES_PDF}" | awk '/^Pages:/ {print $2}')"
[[ "${doc_pages}" -ge 10 ]] || {
  printf 'PDF da documentação parece incompleto: %s páginas.\n' "${doc_pages}" >&2
  exit 1
}
[[ "${slide_pages}" == "8" ]] || {
  printf 'Apresentação deveria ter 8 páginas; encontrou %s.\n' "${slide_pages}" >&2
  exit 1
}

if rg -q '\{\{YOUTUBE_URL\}\}|PENDENTE DE GRAVAÇÃO' \
  "${PHASE_DIR}/Documento_Fase5_Mercado_MVP_VigilanteAI.md" \
  "${PACKAGE_DIR}/3_LINKS.txt"; then
  zip_name="VigilanteAI_Fase5_PRONTO_PARA_VIDEO.zip"
else
  zip_name="VigilanteAI_Fase5_ENTREGA_FINAL.zip"
fi

rm -f "${DELIVERY_DIR:?}/${zip_name}"
(
  cd "${DELIVERY_DIR}"
  zip -q -r "${zip_name}" pacote-fiap
)
unzip -t "${DELIVERY_DIR}/${zip_name}" >/dev/null

printf 'Documentação: %s páginas.\n' "${doc_pages}"
printf 'Apresentação: %s páginas.\n' "${slide_pages}"
printf 'Código-fonte: https://github.com/badmuriss/vigilante-ai\n'
printf 'Pacote verificado: %s\n' "${DELIVERY_DIR}/${zip_name}"
