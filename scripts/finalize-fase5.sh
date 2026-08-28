#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
video_url="${1:-}"

if [[ ! "${video_url}" =~ ^https://(www\.)?(youtube\.com|youtu\.be)/ ]]; then
  printf 'Uso: scripts/finalize-fase5.sh https://youtu.be/ID_DO_VIDEO\n' >&2
  exit 1
fi

VIGILANTE_VIDEO_URL="${video_url}" node "${REPO_ROOT}/scripts/set-fase5-video-url.mjs"
"${REPO_ROOT}/scripts/build-fase5-delivery.sh"

final_zip="${REPO_ROOT}/docs/01-academico/startup-one/fase-05-mercado-mvp/entrega/VigilanteAI_Fase5_ENTREGA_FINAL.zip"
[[ -f "${final_zip}" ]] || {
  printf 'O ZIP final não foi gerado.\n' >&2
  exit 1
}

printf 'Entrega final pronta: %s\n' "${final_zip}"
printf 'Ainda falta testar o link em janela anônima e fazer o upload na FIAP ON.\n'
