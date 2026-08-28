#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env.aws"
DEMO_FILE="${REPO_ROOT}/.aws-fase5/demo-login"
NAMESPACE="vigilante"
PUBLIC_URL="https://vigilanteai.outis.com.br"
EXPECTED_DB_HOST="vigilante-fase5.cw3ssq20s36g.us-east-1.rds.amazonaws.com"

fail() {
  printf 'FALHA: %s\n' "$1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "comando ausente: $1"
}

database_host() {
  kubectl -n "${NAMESPACE}" exec deploy/backend -- python -c \
    'import os; from sqlalchemy.engine import make_url; print(make_url(os.environ["VIGILANTE_DATABASE_URL"]).host)'
}

deploy() {
  [[ -f "${ENV_FILE}" ]] || fail ".env.aws ausente"
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  [[ -n "${VIGILANTE_DATABASE_URL:-}" ]] || fail "VIGILANTE_DATABASE_URL ausente"
  [[ -n "${VIGILANTE_JWT_SECRET:-}" ]] || fail "VIGILANTE_JWT_SECRET ausente"

  local runtime db_host db_url_b64 jwt_b64 secret_patch
  runtime="$(kubectl get nodes -o jsonpath='{.items[0].status.nodeInfo.containerRuntimeVersion}')"
  [[ "${runtime}" == docker://* ]] || fail "o cluster não usa o runtime Docker: ${runtime}"

  db_host="$(printf '%s' "${VIGILANTE_DATABASE_URL}" | python3 -c \
    'import sys; from urllib.parse import urlsplit; print(urlsplit(sys.stdin.read()).hostname)')"
  [[ "${db_host}" == "${EXPECTED_DB_HOST}" ]] || fail "o .env.aws aponta para outro banco: ${db_host}"

  docker image inspect vigilante-ai-backend:latest >/dev/null 2>&1 || fail "imagem vigilante-ai-backend:latest ausente"
  docker image inspect vigilante-ai-frontend:latest >/dev/null 2>&1 || fail "imagem vigilante-ai-frontend:latest ausente"
  docker tag vigilante-ai-backend:latest vigilante-backend:latest
  docker tag vigilante-ai-frontend:latest vigilante-frontend:latest

  db_url_b64="$(printf '%s' "${VIGILANTE_DATABASE_URL}" | base64 -w0)"
  jwt_b64="$(printf '%s' "${VIGILANTE_JWT_SECRET}" | base64 -w0)"
  secret_patch="$(jq -nc --arg db "${db_url_b64}" --arg jwt "${jwt_b64}" '{data:{VIGILANTE_DATABASE_URL:$db,VIGILANTE_JWT_SECRET:$jwt}}')"
  kubectl -n "${NAMESPACE}" patch secret backend-secrets --type merge -p "${secret_patch}" >/dev/null
  unset VIGILANTE_DATABASE_URL VIGILANTE_JWT_SECRET db_url_b64 jwt_b64 secret_patch

  kubectl -n "${NAMESPACE}" patch configmap backend-config --type merge \
    -p '{"data":{"VIGILANTE_ALLOW_OPEN_REGISTRATION":"0","VIGILANTE_REPLAY_ROOT":"/media"}}' >/dev/null
  kubectl apply -f "${REPO_ROOT}/k8s/20-backend.yaml" -f "${REPO_ROOT}/k8s/30-frontend.yaml" >/dev/null
  kubectl -n "${NAMESPACE}" rollout restart deployment/backend deployment/frontend >/dev/null
  kubectl -n "${NAMESPACE}" rollout status deployment/backend --timeout=240s
  kubectl -n "${NAMESPACE}" rollout status deployment/frontend --timeout=180s
  status
}

status() {
  local host ready email password login_payload token cameras camera_count
  host="$(database_host)"
  [[ "${host}" == "${EXPECTED_DB_HOST}" ]] || fail "backend ainda aponta para ${host}"
  ready="$(kubectl -n "${NAMESPACE}" exec deploy/backend -- python -c \
    'import json, urllib.request; print(json.loads(urllib.request.urlopen("http://127.0.0.1:8000/readyz").read()))')"
  grep -q "'ready': True" <<<"${ready}" || fail "backend do k3s não está pronto"
  kubectl -n "${NAMESPACE}" exec deploy/backend -- test -f /media/canteiro2.mp4 || fail "replay não está montado"
  [[ -f "${DEMO_FILE}" ]] || fail "credenciais de demonstração ausentes"
  email="$(sed -n 's/^EMAIL=//p' "${DEMO_FILE}" | head -n 1)"
  password="$(sed -n 's/^PASSWORD=//p' "${DEMO_FILE}" | head -n 1)"
  login_payload="$(jq -n --arg email "${email}" --arg password "${password}" '{email:$email,password:$password}')"
  token="$(curl --fail --silent --show-error -H 'Content-Type: application/json' \
    --data "${login_payload}" "${PUBLIC_URL}/api/auth/login" | jq -r '.access_token')"
  [[ -n "${token}" && "${token}" != "null" ]] || fail "login público falhou"
  cameras="$(curl --fail --silent --show-error -H "Authorization: Bearer ${token}" "${PUBLIC_URL}/api/cameras")"
  camera_count="$(jq 'if type == "array" then length else (.items // .cameras // []) | length end' <<<"${cameras}")"
  (( camera_count >= 1 )) || fail "nenhuma câmera retornou pelo domínio público"
  printf 'OK: k3s usa Amazon RDS em %s.\n' "${host}"
  printf 'OK: replay montado, login público e %s câmera(s) acessível(is) em %s.\n' "${camera_count}" "${PUBLIC_URL}"
}

for command_name in base64 curl docker jq kubectl python3; do
  require_command "${command_name}"
done

case "${1:-}" in
  deploy) deploy ;;
  status) status ;;
  *) printf 'Uso: scripts/k3s-fase5-aws.sh deploy|status\n' >&2; exit 1 ;;
esac
