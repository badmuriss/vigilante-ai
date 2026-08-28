#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${VIGILANTE_AWS_STATE_DIR:-${REPO_ROOT}/.aws-fase5}"
STATE_FILE="${STATE_DIR}/state.env"
PASSWORD_FILE="${STATE_DIR}/db-password"
CREDENTIALS_FILE="${STATE_DIR}/iam-credentials"
ENV_FILE="${REPO_ROOT}/.env.aws"

EXPECTED_ACCOUNT_ID="426902158910"
AWS_REGION="us-east-1"
DEPLOY_USER_NAME="vigilante-fase5-deployer"
DEPLOY_POLICY_NAME="VigilanteFase5DeploymentPolicy"
BUDGET_NAME="vigilante-fase5-usd10"
DB_IDENTIFIER="vigilante-fase5"
DB_NAME="vigilante"
DB_USERNAME="vigilante"
DB_INSTANCE_CLASS="db.t4g.micro"
DB_ENGINE_VERSION="16.15"
DB_STORAGE_GIB="20"
DB_PARAMETER_GROUP="vigilante-fase5-pg16"
SECURITY_GROUP_NAME="vigilante-fase5-postgres"

usage() {
  printf '%s\n' \
    "Uso: scripts/aws-fase5.sh <comando>" \
    "" \
    "Comandos:" \
    "  bootstrap  cria ou atualiza o usuário IAM limitado" \
    "  deploy     cria budget, segurança e RDS" \
    "  status     consulta o estado sem exibir segredos" \
    "  env        regenera .env.aws a partir do estado local" \
    "  destroy    remove RDS e rede após confirmação explícita"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Comando ausente: %s\n' "$1" >&2
    exit 1
  fi
}

assert_login() {
  local account_id
  account_id="$(aws sts get-caller-identity --region "${AWS_REGION}" --query Account --output text)"
  if [[ "${account_id}" != "${EXPECTED_ACCOUNT_ID}" ]]; then
    printf 'Conta AWS incorreta. Esperada %s; recebida %s.\n' "${EXPECTED_ACCOUNT_ID}" "${account_id}" >&2
    exit 1
  fi
}

load_state() {
  if [[ ! -f "${STATE_FILE}" ]]; then
    printf 'Estado local ausente: %s\n' "${STATE_FILE}" >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  source "${STATE_FILE}"
  if [[ "${STATE_ACCOUNT_ID:-}" != "${EXPECTED_ACCOUNT_ID}" || "${STATE_REGION:-}" != "${AWS_REGION}" ]]; then
    printf 'O estado local pertence a outra conta ou região.\n' >&2
    exit 1
  fi
}

write_state() {
  mkdir -p "${STATE_DIR}"
  chmod 700 "${STATE_DIR}"
  local temporary_state
  temporary_state="$(mktemp "${STATE_DIR}/state.XXXXXX")"
  {
    printf 'STATE_ACCOUNT_ID=%q\n' "${EXPECTED_ACCOUNT_ID}"
    printf 'STATE_REGION=%q\n' "${AWS_REGION}"
    printf 'STATE_DEPLOYER_ARN=%q\n' "${STATE_DEPLOYER_ARN}"
    printf 'STATE_VPC_ID=%q\n' "${STATE_VPC_ID}"
    printf 'STATE_SECURITY_GROUP_ID=%q\n' "${STATE_SECURITY_GROUP_ID}"
    printf 'STATE_ALLOWED_CIDR=%q\n' "${STATE_ALLOWED_CIDR}"
    printf 'STATE_DB_IDENTIFIER=%q\n' "${DB_IDENTIFIER}"
    printf 'STATE_DB_ENDPOINT=%q\n' "${STATE_DB_ENDPOINT:-}"
  } >"${temporary_state}"
  chmod 600 "${temporary_state}"
  mv "${temporary_state}" "${STATE_FILE}"
}

