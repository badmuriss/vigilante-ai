# AWS RDS para a entrega da Fase 5

O ambiente acadêmico usa Amazon RDS for PostgreSQL como banco em nuvem. A aplicação executa no k3s da máquina de demonstração e é publicada em `https://vigilanteai.outis.com.br` por Cloudflare Tunnel. A inferência permanece nessa máquina para acessar o vídeo e o modelo sem manter computação ociosa na AWS.

## Recursos

| Recurso | Configuração |
|---|---|
| Região | `us-east-1` |
| Banco | PostgreSQL 16 |
| Instância | `db.t4g.micro`, Single-AZ |
| Armazenamento | 20 GiB gp3, criptografado |
| Rede | VPC padrão, IPv4 público temporário |
| Entrada | TCP 5432 limitado ao IP atual em `/32` |
| TLS | `rds.force_ssl=1` e cliente com `sslmode=require` |
| Extensões | `vector` e `pg_trgm`, criadas pela migration `0004` |

## Operação

```bash
aws login
scripts/aws-fase5.sh deploy
docker compose --env-file .env.aws build backend frontend
docker compose --env-file .env.aws \
  -f docker-compose.yml \
  -f docker-compose.aws.yml \
  up -d backend frontend
scripts/verify-fase5.sh
```

O Docker Compose continua disponível para validação local isolada. A demonstração pública usa o k3s:

```bash
scripts/k3s-fase5-aws.sh deploy
scripts/k3s-fase5-aws.sh status
```

O primeiro comando atualiza as imagens, configura o backend para usar o RDS e reinicia os deployments. O segundo confirma que o pod recebeu o endpoint do RDS, que o backend está pronto, que o arquivo replay foi montado e que login e listagem de câmeras funcionam pelo domínio público. O PostgreSQL interno do k3s permanece como opção de retorno, mas não é usado pelo backend nesse modo.

As credenciais da demonstração ficam em `.aws-fase5/demo-login`. Esse arquivo é local, tem permissão `600` e não entra no Git. O verificador autentica, consulta a câmera replay e exige pelo menos um alerta persistido sem imprimir senha ou token.

O deploy cria um usuário IAM temporário e limitado e passa a usá-lo para RDS, rede e budget. A credencial temporária, a senha, o JWT e a URL de conexão ficam em `.aws-fase5/` e `.env.aws`, ambos ignorados pelo Git.

Consulte o estado sem exibir credenciais:

```bash
scripts/aws-fase5.sh status
```

Se o IP público mudar, execute `scripts/aws-fase5.sh deploy` novamente. O script remove regras antigas do security group e mantém apenas o novo CIDR `/32`.

## Limpeza

Depois da gravação e da confirmação do grupo:

```bash
VIGILANTE_CONFIRM_DESTROY=vigilante-fase5 scripts/aws-fase5.sh destroy
```

Esse comando remove o RDS, o parameter group, o security group e o usuário IAM temporário. Ele preserva o budget para manter a trilha de custos.

Não remova o RDS enquanto o domínio público ainda precisar funcionar. Para voltar ao banco interno antes da limpeza da AWS, reaplique o secret anterior do cluster e reinicie o backend.
