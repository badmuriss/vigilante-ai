#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env.aws"
DEMO_FILE="${REPO_ROOT}/.aws-fase5/demo-login"
API_URL="${VIGILANTE_API_URL:-http://localhost:8000}"
DB_IDENTIFIER="vigilante-fase5"
AWS_REGION="us-east-1"

fail() {
  printf 'FALHA: %s\n' "$1" >&2
  exit 1
}

for command_name in aws curl docker jq; do
  command -v "${command_name}" >/dev/null 2>&1 || fail "comando ausente: ${command_name}"
done

[[ -f "${ENV_FILE}" ]] || fail ".env.aws não encontrado; execute scripts/aws-fase5.sh deploy"
[[ -f "${DEMO_FILE}" ]] || fail ".aws-fase5/demo-login não encontrado"

db_state="$(aws rds describe-db-instances \
  --region "${AWS_REGION}" \
  --db-instance-identifier "${DB_IDENTIFIER}" \
  --query 'DBInstances[0].[DBInstanceStatus,EngineVersion,DBInstanceClass,AllocatedStorage,StorageEncrypted,PubliclyAccessible,MultiAZ]' \
  --output text)"
read -r db_status db_version db_class db_storage db_encrypted db_public db_multi_az <<<"${db_state}"
[[ "${db_status}" == "available" ]] || fail "RDS não está disponível: ${db_status}"
[[ "${db_version}" == 16.* ]] || fail "versão PostgreSQL inesperada: ${db_version}"
[[ "${db_class}" == "db.t4g.micro" ]] || fail "classe RDS inesperada: ${db_class}"
[[ "${db_storage}" == "20" && "${db_encrypted}" == "True" ]] || fail "armazenamento RDS divergente"
[[ "${db_public}" == "True" && "${db_multi_az}" == "False" ]] || fail "topologia RDS divergente"

compose=(docker compose --env-file "${ENV_FILE}" -f "${REPO_ROOT}/docker-compose.yml" -f "${REPO_ROOT}/docker-compose.aws.yml")
"${compose[@]}" ps --status running backend frontend | grep -q backend || fail "backend não está em execução"
"${compose[@]}" ps --status running backend frontend | grep -q frontend || fail "frontend não está em execução"

health="$(curl --fail --silent --show-error "${API_URL}/healthz")"
ready="$(curl --fail --silent --show-error "${API_URL}/readyz")"
jq -e '.status == "ok" or .healthy == true' >/dev/null <<<"${health}" || fail "/healthz retornou conteúdo inesperado"
jq -e '.ready == true and .db == true and .model == true' >/dev/null <<<"${ready}" || fail "/readyz não está pronto"

email="$(sed -n 's/^EMAIL=//p' "${DEMO_FILE}" | head -n 1)"
password="$(sed -n 's/^PASSWORD=//p' "${DEMO_FILE}" | head -n 1)"
[[ -n "${email}" && -n "${password}" ]] || fail "credenciais de demonstração incompletas"

login_payload="$(jq -n --arg email "${email}" --arg password "${password}" '{email:$email,password:$password}')"
token="$(curl --fail --silent --show-error \
  -H 'Content-Type: application/json' \
  --data "${login_payload}" \
  "${API_URL}/api/auth/login" | jq -r '.access_token')"
[[ -n "${token}" && "${token}" != "null" ]] || fail "login de demonstração falhou"

cameras="$(curl --fail --silent --show-error -H "Authorization: Bearer ${token}" "${API_URL}/api/cameras")"
camera_id="$(jq -r '.cameras[] | select(.source_kind == "replay") | .id' <<<"${cameras}" | head -n 1)"
[[ -n "${camera_id}" ]] || fail "nenhuma câmera replay persistida"
alerts="$(curl --fail --silent --show-error \
  -H "Authorization: Bearer ${token}" \
  "${API_URL}/api/cameras/${camera_id}/alerts?status=all")"
camera_count="$(jq 'if type == "array" then length else (.items // .cameras // []) | length end' <<<"${cameras}")"
alert_count="$(jq 'if type == "array" then length else (.items // .alerts // []) | length end' <<<"${alerts}")"
(( camera_count >= 1 )) || fail "nenhuma câmera persistida"
(( alert_count >= 1 )) || fail "nenhum alerta persistido"

db_evidence="$("${compose[@]}" exec -T backend python -c \
  'from sqlalchemy import text; from app.db.base import get_engine; e=get_engine(); c=e.connect(); r=c.execute(text("select version(), extversion from pg_extension where extname=:name"), {"name":"vector"}); print(r.one()); print(c.execute(text("select version_num from alembic_version")).scalar_one()); print(c.execute(text("select ssl from pg_stat_ssl where pid=pg_backend_pid()")).scalar_one()); c.close()' 2>/dev/null)"
grep -q "0005" <<<"${db_evidence}" || fail "Alembic não está na revisão 0005"
grep -q "True" <<<"${db_evidence}" || fail "conexão do banco sem TLS"

printf 'OK: RDS PostgreSQL %s, %s, %s GiB, TLS, pgvector, migration 0005.\n' "${db_version}" "${db_class}" "${db_storage}"
printf 'OK: aplicação pronta com %s câmera(s) e %s alerta(s) persistido(s).\n' "${camera_count}" "${alert_count}"