bootstrap_user() {
  assert_login
  local caller_arn account_id deployer_arn temporary_dir policy_file access_key
  caller_arn="$(aws sts get-caller-identity --region "${AWS_REGION}" --query Arn --output text)"
  account_id="$(aws sts get-caller-identity --region "${AWS_REGION}" --query Account --output text)"
  temporary_dir="$(mktemp -d)"
  policy_file="${temporary_dir}/policy.json"

  if [[ "${caller_arn}" != "arn:aws:iam::${account_id}:root" ]]; then
    printf 'Bootstrap exige a sessão raiz atual.\n' >&2
    exit 1
  fi

  if ! aws iam get-role --role-name AWSServiceRoleForRDS >/dev/null 2>&1; then
    aws iam create-service-linked-role --aws-service-name rds.amazonaws.com >/dev/null
  fi

  cat >"${policy_file}" <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadAccountAndNetwork",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeSecurityGroupRules",
        "rds:DescribeDBInstances",
        "rds:DescribeDBParameterGroups",
        "rds:DescribeDBParameters",
        "rds:ListTagsForResource"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ManageProjectNetwork",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateSecurityGroup",
        "ec2:DeleteSecurityGroup",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupIngress",
        "ec2:CreateTags",
        "ec2:DeleteTags"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ManageProjectDatabase",
      "Effect": "Allow",
      "Action": [
        "rds:AddTagsToResource",
        "rds:CreateDBInstance",
        "rds:DeleteDBInstance",
        "rds:ModifyDBInstance",
        "rds:CreateDBParameterGroup",
        "rds:ModifyDBParameterGroup",
        "rds:DeleteDBParameterGroup"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ManageProjectBudget",
      "Effect": "Allow",
      "Action": [
        "budgets:CreateBudget",
        "budgets:ModifyBudget",
        "budgets:ViewBudget",
        "budgets:CreateNotification",
        "budgets:UpdateNotification",
        "budgets:CreateSubscriber",
        "budgets:UpdateSubscriber"
      ],
      "Resource": "*"
    }
  ]
}
JSON

  if ! aws iam get-user --user-name "${DEPLOY_USER_NAME}" >/dev/null 2>&1; then
    aws iam create-user \
      --user-name "${DEPLOY_USER_NAME}" \
      --tags Key=Project,Value=VigilanteAI Key=Phase,Value=Fase5 >/dev/null
  fi
  aws iam put-user-policy \
    --user-name "${DEPLOY_USER_NAME}" \
    --policy-name "${DEPLOY_POLICY_NAME}" \
    --policy-document "file://${policy_file}" >/dev/null

  deployer_arn="$(aws iam get-user --user-name "${DEPLOY_USER_NAME}" --query 'User.Arn' --output text)"
  mkdir -p "${STATE_DIR}"
  chmod 700 "${STATE_DIR}"
  if [[ ! -f "${CREDENTIALS_FILE}" ]]; then
    access_key="$(aws iam create-access-key \
      --user-name "${DEPLOY_USER_NAME}" \
      --query 'AccessKey.[AccessKeyId,SecretAccessKey]' \
      --output text)"
    read -r AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY <<<"${access_key}"
    {
      printf 'AWS_ACCESS_KEY_ID=%q\n' "${AWS_ACCESS_KEY_ID}"
      printf 'AWS_SECRET_ACCESS_KEY=%q\n' "${AWS_SECRET_ACCESS_KEY}"
    } >"${CREDENTIALS_FILE}"
    chmod 600 "${CREDENTIALS_FILE}"
    unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
  fi
  printf '%s\n' "${deployer_arn}" >"${STATE_DIR}/deployer-arn"
  chmod 600 "${STATE_DIR}/deployer-arn"
  rm -rf "${temporary_dir}"
  printf 'Usuário IAM temporário pronto: %s\n' "${DEPLOY_USER_NAME}"
}

activate_deployer() {
  if [[ ! -f "${CREDENTIALS_FILE}" || ! -f "${STATE_DIR}/deployer-arn" ]]; then
    printf 'Credencial IAM temporária ausente. Execute bootstrap.\n' >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  source "${CREDENTIALS_FILE}"
  export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
  unset AWS_SESSION_TOKEN || true
  export AWS_REGION AWS_DEFAULT_REGION="${AWS_REGION}"
  STATE_DEPLOYER_ARN="$(<"${STATE_DIR}/deployer-arn")"
  local account_id
  for _attempt in $(seq 1 10); do
    account_id="$(aws sts get-caller-identity --region "${AWS_REGION}" --query Account --output text 2>/dev/null || true)"
    if [[ "${account_id}" == "${EXPECTED_ACCOUNT_ID}" ]]; then
      return
    fi
    sleep 2
  done
  printf 'A credencial IAM temporária não propagou após 20 segundos.\n' >&2
  exit 1
}

