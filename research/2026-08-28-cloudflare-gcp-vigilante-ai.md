# Pesquisa: Cloudflare e GCP para o Vigilante.AI

## Protocol

- Question: qual divisão entre Cloudflare e GCP atende a entrega acadêmica e reduz custo e migração sem quebrar RTSP, YOLO, PostgreSQL com `pgvector` e as evidências do Vigilante.AI?
- Decision criterion: cumprir o requisito de banco em nuvem e manter a demonstração funcional com a menor reescrita e o menor custo incremental.
- Falsifier: a recomendação pelo GCP será rejeitada se a Cloudflare executar todo o backend atual e o banco PostgreSQL com `pgvector` sem migração material, ou se o GCP ultrapassar o orçamento registrado neste documento.
- Risk: material
- Credits used: 39

## Provider trail

| Intent | Provider | Tool or endpoint | Outcome | Credits | Fallback reason |
|---|---|---|---|---:|---|
| Reutilizar decisões anteriores | local | `research/*.md` | Quatro estudos GCP de 12/08/2026 localizados | 0 | None |
| Verificar o provedor pago | ScrapingDog | `key-env-check.sh` e `account_summary.sh` | Chave atual e saldo inicial registrados | 0 | None |
| Localizar preços e documentação oficiais | ScrapingDog | `/google` e `/scrape` | Páginas primárias de GCP, Cloudflare e APIs localizadas | 23 | None |
| Preservar fontes primárias | ScrapingDog | `/scrape?dynamic=false` | 16 de 17 páginas preservadas em `research/sources/cloud-cost/` | 16 | None |
| Verificar preço público da Twilio | ScrapingDog | `/google`, depois `/scrape` | Busca limitada sem resultado orgânico e captura estática retornou HTTP 400 | 0 | A captura pediu Stealth Mode; foi usada a página oficial localizada pela busca nativa como último recurso |

## Claim ledger

