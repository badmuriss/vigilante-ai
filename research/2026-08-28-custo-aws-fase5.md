# Pesquisa: custo AWS para o banco em nuvem da Fase 5

## Protocol

- Question: qual é o custo mínimo para cumprir na AWS o requisito de banco PostgreSQL em nuvem do Vigilante.AI usando os créditos exibidos pela equipe?
- Decision criterion: cumprir explicitamente o requisito acadêmico, manter PostgreSQL e `pgvector`, evitar migração de stack e limitar o consumo do crédito.
- Falsifier: a recomendação será rejeitada se o RDS não aceitar o crédito da conta, não suportar `pgvector` ou exigir um gasto relevante fora do crédito.
- Risk: material
- Credits used: 10

## Provider trail

| Intent | Provider | Tool or endpoint | Outcome | Credits | Fallback reason |
|---|---|---|---|---:|---|
| Ler o saldo mostrado pela equipe | local | imagem recebida e conversão por MarkItDown | O OCR não extraiu o texto; a inspeção visual mostrou dois créditos ativos | 0 | Inspeção visual necessária após falha do OCR |
| Consultar a conta AWS antes do login | AWS CLI | `sts get-caller-identity` | Sessão expirada; nenhuma consulta autenticada ou mutação foi realizada | 0 | Foi necessário executar `aws login` |
| Confirmar plano, saldo e elegibilidade | AWS APIs | Free Tier `get-account-plan-state` e Billing `get-credits` | Plano Paid ativo, US$ 160 restantes; a criação do RDS acrescentou dois créditos de atividade | 0 | None |
| Verificar consumo e inventário | AWS APIs | Billing allocation, Cost Explorer e RDS `describe-db-instances` | RDS disponível em `us-east-1`; Cost Explorer ainda sem dados | 0 | Conta recém-criada, dados de custo ainda não ingeridos |
| Obter preço atual de RDS | AWS | Price List Bulk API, `AmazonRDS`, `us-east-1` | JSON oficial publicado em 2026-08-28 consultado diretamente | 0 | None |
| Verificar armazenamento, extensão, IPv4 e créditos | AWS | documentação oficial | Cinco páginas oficiais preservadas | 10 | None |
| Reutilizar o câmbio | local | `research/2026-08-28-cloudflare-gcp-vigilante-ai.md` | Cotação BCB já preservada | 0 | None |

## Claim ledger