ensure_budget() {
  local current_budget temporary_dir budget_file
  current_budget="$(aws budgets describe-budget \
    --account-id "${EXPECTED_ACCOUNT_ID}" \
    --budget-name "${BUDGET_NAME}" \
    --query 'Budget.BudgetName' --output text 2>/dev/null || true)"
  if [[ "${current_budget}" == "${BUDGET_NAME}" ]]; then
    return
  fi
  temporary_dir="$(mktemp -d)"
  budget_file="${temporary_dir}/budget.json"
  cat >"${budget_file}" <<JSON
{
  "BudgetName": "${BUDGET_NAME}",
  "BudgetLimit": {"Amount": "10", "Unit": "USD"},
  "CostTypes": {
    "IncludeTax": true,
    "IncludeSubscription": true,
    "UseBlended": false,
    "IncludeRefund": true,
    "IncludeCredit": true,
    "IncludeUpfront": true,
    "IncludeRecurring": true,
    "IncludeOtherSubscription": true,
    "IncludeSupport": true,
    "IncludeDiscount": true,
    "UseAmortized": false
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
JSON
  aws budgets create-budget \
    --account-id "${EXPECTED_ACCOUNT_ID}" \
    --budget "file://${budget_file}" >/dev/null
  rm -rf "${temporary_dir}"
}

resolve_public_cidr() {
  local public_ip
  public_ip="$(curl --fail --silent --show-error https://checkip.amazonaws.com | tr -d '[:space:]')"
  python3 - "${public_ip}" <<'PY'
import ipaddress
import sys

address = ipaddress.ip_address(sys.argv[1])
if address.version != 4:
    raise SystemExit("A conexão atual não possui IPv4 público")
print(f"{address}/32")
PY
}

ensure_security_group() {
  local existing_group
  STATE_VPC_ID="$(aws ec2 describe-vpcs \
    --filters Name=is-default,Values=true \
    --query 'Vpcs[0].VpcId' --output text)"
  if [[ -z "${STATE_VPC_ID}" || "${STATE_VPC_ID}" == "None" ]]; then
    printf 'A região %s não possui VPC padrão.\n' "${AWS_REGION}" >&2
    exit 1
  fi
  STATE_ALLOWED_CIDR="$(resolve_public_cidr)"
  existing_group="$(aws ec2 describe-security-groups \
    --filters Name=vpc-id,Values="${STATE_VPC_ID}" Name=group-name,Values="${SECURITY_GROUP_NAME}" \
    --query 'SecurityGroups[0].GroupId' --output text)"
  if [[ -z "${existing_group}" || "${existing_group}" == "None" ]]; then
    STATE_SECURITY_GROUP_ID="$(aws ec2 create-security-group \
      --group-name "${SECURITY_GROUP_NAME}" \
      --description "PostgreSQL temporario do Vigilante.AI Fase 5" \
      --vpc-id "${STATE_VPC_ID}" \
      --tag-specifications 'ResourceType=security-group,Tags=[{Key=Project,Value=VigilanteAI},{Key=Phase,Value=Fase5}]' \
      --query GroupId --output text)"
  else
    STATE_SECURITY_GROUP_ID="${existing_group}"
  fi

  local existing_rules rule_id rule_cidr
  existing_rules="$(aws ec2 describe-security-group-rules \
    --filters Name=group-id,Values="${STATE_SECURITY_GROUP_ID}" \
    --query 'SecurityGroupRules[?IsEgress==`false`].[SecurityGroupRuleId,CidrIpv4]' \
    --output text)"
  while read -r rule_id rule_cidr; do
    [[ -z "${rule_id:-}" ]] && continue
    if [[ "${rule_cidr}" != "${STATE_ALLOWED_CIDR}" ]]; then
      aws ec2 revoke-security-group-ingress \
        --group-id "${STATE_SECURITY_GROUP_ID}" \
        --security-group-rule-ids "${rule_id}" >/dev/null
    fi
  done <<<"${existing_rules}"

  if ! aws ec2 describe-security-group-rules \
    --filters Name=group-id,Values="${STATE_SECURITY_GROUP_ID}" \
    --query "SecurityGroupRules[?IsEgress==\`false\` && CidrIpv4=='${STATE_ALLOWED_CIDR}' && FromPort==\`5432\` && ToPort==\`5432\`] | length(@)" \
    --output text | grep -qx '1'; then
    aws ec2 authorize-security-group-ingress \
      --group-id "${STATE_SECURITY_GROUP_ID}" \
      --ip-permissions "IpProtocol=tcp,FromPort=5432,ToPort=5432,IpRanges=[{CidrIp=${STATE_ALLOWED_CIDR},Description=Vigilante-Fase5}]" >/dev/null
  fi
}

ensure_parameter_group() {
  if ! aws rds describe-db-parameter-groups \
    --db-parameter-group-name "${DB_PARAMETER_GROUP}" >/dev/null 2>&1; then
    aws rds create-db-parameter-group \
      --db-parameter-group-name "${DB_PARAMETER_GROUP}" \
      --db-parameter-group-family postgres16 \
      --description "TLS obrigatório para o Vigilante.AI Fase 5" \
      --tags Key=Project,Value=VigilanteAI Key=Phase,Value=Fase5 >/dev/null
  fi
  aws rds modify-db-parameter-group \
    --db-parameter-group-name "${DB_PARAMETER_GROUP}" \
    --parameters 'ParameterName=rds.force_ssl,ParameterValue=1,ApplyMethod=immediate' >/dev/null
}

ensure_password() {
  mkdir -p "${STATE_DIR}"
  chmod 700 "${STATE_DIR}"
  if [[ ! -f "${PASSWORD_FILE}" ]]; then
    openssl rand -hex 24 >"${PASSWORD_FILE}"
    chmod 600 "${PASSWORD_FILE}"
  fi
}

ensure_database() {
  local database_status password
  database_status="$(aws rds describe-db-instances \
    --db-instance-identifier "${DB_IDENTIFIER}" \
    --query 'DBInstances[0].DBInstanceStatus' --output text 2>/dev/null || true)"
  if [[ -z "${database_status}" ]]; then
    password="$(<"${PASSWORD_FILE}")"
    aws rds create-db-instance \
      --db-instance-identifier "${DB_IDENTIFIER}" \
      --db-name "${DB_NAME}" \
      --engine postgres \
      --engine-version "${DB_ENGINE_VERSION}" \
      --db-instance-class "${DB_INSTANCE_CLASS}" \
      --allocated-storage "${DB_STORAGE_GIB}" \
      --storage-type gp3 \
      --storage-encrypted \
      --master-username "${DB_USERNAME}" \
      --master-user-password "${password}" \
      --vpc-security-group-ids "${STATE_SECURITY_GROUP_ID}" \
      --db-parameter-group-name "${DB_PARAMETER_GROUP}" \
      --backup-retention-period 0 \
      --port 5432 \
      --publicly-accessible \
      --no-multi-az \
      --no-deletion-protection \
      --auto-minor-version-upgrade \
      --tags Key=Project,Value=VigilanteAI Key=Phase,Value=Fase5 Key=Purpose,Value=AcademicDemo >/dev/null
  else
    aws rds modify-db-instance \
      --db-instance-identifier "${DB_IDENTIFIER}" \
      --vpc-security-group-ids "${STATE_SECURITY_GROUP_ID}" \
      --db-parameter-group-name "${DB_PARAMETER_GROUP}" \
      --apply-immediately >/dev/null
  fi
  printf 'Aguardando o RDS ficar disponível. Isso pode levar alguns minutos.\n'
  aws rds wait db-instance-available --db-instance-identifier "${DB_IDENTIFIER}"
  STATE_DB_ENDPOINT="$(aws rds describe-db-instances \
    --db-instance-identifier "${DB_IDENTIFIER}" \
    --query 'DBInstances[0].Endpoint.Address' --output text)"
}

write_env_file() {
  load_state
  if [[ ! -f "${PASSWORD_FILE}" ]]; then
    printf 'Senha local do banco ausente.\n' >&2
    exit 1
  fi
  local password jwt_secret temporary_env
  password="$(<"${PASSWORD_FILE}")"
  jwt_secret="$(openssl rand -hex 32)"
  if [[ -f "${ENV_FILE}" ]]; then
    local existing_jwt
    existing_jwt="$(sed -n 's/^VIGILANTE_JWT_SECRET=//p' "${ENV_FILE}" | head -n 1)"
    if [[ -n "${existing_jwt}" ]]; then
      jwt_secret="${existing_jwt}"
    fi
  fi
  temporary_env="$(mktemp "${STATE_DIR}/env.XXXXXX")"
  {
    printf 'VIGILANTE_DATABASE_URL=postgresql+psycopg2://%s:%s@%s:5432/%s?sslmode=require\n' \
      "${DB_USERNAME}" "${password}" "${STATE_DB_ENDPOINT}" "${DB_NAME}"
    printf 'VIGILANTE_JWT_SECRET=%s\n' "${jwt_secret}"
    printf 'VIGILANTE_ALLOW_OPEN_REGISTRATION=0\n'
    printf 'VIGILANTE_REPLAY_ROOT=/media\n'
  } >"${temporary_env}"
  chmod 600 "${temporary_env}"
  mv "${temporary_env}" "${ENV_FILE}"
  printf 'Arquivo local criado: .env.aws\n'
}

deploy() {
  bootstrap_user
  activate_deployer
  ensure_budget
  ensure_security_group
  ensure_parameter_group
  ensure_password
  STATE_DB_ENDPOINT=""
  write_state
  ensure_database
  write_state
  write_env_file
  printf 'RDS disponível e configuração local pronta.\n'
}

status() {
  assert_login
  local plan balance db_status endpoint
  plan="$(aws freetier get-account-plan-state --region "${AWS_REGION}" --query accountPlanType --output text)"
  balance="$(aws freetier get-account-plan-state --region "${AWS_REGION}" --query accountPlanRemainingCredits.amount --output text)"
  db_status="$(aws rds describe-db-instances --region "${AWS_REGION}" \
    --db-instance-identifier "${DB_IDENTIFIER}" \
    --query 'DBInstances[0].DBInstanceStatus' --output text 2>/dev/null || printf 'absent')"
  endpoint="$(aws rds describe-db-instances --region "${AWS_REGION}" \
    --db-instance-identifier "${DB_IDENTIFIER}" \
    --query 'DBInstances[0].Endpoint.Address' --output text 2>/dev/null || printf '-')"
  printf 'Conta: %s\nRegião: %s\nPlano: %s\nCréditos restantes: US$ %s\nRDS: %s\nEndpoint: %s\n' \
    "${EXPECTED_ACCOUNT_ID}" "${AWS_REGION}" "${plan}" "${balance}" "${db_status}" "${endpoint}"
}

destroy() {
  load_state
  if [[ "${VIGILANTE_CONFIRM_DESTROY:-}" != "${DB_IDENTIFIER}" ]]; then
    printf 'Defina VIGILANTE_CONFIRM_DESTROY=%s para confirmar a remoção.\n' "${DB_IDENTIFIER}" >&2
    exit 1
  fi
  activate_deployer
  if aws rds describe-db-instances --db-instance-identifier "${DB_IDENTIFIER}" >/dev/null 2>&1; then
    aws rds delete-db-instance \
      --db-instance-identifier "${DB_IDENTIFIER}" \
      --skip-final-snapshot \
      --delete-automated-backups >/dev/null
    aws rds wait db-instance-deleted --db-instance-identifier "${DB_IDENTIFIER}"
  fi
  aws rds delete-db-parameter-group --db-parameter-group-name "${DB_PARAMETER_GROUP}" >/dev/null 2>&1 || true
  aws ec2 delete-security-group --group-id "${STATE_SECURITY_GROUP_ID}" >/dev/null 2>&1 || true
  local access_key_id
  access_key_id="$(sed -n 's/^AWS_ACCESS_KEY_ID=//p' "${CREDENTIALS_FILE}" | head -n 1)"
  unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN || true
  assert_login
  aws iam delete-access-key --user-name "${DEPLOY_USER_NAME}" --access-key-id "${access_key_id}" >/dev/null
  aws iam delete-user-policy --user-name "${DEPLOY_USER_NAME}" --policy-name "${DEPLOY_POLICY_NAME}" >/dev/null
  aws iam delete-user --user-name "${DEPLOY_USER_NAME}" >/dev/null
  rm -f "${CREDENTIALS_FILE}" "${STATE_DIR}/deployer-arn"
  printf 'RDS, parameter group, security group e usuário IAM temporário removidos. O budget foi preservado.\n'
}

require_command aws
require_command curl
require_command openssl
require_command python3

case "${1:-}" in
  bootstrap) bootstrap_user ;;
  deploy) deploy ;;
  status) status ;;
  env) write_env_file ;;
  destroy) destroy ;;
  *) usage; exit 1 ;;
esac