| Claim | Source | Accessed | Snapshot | Primary | Direct | Current | Independent | Verdict |
|---|---|---|---|---|---|---|---|---|
| Workers Paid custa no mínimo US$ 5 por conta e inclui 10 milhões de requisições e 30 milhões de ms de CPU por mês | [Cloudflare Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/) | 2026-08-28 | `research/sources/cloud-cost/cloudflare-workers-pricing/page.md` | yes | yes | yes | unknown | accepted |
| Containers faz parte do Workers Paid e inclui 25 GiB-h de memória, 375 vCPU-min e 200 GB-h de disco | [Cloudflare Containers pricing](https://developers.cloudflare.com/containers/pricing/) | 2026-08-28 | `research/sources/cloud-cost/cloudflare-containers-pricing/page.md` | yes | yes | yes | unknown | accepted |
| Containers não tem autoscaling stateless embutido, usa disco efêmero e não garante duração de instância | [Cloudflare Containers FAQ](https://developers.cloudflare.com/containers/faq/) | 2026-08-28 | `research/sources/cloud-cost/cloudflare-containers-faq/page.md` | yes | yes | yes | unknown | accepted |
| D1 no plano pago inclui 25 bilhões de linhas lidas, 50 milhões de linhas escritas e 5 GB por mês | [Cloudflare D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/) | 2026-08-28 | `research/sources/cloud-cost/cloudflare-d1-pricing/page.md` | yes | yes | yes | unknown | accepted |
| Hyperdrive conecta um banco PostgreSQL existente, mas não hospeda nem substitui o banco | [Cloudflare Hyperdrive](https://developers.cloudflare.com/hyperdrive/) | 2026-08-28 | `research/sources/cloud-cost/cloudflare-hyperdrive/page.md` | yes | yes | yes | unknown | accepted |
| Cloud Run oferece cota gratuita mensal e cobra por CPU, memória e requisições após a cota | [Google Cloud Run pricing](https://cloud.google.com/run/pricing) | 2026-08-28 | `research/sources/cloud-cost/gcp-cloud-run-pricing/page.md` | yes | yes | yes | unknown | accepted |
| Cloud SQL `db-f1-micro` custa US$ 0,0105/h em `us-central1`, sem SLA | [Google Cloud SQL pricing](https://cloud.google.com/sql/pricing) | 2026-08-28 | `research/sources/cloud-cost/gcp-cloud-sql-pricing/page.md` | yes | yes | yes | unknown | accepted |
| O disco mínimo do Cloud SQL é 10 GB | [Cloud SQL Admin API](https://docs.cloud.google.com/sql/docs/postgres/admin-api/rest/v1/instances) | 2026-08-28 | Search result only | yes | yes | yes | unknown | limited |
| O câmbio oficial mais recente disponível é R$ 5,1642 por US$ em 27/08/2026 | [Banco Central do Brasil, série 1](https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/10?formato=json) | 2026-08-28 | `research/sources/cloud-cost/bcb-usd-brl/page.md` | yes | yes | yes | unknown | volatile |
| DeepSeek V4 Pro cobra entre US$ 0,66 e US$ 1,32 por milhão de tokens de entrada sem cache e entre US$ 1,98 e US$ 3,96 por milhão de tokens de saída | [DeepSeek API pricing](https://api-docs.deepseek.com/quick_start/pricing) | 2026-08-28 | `research/sources/cloud-cost/deepseek-pricing/page.md` | yes | yes | yes | unknown | volatile |
| `text-embedding-3-small` custa US$ 0,02 por milhão de tokens | [OpenAI model page](https://developers.openai.com/api/docs/models/text-embedding-3-small) | 2026-08-28 | `research/sources/cloud-cost/openai-embedding-pricing/page.md` | yes | yes | yes | unknown | volatile |
| A Twilio cobra US$ 0,005 por mensagem do WhatsApp, além da tarifa de template da Meta | [Twilio WhatsApp pricing](https://www.twilio.com/en-us/whatsapp/pricing?locale=en) | 2026-08-28 | Snapshot failed | yes | yes | yes | unknown | volatile |

## Findings

### Recomendação

Use GCP para esta entrega. Implante frontend e API no Cloud Run, PostgreSQL com `pgvector` no Cloud SQL, arquivos de replay no Cloud Storage e imagens no Artifact Registry. Limite o backend a uma instância porque o registro de câmeras e os workers de visão vivem no processo.

Mantenha a Cloudflare como camada opcional de DNS, domínio e objetos. Não migre o banco para D1 antes da entrega. O código atual usa SQLAlchemy, PostgreSQL, migrações e `pgvector`; trocar por SQLite/D1 e outro mecanismo vetorial seria uma reescrita material.

Cloudflare Containers consegue executar o container Python. Ainda assim, a plataforma não oferece autoscaling stateless embutido, usa disco efêmero e pode encerrar uma instância por eventos da plataforma. Essas propriedades aumentam o risco de um worker contínuo de câmera. A economia também é incompleta, pois Hyperdrive ainda exige um PostgreSQL externo.

### Custo mensal de referência

Premissas: cinco integrantes, `us-central1`, 730 horas, Cloud SQL `db-f1-micro`, SSD mínimo de 10 GB, 1 GB de backup usado, Cloud Run dentro da cota gratuita e câmbio de R$ 5,1642 por US$. Fontes: [Cloud SQL](https://cloud.google.com/sql/pricing) e [Banco Central](https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/10?formato=json), accessed 2026-08-28.

| Item | Fórmula | Estimativa mensal |
|---|---:|---:|
| Cloud SQL, processamento | US$ 0,0105 × 730 h | US$ 7,665. [Cloud SQL](https://cloud.google.com/sql/pricing), accessed 2026-08-28 |
| Cloud SQL, SSD | US$ 0,000232877 × 10 GiB × 730 h | US$ 1,700. [Cloud SQL](https://cloud.google.com/sql/pricing), accessed 2026-08-28 |
| Cloud SQL, backup usado | US$ 0,000109589 × 1 GiB × 730 h | US$ 0,080. [Cloud SQL](https://cloud.google.com/sql/pricing), accessed 2026-08-28 |
| Cloud Run | dentro da cota gratuita, se disponível na conta de faturamento | US$ 0,00. [Cloud Run](https://cloud.google.com/run/pricing), accessed 2026-08-28 |
| Cloud Storage e Artifact Registry | vídeo pequeno e imagens abaixo das franquias ou com custo subcentavo | aproximadamente US$ 0,00. [Artifact Registry](https://cloud.google.com/artifact-registry/pricing), accessed 2026-08-28 |
| Número Twilio | valor informado por Murilo, comprovante pendente | US$ 4,60, não corroborado pela [tabela pública da Twilio](https://www.twilio.com/en-us/whatsapp/pricing?locale=en), accessed 2026-08-28 |
| Total recorrente de referência | Cloud SQL + Twilio | US$ 14,045, ou R$ 72,53. Fontes acima, [Cloud SQL](https://cloud.google.com/sql/pricing), accessed 2026-08-28 |
| Rateio recorrente | R$ 72,53 ÷ 5 | R$ 14,51 por integrante. [Câmbio do BCB](https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/10?formato=json), accessed 2026-08-28 |

O Cloud SQL é cobrado por segundo enquanto está ativo. Mantê-lo por três dias reduz a parcela de banco para cerca de US$ 0,93. Mantê-lo por cinco dias custa cerca de US$ 1,55. Fonte: [Cloud SQL](https://cloud.google.com/sql/pricing), accessed 2026-08-28. O número da Twilio continua mensal.

### Acerto entre integrantes

- Gasto histórico informado: R$ 70,00. Evidência financeira ainda não anexada e valor exato não corroborado pela [tabela pública da Twilio](https://www.twilio.com/en-us/whatsapp/pricing?locale=en), accessed 2026-08-28.
- Cota histórica: R$ 14,00 por integrante, derivada do gasto informado acima. [Referência pública da Twilio](https://www.twilio.com/en-us/whatsapp/pricing?locale=en), accessed 2026-08-28.
- Primeiro acerto com um mês de infraestrutura: R$ 14,00 + R$ 14,51 = R$ 28,51 por integrante. [Câmbio do BCB](https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/10?formato=json), accessed 2026-08-28.
- Arrecadação recomendada: R$ 30,00 por integrante. [Câmbio do BCB](https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/10?formato=json), accessed 2026-08-28.
- Saldo de segurança: R$ 7,47 no caixa do projeto se os cinco contabilizarem R$ 30,00. [Câmbio do BCB](https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/10?formato=json), accessed 2026-08-28.

Se apenas os outros quatro transferirem para quem antecipa os pagamentos, cada um envia R$ 30,00. O excedente sobre a cota estimada deve ficar registrado como saldo do projeto. [Câmbio do BCB](https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/10?formato=json), accessed 2026-08-28.

### APIs

Não há mensalidade fixa de IA identificada no código. O custo depende de tokens e áudio. Como cenário de teto para o vídeo, 100 respostas com 10 mil tokens de entrada e mil de saída cada custariam até US$ 1,716 no horário de pico do DeepSeek, ou R$ 8,86 no total. Isso adiciona R$ 1,77 por integrante. Fonte: [DeepSeek](https://api-docs.deepseek.com/quick_start/pricing), accessed 2026-08-28. Embeddings custam US$ 0,02 por milhão de tokens e tendem a ser residuais neste volume. Fonte: [OpenAI](https://developers.openai.com/api/docs/models/text-embedding-3-small), accessed 2026-08-28.

O backend atual integra WhatsApp pela API da Meta, não pela Twilio. Portanto, o número da Twilio é despesa administrativa informada pela equipe, não dependência comprovada do runtime. A planilha deve manter essa classificação até a equipe anexar a fatura e confirmar o uso.

### Cloudflare como alternativa futura

O Workers Paid já existente pode absorver frontend, gateway e R2 sem novo custo fixo. Uma migração completa exigiria uma destas opções:

1. Cloudflare Container para Python e OpenCV, R2 para evidências e PostgreSQL externo via Hyperdrive.
2. Reescrita do banco para D1 e da busca vetorial para Vectorize, além da adaptação do ORM e das migrações.

A primeira opção mantém um banco externo e não elimina o principal custo fixo. A segunda reduz o custo recorrente, mas cria migração incompatível com o prazo e com a arquitetura validada. Reavalie após a entrega acadêmica.

## Disagreements

- A documentação antiga usa R$6,00 por US$ como premissa interna. Esta análise usa o último valor oficial disponível do Banco Central, R$5,1642 em 27/08/2026. Preserve R$6,00 apenas como margem conservadora no plano financeiro acadêmico.
- A despesa Twilio de US$4,60 difere do preço público de alguns números brasileiros e não aparece na integração do repositório. O valor informado pela equipe prevalece no caixa, mas precisa de fatura.

## Open questions

- Qual projeto GCP ficará ativo após a troca de conta no `gcloud`?
- O Workers Paid da Cloudflare será tratado como custo pessoal já contratado ou como despesa compartilhada do grupo?
- O grupo quer apagar o Cloud SQL após gravar o vídeo ou manter a demonstração disponível até a correção?

## Council review

- Status: not run
- Reason: as fontes primárias concordam. A decisão depende mais da compatibilidade observada no repositório do que de uma disputa factual.
- Accepted findings: GCP para a entrega, Cloudflare como camada opcional e migração completa adiada.
- Rejected findings: D1 como substituição direta de PostgreSQL com `pgvector`.

## Sources consulted

- [Google Cloud Run pricing](https://cloud.google.com/run/pricing), accessed 2026-08-28.
- [Google Cloud SQL pricing](https://cloud.google.com/sql/pricing), accessed 2026-08-28.
- [Cloud SQL Admin API](https://docs.cloud.google.com/sql/docs/postgres/admin-api/rest/v1/instances), accessed 2026-08-28.
- [Cloud SQL extensions](https://docs.cloud.google.com/sql/docs/postgres/extensions), accessed 2026-08-28.
- [Cloud Run Cloud Storage mounts](https://docs.cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts), accessed 2026-08-28.
- [Artifact Registry pricing](https://cloud.google.com/artifact-registry/pricing), accessed 2026-08-28.
- [Cloudflare Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/), accessed 2026-08-28.
- [Cloudflare Containers pricing](https://developers.cloudflare.com/containers/pricing/), accessed 2026-08-28.
- [Cloudflare Containers FAQ](https://developers.cloudflare.com/containers/faq/), accessed 2026-08-28.
- [Cloudflare D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/), accessed 2026-08-28.
- [Cloudflare R2 pricing](https://developers.cloudflare.com/r2/pricing/), accessed 2026-08-28.
- [Cloudflare Hyperdrive](https://developers.cloudflare.com/hyperdrive/), accessed 2026-08-28.
- [DeepSeek API pricing](https://api-docs.deepseek.com/quick_start/pricing), accessed 2026-08-28.
- [OpenAI `text-embedding-3-small`](https://developers.openai.com/api/docs/models/text-embedding-3-small), accessed 2026-08-28.
- [Twilio WhatsApp pricing](https://www.twilio.com/en-us/whatsapp/pricing?locale=en), accessed 2026-08-28.
- [Banco Central do Brasil, série 1](https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/10?formato=json), accessed 2026-08-28.

## Trial by fire

- Primary-source claims: todos os preços e limites publicados usam documentação oficial.
- Secondary-only claims: none.
- Volatile claims: preços, câmbio, cotas e disponibilidade regional devem ser reconfirmados no deploy.
- Repository evidence: a conclusão sobre migração usa as dependências, configurações e integrações presentes no checkout de 28/08/2026.