| Claim | Source | Accessed | Snapshot | Primary | Direct | Current | Independent | Verdict |
|---|---|---|---|---|---|---|---|---|
| RDS PostgreSQL `db.t4g.micro` Single-AZ custa US$ 0,016 por hora em `us-east-1` | [AWS Price List Bulk API](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-1/index.json) | 2026-08-28 | `research/sources/aws-cost/aws-rds-price-list-extract.md` | yes | yes | yes | unknown | volatile |
| Armazenamento RDS PostgreSQL gp3 custa US$ 0,115 por GB-mês em `us-east-1` | [AWS Price List Bulk API](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-1/index.json) | 2026-08-28 | `research/sources/aws-cost/aws-rds-price-list-extract.md` | yes | yes | yes | unknown | volatile |
| PostgreSQL gp3 começa em 20 GiB no RDS | [AWS RDS storage](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Storage.html) | 2026-08-28 | `research/sources/aws-cost/aws-rds-storage/page.md` | yes | yes | yes | unknown | accepted |
| Um IPv4 público em uso custa US$ 0,005 por hora e o RDS público é cobrado | [AWS VPC pricing](https://aws.amazon.com/vpc/pricing/) | 2026-08-28 | `research/sources/aws-cost/aws-public-ipv4-pricing/page.md` | yes | yes | yes | unknown | volatile |
| RDS PostgreSQL oferece `pgvector` | [AWS PostgreSQL extensions](https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-extensions.html) | 2026-08-28 | `research/sources/aws-cost/aws-rds-pg-extensions/page.md` | yes | yes | yes | unknown | accepted |
| A conta Free Tier atual recebe US$ 100 inicialmente | [AWS Free Tier](https://aws.amazon.com/free/) | 2026-08-28 | `research/sources/aws-cost/aws-free-tier/page.md` | yes | yes | yes | unknown | volatile |
| Crédito promocional só cobre serviços elegíveis designados | [AWS Promotional Credit Terms](https://aws.amazon.com/awscredits/) | 2026-08-28 | `research/sources/aws-cost/aws-promotional-credit-terms/page.md` | yes | yes | yes | unknown | accepted |
| A cotação oficial mais recente disponível é R$ 5,1642 por US$ em 27/08/2026 | [Banco Central do Brasil](https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/10?formato=json) | 2026-08-28 | `research/sources/cloud-cost/bcb-usd-brl/page.md` | yes | yes | yes | unknown | volatile |
| A conta está no plano Paid ativo e tem US$ 160 de créditos restantes | [AWS Free Tier API](https://docs.aws.amazon.com/cli/latest/reference/freetier/get-account-plan-state.html) | 2026-08-28 | `research/sources/aws-cost/account-verification-2026-08-28.md` | yes | yes | yes | unknown | accepted |
| Os créditos de US$ 100 e US$ 20 listam Amazon RDS como produto aplicável | [AWS Billing API](https://docs.aws.amazon.com/cli/latest/reference/billing/get-credits.html) | 2026-08-28 | `research/sources/aws-cost/account-verification-2026-08-28.md` | yes | yes | yes | unknown | accepted |
| O RDS `vigilante-fase5` está disponível com PostgreSQL 16.15, `db.t4g.micro`, 20 GiB gp3 e criptografia | [AWS RDS API](https://docs.aws.amazon.com/cli/latest/reference/rds/describe-db-instances.html) | 2026-08-28 | `research/sources/aws-cost/account-verification-2026-08-28.md` | yes | yes | yes | unknown | accepted |

## Findings

A escolha recomendada é Amazon RDS for PostgreSQL em `us-east-1`, classe `db.t4g.micro`, Single-AZ, com 20 GiB gp3. O RDS suporta `pgvector`, portanto o backend mantém PostgreSQL, SQLAlchemy, Alembic e busca vetorial sem migração de banco. [AWS RDS storage](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Storage.html) e [AWS PostgreSQL extensions](https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-extensions.html), accessed 2026-08-28.

O custo mensal de referência do banco privado é US$ 13,98: `730 × US$ 0,016 + 20 × US$ 0,115`. As tarifas são da [AWS Price List Bulk API](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-1/index.json), accessed 2026-08-28.

Para conectar o backend local diretamente ao RDS durante a demonstração, some um IPv4 público a US$ 0,005 por hora. O total por 730 horas passa para US$ 17,63, aproximadamente R$ 91,04 pelo câmbio de R$ 5,1642 por US$. [AWS VPC pricing](https://aws.amazon.com/vpc/pricing/), [AWS Price List Bulk API](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-1/index.json) e [Banco Central do Brasil](https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/10?formato=json), accessed 2026-08-28.

Se o RDS público existir apenas por cinco dias, a estimativa proporcional é US$ 2,90, cerca de R$ 14,97. Por sete dias, US$ 4,06, cerca de R$ 20,95. As estimativas usam as tarifas atuais da [AWS Price List Bulk API](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-1/index.json), [AWS VPC pricing](https://aws.amazon.com/vpc/pricing/) e o câmbio do [Banco Central do Brasil](https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/10?formato=json), accessed 2026-08-28.

Uma consulta autenticada confirmou que a conta está no plano Paid ativo e possui US$ 160 restantes. A captura anterior mostrava US$ 120. Depois do deploy do RDS, duas atividades acrescentaram US$ 20 cada ao saldo. A Billing API lista `Amazon Relational Database Service` como produto aplicável nos créditos iniciais. Portanto, o saldo elegível pode absorver a cobrança prevista do RDS. [AWS Free Tier API](https://docs.aws.amazon.com/cli/latest/reference/freetier/get-account-plan-state.html) e [AWS Billing API](https://docs.aws.amazon.com/cli/latest/reference/billing/get-credits.html), accessed 2026-08-28. Evidência: `research/sources/aws-cost/account-verification-2026-08-28.md`.

Os US$ 160 cobrem aproximadamente 9,08 meses do cenário público estimado em US$ 17,63 por mês. Esse cálculo é apenas uma referência: o grupo deve apagar o RDS depois da gravação, em vez de consumir o saldo por ociosidade. [AWS Billing API](https://docs.aws.amazon.com/cli/latest/reference/billing/get-credits.html), [AWS Price List Bulk API](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-1/index.json) e [AWS VPC pricing](https://aws.amazon.com/vpc/pricing/), accessed 2026-08-28.

Para a entrega, mantenha frontend, backend e processamento YOLO locais e use apenas o RDS em nuvem. Isso cumpre o requisito literal de banco em provedor cloud com o menor consumo previsto. O custo em dinheiro é US$ 0 enquanto os créditos elegíveis absorverem a cobrança. [AWS Billing API](https://docs.aws.amazon.com/cli/latest/reference/billing/get-credits.html), accessed 2026-08-28.

## Disagreements

O screenshot anterior registrou US$ 120, mas a consulta autenticada feita depois do deploy registra US$ 160. A diferença corresponde a dois créditos de atividade de US$ 20 listados pela Billing API. [AWS Free Tier API](https://docs.aws.amazon.com/cli/latest/reference/freetier/get-account-plan-state.html) e [AWS Billing API](https://docs.aws.amazon.com/cli/latest/reference/billing/get-credits.html), accessed 2026-08-28.

## Open questions

- O Cost Explorer passará a mostrar o consumo diário quando concluir a primeira ingestão de dados?

## Council review

- Status: not run
- Reason: o risco é material, mas as tarifas e regras usadas vêm diretamente das fontes oficiais e não há fonte primária conflitante sobre o custo unitário.
- Accepted findings: None.
- Rejected findings: None.

## Sources consulted

- [AWS Price List Bulk API, Amazon RDS em `us-east-1`](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-1/index.json), accessed 2026-08-28.
- [AWS RDS storage](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Storage.html), accessed 2026-08-28.
- [AWS PostgreSQL extensions](https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-extensions.html), accessed 2026-08-28.
- [AWS VPC pricing](https://aws.amazon.com/vpc/pricing/), accessed 2026-08-28.
- [AWS Free Tier](https://aws.amazon.com/free/), accessed 2026-08-28.
- [AWS Promotional Credit Terms](https://aws.amazon.com/awscredits/), accessed 2026-08-28.
- [AWS Free Tier API, account plan](https://docs.aws.amazon.com/cli/latest/reference/freetier/get-account-plan-state.html), accessed 2026-08-28.
- [AWS Billing API, credits](https://docs.aws.amazon.com/cli/latest/reference/billing/get-credits.html), accessed 2026-08-28.
- [AWS RDS API, instances](https://docs.aws.amazon.com/cli/latest/reference/rds/describe-db-instances.html), accessed 2026-08-28.
- [AWS Free Tier API, activity](https://docs.aws.amazon.com/cli/latest/reference/freetier/get-account-activity.html), accessed 2026-08-28.
- [Banco Central do Brasil](https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/10?formato=json), accessed 2026-08-28.

## Trial by fire

- Primary-source claims: preços unitários, armazenamento mínimo, cobrança de IPv4, suporte a `pgvector`, crédito inicial e elegibilidade dos créditos.
- Secondary-only claims: None.
- Volatile claims: tarifas, câmbio e saldo devem ser reconfirmados no momento da criação do RDS.
- Repository evidence: o cálculo assume que a aplicação atual continuará usando PostgreSQL e `pgvector` sem hospedagem integral na AWS.
