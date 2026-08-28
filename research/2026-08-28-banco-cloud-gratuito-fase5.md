# Pesquisa: banco em nuvem sem custo para a Fase 5

## Protocol

- Question: como cumprir o requisito de banco de dados em nuvem da Fase 5 sem criar custo recorrente e sem reescrever o Vigilante.AI?
- Decision criterion: custo incremental zero, compatibilidade com PostgreSQL e `pgvector`, integração pequena e evidência suficiente para a avaliação.
- Falsifier: a opção será rejeitada se exigir cartão, perder PostgreSQL ou `pgvector`, ou impedir migrations e conexão pelo backend atual.
- Risk: material
- Credits used: 4

## Provider trail

| Intent | Provider | Tool or endpoint | Outcome | Credits | Fallback reason |
|---|---|---|---|---:|---|
| Reutilizar a análise anterior | local | `research/2026-08-28-cloudflare-gcp-vigilante-ai.md` | Cloud SQL identificado como principal custo fixo | 0 | None |
| Localizar documentação estruturada | Neon, Supabase e Cloudflare | `llms.txt` oficial | Índices oficiais encontrados com HTTP 200 | 0 | None |
| Verificar plano gratuito e compatibilidade | Neon | páginas Markdown oficiais | Plano Free, `pgvector` e conexão direta confirmados | 0 | None |
| Preservar as fontes | ScrapingDog | `/scrape?dynamic=false` | Quatro páginas oficiais preservadas | 4 | None |

## Claim ledger

| Claim | Source | Accessed | Snapshot | Primary | Direct | Current | Independent | Verdict |
|---|---|---|---|---|---|---|---|---|
| O Neon Free custa US$ 0 por mês, é permanente e não exige cartão | [Neon pricing](https://neon.com/pricing) | 2026-08-28 | `research/sources/free-cloud-db/neon-pricing/page.md` | yes | yes | yes | unknown | volatile |
| O Free inclui 100 CU-horas, 0,5 GB de armazenamento e 5 GB de egress por projeto | [Neon pricing](https://neon.com/pricing) | 2026-08-28 | `research/sources/free-cloud-db/neon-pricing/page.md` | yes | yes | yes | unknown | volatile |
| `pgvector` está disponível em todos os planos sem complemento pago | [Neon pgvector](https://neon.com/docs/extensions/pgvector) | 2026-08-28 | `research/sources/free-cloud-db/neon-pgvector/page.md` | yes | yes | yes | unknown | accepted |
| A conexão direta deve ser usada para migrations | [Neon connection pooling](https://neon.com/docs/connect/connection-pooling) | 2026-08-28 | `research/sources/free-cloud-db/neon-connection-pooling/page.md` | yes | yes | yes | unknown | accepted |
| Cloudflare Tunnel publica um serviço local sem IP público | [Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/) | 2026-08-28 | `research/sources/free-cloud-db/cloudflare-tunnel/page.md` | yes | yes | yes | unknown | accepted |

## Findings

Use Neon Free para o banco e mantenha frontend, backend e YOLO locais durante a gravação. O plano custa US$ 0 por mês e não exige cartão. [Neon pricing](https://neon.com/pricing), accessed 2026-08-28.

O plano inclui 100 CU-horas, 0,5 GB de armazenamento e 5 GB de transferência pública por projeto. Esses limites são adequados para migrations, usuários, câmeras, alertas e embeddings do MVP, desde que as imagens permaneçam fora do banco. [Neon pricing](https://neon.com/pricing), accessed 2026-08-28.

O backend atual continua usando SQLAlchemy, PostgreSQL e `pgvector`. O Neon disponibiliza `pgvector` em todos os planos sem complemento pago. [Neon pgvector](https://neon.com/docs/extensions/pgvector), accessed 2026-08-28.

Use a URL direta do Neon para executar Alembic e o backend da demonstração. O pooler é indicado para aplicações serverless, mas a documentação recomenda conexão direta para migrations. [Neon connection pooling](https://neon.com/docs/connect/connection-pooling), accessed 2026-08-28.

Uma URL HTTPS temporária pode ser criada com Cloudflare Tunnel para o vídeo. O túnel conecta o serviço local sem exigir IP publicamente roteável. [Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/), accessed 2026-08-28.

Não use D1 nesta entrega. D1 é SQLite e exigiria adaptar ORM, migrations e busca vetorial. Não use GCP se a equipe não aceita faturamento.

## Disagreements

None.

## Open questions

- A equipe já possui conta Neon ou precisa criar uma conta gratuita?
- A URL HTTPS precisa existir somente durante a gravação ou até a correção?

## Council review

- Status: not run
- Reason: as fontes oficiais são diretas e não há desacordo material.

## Sources consulted

- [Neon pricing](https://neon.com/pricing), accessed 2026-08-28.
- [Neon pgvector](https://neon.com/docs/extensions/pgvector), accessed 2026-08-28.
- [Neon connection pooling](https://neon.com/docs/connect/connection-pooling), accessed 2026-08-28.
- [Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/), accessed 2026-08-28.

## Trial by fire

- Primary-source claims: plano gratuito, limites, `pgvector`, conexão e túnel.
- Secondary-only claims: None.
- Volatile claims: preço e cotas do plano gratuito devem ser reconfirmados ao criar o projeto.
- Repository evidence: o backend já usa PostgreSQL, SQLAlchemy, Alembic e `pgvector`.
