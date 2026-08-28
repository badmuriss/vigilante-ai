# PARTE 5 — INFRAESTRUTURA TECNOLÓGICA

## 5.1 Comparativo Geral de Provedores Cloud

### Contexto da Avaliação

O Vigilante.AI é uma plataforma SaaS que recebe streams de vídeo RTSP de câmeras IP já existentes no canteiro de obras, processa com YOLOv8 em instâncias GPU na nuvem e entrega resultados via dashboard web. Os critérios de avaliação refletem diretamente essa arquitetura:

1. **Ingestão de vídeo** — serviço gerenciado para receber streams RTSP de câmeras IP
2. **GPU para inferência** — instâncias com NVIDIA T4 disponíveis na região Brasil
3. **Serviços de aplicação** — containers, banco de dados, armazenamento, autenticação, CDN
4. **Custo e programas para startups**
5. **Maturidade no Brasil** — região São Paulo, estabilidade de serviços, ecossistema

### Regiões no Brasil

| Critério | AWS | Azure | GCP |
|----------|-----|-------|-----|
| **Região** | sa-east-1 (São Paulo) | Brazil South (São Paulo) | southamerica-east1 (São Paulo) |
| **Desde** | Dezembro de 2011 | Junho de 2014 | Setembro de 2017 |
| **Zonas de disponibilidade** | 3 | 3 | 3 |
| **GPU confirmada (T4)** | g4dn — disponível | NC T4 v3 — disponibilidade instável | T4 — disponível |
| **Maturidade** | Alta (14 anos) | Média-Alta (11 anos) | Média (8 anos) |

A AWS é a mais antiga no Brasil, com o maior catálogo de serviços disponíveis na região. Azure sofre com disponibilidade instável de GPUs em brazilsouth — diversos relatos de incapacidade de provisionar VMs NC T4 v3.

### Ingestão de Vídeo (Critério Decisivo)

Este é o ponto mais crítico da comparação: o Vigilante.AI precisa de um serviço que receba streams RTSP de câmeras IP e os disponibilize para processamento GPU.

| Critério | AWS | Azure | GCP |
|----------|-----|-------|-----|
| **Serviço gerenciado para RTSP** | **Kinesis Video Streams (KVS)** — ativo, maduro | **Nenhum** — Azure Media Services foi descontinuado em junho de 2024 | **Nenhum** — não existe equivalente nativo |
| **Como recebe RTSP** | KVS RTSP Agent (container Docker) ou GStreamer plugin | Precisaria montar infra própria (MediaMTX/GStreamer em VMs) | Precisaria montar infra própria |
| **Funcionalidades** | Ingestão, armazenamento, reprodução, WebRTC, retenção configurável | N/A | Live Stream API existe, mas é para broadcasting (HLS/DASH), não para câmeras IP |
| **SDKs** | C, Java, Python | N/A | N/A |

A AWS é o único provedor com solução gerenciada para ingestão de streams RTSP. Nos outros dois, seria necessário construir e manter essa camada manualmente — complexidade significativa e ponto de falha adicional.

O Azure perdeu seu serviço de vídeo (Azure Media Services + Azure Video Analyzer) em junho de 2024, sem substituto direto. A Microsoft passou a recomendar soluções de parceiros terceiros (Harmonic, MediaKind) via Marketplace.

### Instâncias GPU para Inferência YOLOv8

Todas as três plataformas oferecem NVIDIA T4 na região Brasil. A T4 é ideal para inferência YOLOv8 — 16 GB de memória GPU, suporte a FP16 e INT8.

#### AWS — sa-east-1

| Instância | GPU | vCPUs | RAM | On-Demand (USD/h) | Spot (USD/h) |
|-----------|-----|-------|-----|-------------------|--------------|
| g4dn.xlarge | 1x T4 | 4 | 16 GB | ~$0,71 | ~$0,21–0,28 |
| g4dn.2xlarge | 1x T4 | 8 | 32 GB | ~$1,02 | ~$0,31–0,40 |
| g4dn.12xlarge | 4x T4 | 48 | 192 GB | ~$5,28 | ~$1,58–2,10 |

#### Azure — brazilsouth

| Instância | GPU | vCPUs | RAM | On-Demand (USD/h) | Spot (USD/h) |
|-----------|-----|-------|-----|-------------------|--------------|
| NC4as_T4_v3 | 1x T4 | 4 | 28 GB | ~$0,59 | ~$0,12–0,18 |
| NC8as_T4_v3 | 1x T4 | 8 | 56 GB | ~$0,85 | ~$0,17–0,26 |
| NC16as_T4_v3 | 1x T4 | 16 | 110 GB | ~$1,56 | ~$0,31–0,47 |

**Risco**: disponibilidade de GPU em brazilsouth é notoriamente instável. Spot GPU no Azure Brasil é ainda mais raro.

#### GCP — southamerica-east1

| Configuração | GPU | vCPUs | RAM | On-Demand (USD/h) | Spot (USD/h) |
|--------------|-----|-------|-----|-------------------|--------------|
| n1-standard-4 + 1x T4 | 1x T4 | 4 | 15 GB | ~$0,61 | ~$0,18–0,22 |
| n1-standard-8 + 1x T4 | 1x T4 | 8 | 30 GB | ~$0,84 | ~$0,25–0,30 |

No GCP, a GPU é adicionada como acelerador a uma VM customizável.

#### Comparativo de Custo GPU

| Provedor | On-Demand (1x T4, 4 vCPUs) | Spot/Preemptível | Economia Spot |
|----------|---------------------------|------------------|---------------|
| **AWS** | ~$0,71/h | ~$0,25/h | ~65% |
| **Azure** | ~$0,59/h | ~$0,15/h | ~75% (quando disponível) |
| **GCP** | ~$0,61/h | ~$0,20/h | ~67% |

Azure é nominalmente mais barato, mas o risco de indisponibilidade anula essa vantagem. AWS e GCP são confiáveis.

### Serviços de Aplicação

#### Containers (API + Dashboard)

| Critério | AWS | Azure | GCP |
|----------|-----|-------|-----|
| **Serverless containers** | ECS Fargate | Azure Container Apps | Cloud Run |
| **Kubernetes** | EKS | AKS (control plane grátis) | GKE |
| **Simplicidade** | Média | Média | Cloud Run é o mais simples |
| **Suporta GPU?** | Não (Fargate). GPU via ECS em EC2 | Não (ACA). GPU via AKS | Não (Cloud Run). GPU via GKE/GCE |

Nenhum serviço serverless de containers suporta GPU. A inferência GPU roda em instâncias EC2/VMs dedicadas.

#### Armazenamento de Objetos (Frames de Alertas)

| Critério | AWS S3 | Azure Blob | GCP Cloud Storage |
|----------|--------|------------|-------------------|
| Standard (USD/GB/mês) | ~$0,026 | ~$0,023 | ~$0,023 |
| Acesso infrequente | ~$0,018 | ~$0,013 (Cool) | ~$0,016 (Nearline) |
| Arquivo | ~$0,005 (Glacier) | ~$0,002 (Archive) | ~$0,004 (Coldline) |
| Egress (USD/GB) | ~$0,09 | ~$0,08 | ~$0,08 |

Diferença marginal. Egress (tráfego de saída para servir imagens no dashboard) é o custo mais relevante.

#### PostgreSQL Gerenciado

| Critério | AWS RDS | Azure DB for PostgreSQL | GCP Cloud SQL |
|----------|---------|------------------------|---------------|
| Menor instância (USD/mês) | db.t3.micro: ~$18 | B1ms (1vCPU, 2GB): ~$25 | db-f1-micro: ~$10 |
| Produção (2vCPU, 8GB) | db.t3.medium: ~$70 | D2s_v3: ~$95 | db-custom-2-8192: ~$75 |
| Backups automáticos | 35 dias | 35 dias | 7 dias (grátis) |
| Free tier | 12 meses (db.t3.micro) | Não | Não |

AWS RDS tem free tier de 12 meses. GCP Cloud SQL é o mais barato na menor instância.

#### Autenticação

| Critério | AWS Cognito | Azure AD B2C | Firebase Auth (GCP) |
|----------|-------------|--------------|---------------------|
| Free tier | 50.000 MAUs | 50.000 MAUs | Ilimitado (auth básico) |
| Social login | Sim | Sim | Sim |
| MFA | Sim | Sim | Sim |
| Complexidade de setup | Média-Alta | Alta | Mais simples |

#### CDN

| Critério | CloudFront | Azure CDN | Cloud CDN |
|----------|-----------|-----------|-----------|
| PoPs no Brasil | São Paulo, Rio | São Paulo | São Paulo |
| Preço (USD/GB, SA) | ~$0,085 | ~$0,081 | ~$0,08 |
| WAF integrado | AWS WAF (separado) | Azure WAF (Front Door) | Cloud Armor |

### Programas para Startups

| Critério | AWS Activate | Microsoft Founders Hub | Google for Startups |
|----------|-------------|----------------------|---------------------|
| Sem aceleradora | Até US$ 1.000 | Até US$ 1.000 | Até US$ 2.000 |
| Com aceleradora/VC | Até US$ 25.000–100.000 | Até US$ 25.000–150.000 | Até US$ 100.000–200.000 |
| Validade dos créditos | 2 anos | 1 ano | 1–2 anos |
| Extras | Business Support, treinamento | Créditos OpenAI, VS Enterprise, M365 | Google Workspace, Firebase, Maps |

### Descontinuações de Serviços (Risco)

| Serviço descontinuado | Provedor | Data | Impacto para o Vigilante.AI |
|----------------------|----------|------|-----------------------------|
| Azure Media Services + Video Analyzer | Azure | Junho 2024 | **Crítico** — sem substituto para ingestão RTSP |
| Cloud IoT Core | GCP | Agosto 2023 | Baixo para nosso caso de uso |
| (nenhum serviço relevante) | AWS | — | Portfólio estável |

### Ecossistema no Brasil

| Critério | AWS | Azure | GCP |
|----------|-----|-------|-----|
| Market share estimado | ~40–45% (líder) | ~25–30% | ~10–15% |
| Parceiros/consultorias | Maior ecossistema | Forte via canal Microsoft | Crescente, menor |
| Documentação em PT-BR | Parcial (~60–70%) | Mais completa (tradução histórica) | Limitada |
| Suporte em português | Planos Business/Enterprise | Todos os planos pagos | Disponível, equipe menor |

### Conclusão do Comparativo

**Provedor escolhido: Amazon Web Services (AWS)**

O Kinesis Video Streams é o fator decisivo: é o único serviço gerenciado entre os três provedores que resolve nativamente a ingestão de streams RTSP de câmeras IP. Somado à estabilidade do portfólio (nenhum serviço relevante descontinuado), disponibilidade confiável de GPU (g4dn) em sa-east-1, maior ecossistema no Brasil e free tier com RDS PostgreSQL por 12 meses, a AWS é a escolha mais sólida para o Vigilante.AI.

O GCP seria uma alternativa viável pelo custo-benefício e programas de startup generosos, mas a ausência de serviço gerenciado para RTSP exigiria construir e manter essa camada manualmente. O Azure é descartado pela descontinuação do Media Services e instabilidade de GPUs no Brasil.

*Nota: todos os preços são aproximados e referem-se às regiões Brasil de cada provedor. Valores devem ser verificados nas calculadoras oficiais no momento da implementação.*

---

## 5.2 Arquitetura do Sistema

### Modelo Arquitetural: SaaS Cloud-First

A arquitetura do Vigilante.AI é inteiramente baseada em cloud. O cliente não instala nenhum software ou hardware proprietário — apenas aponta suas câmeras IP existentes para o serviço. Isso elimina barreiras de entrada e permite que uma construtora de 30 funcionários comece a usar o sistema no mesmo dia.

### Fluxo de Dados

```
Canteiro de Obras                         AWS Cloud (sa-east-1)

┌────────────┐                   ┌─────────────────────────────────────────┐
│ Câmera IP  │──── RTSP ────────▶│  Kinesis Video Streams                 │
│ (existente)│   (via internet)  │  (ingestão e buffer de streams)        │
└────────────┘                   └──────────────┬──────────────────────────┘
                                                │
┌────────────┐                   ┌──────────────▼──────────────────────────┐
│ Câmera IP  │──── RTSP ────────▶│  EC2 GPU (G4dn — NVIDIA T4)            │
│ (existente)│                   │  FastAPI + YOLOv8 Inference             │
└────────────┘                   │  - Decodifica frames do stream          │
                                 │  - Roda detecção de EPIs               │
┌────────────┐                   │  - Gera alertas em tempo real          │
│ Câmera IP  │──── RTSP ────────▶│  - Aplica blur facial automático       │
│ (existente)│                   └──────┬──────────┬───────────────────────┘
└────────────┘                          │          │
                                 ┌──────▼───┐ ┌───▼──────────────────────┐
                                 │   RDS    │ │  S3 (frames de alertas)  │
                                 │PostgreSQL│ │  com blur facial         │
                                 └──────┬───┘ └───┬──────────────────────┘
                                        │         │
                                 ┌──────▼─────────▼──────────────────────┐
                                 │  ECS Fargate (API + Dashboard)        │
                                 │  FastAPI (dados) + Next.js (frontend) │
                                 └──────────────┬────────────────────────┘
                                                │
                                 ┌──────────────▼────────────────────────┐
                                 │  CloudFront (CDN) + Cognito (Auth)    │
                                 └──────────────┬────────────────────────┘
                                                │ HTTPS
                                 ┌──────────────▼────────────────────────┐
                                 │  Browser do supervisor / técnico      │
                                 │  (qualquer dispositivo)               │
                                 └───────────────────────────────────────┘
```

### Por que Cloud e não Processamento Local?

| Fator | Processamento na Cloud | Processamento Local (Edge) |
|-------|------------------------|---------------------------|
| **Barreira de entrada** | Zero — cliente já tem câmeras IP | Cliente precisa comprar hardware (R$ 800–3.500 por dispositivo) |
| **Setup** | Cadastrar câmeras IP no painel, pronto | Instalar dispositivo, configurar rede local, manutenção física |
| **Escalabilidade** | Auto-scaling automático conforme demanda | Cada novo canteiro = novo hardware |
| **Atualização do modelo** | Atualização instantânea para todos os clientes | Update remoto por dispositivo, risco de falha |
| **Manutenção** | Zero para o cliente | Cliente responsável por hardware no canteiro |
| **Custo para o cliente** | Apenas mensalidade SaaS | Mensalidade + investimento inicial em hardware |

A escolha cloud-first é estratégica: o produto mais acessível vence no segmento de PMEs. Se o cliente já tem câmeras IP (muito comum em canteiros por questões de segurança patrimonial), o Vigilante.AI adiciona inteligência sem nenhum custo adicional de infraestrutura do lado do cliente.

### Componentes e Serviços AWS

| Componente | Serviço AWS | Justificativa |
|------------|-------------|---------------|
| **Ingestão de vídeo** | Kinesis Video Streams | Recebe streams RTSP de câmeras IP, buffer e disponibiliza para processamento. Escala automaticamente com número de câmeras |
| **Inferência GPU** | EC2 G4dn (NVIDIA T4) | Processa múltiplos streams simultâneos com YOLOv8. Spot Instances para economia de até 65% |
| **API Backend** | ECS Fargate | Containers serverless para a API de dados (alertas, stats, config). Pay-per-use |
| **Frontend** | S3 + CloudFront | Next.js em modo estático, CDN com edge locations na América do Sul |
| **Banco de dados** | RDS PostgreSQL | Dados relacionais: cliente → canteiros → câmeras → alertas → EPIs. Free tier 12 meses |
| **Armazenamento de mídia** | S3 | Frames de alertas (com blur facial). Lifecycle policies para redução de custo ao longo do tempo |
| **Autenticação** | Cognito | Multi-tenancy, OAuth2, MFA. 50.000 MAUs gratuitos |
| **CDN** | CloudFront | Edge locations na América do Sul, reduz latência do dashboard para usuários em todo o Brasil |
| **Monitoramento** | CloudWatch | Logs centralizados, métricas de inferência, alarmes de disponibilidade |
| **Segurança** | WAF + GuardDuty | Proteção contra ataques web e detecção de ameaças |

### Banco de Dados: PostgreSQL (RDS)

A escolha do PostgreSQL como banco de dados principal é justificada pela natureza relacional dos dados do sistema:

- **Relacionamentos claros**: cliente → canteiro de obras → câmeras → alertas → EPIs detectados
- **Consultas complexas**: relatórios de compliance por período, comparativos entre canteiros, evolução temporal de violações
- **Suporte nativo a JSON**: metadados flexíveis de detecção (bounding boxes, nível de confiança, classes detectadas)
- **PostGIS**: geolocalização de canteiros de obras para visualização em mapa
- **Free tier**: instância db.t3.micro gratuita por 12 meses, suficiente para o MVP

Para escala futura (acima de 500 clientes), a ingestão de alertas em tempo real pode ser migrada para DynamoDB (25 GB gratuitos permanentemente, latência single-digit milliseconds), mantendo PostgreSQL para dados de configuração e relatórios.

### Modelo Arquitetural: Monolito Modular com Evolução Gradual

A decisão é iniciar com monolito modular e extrair microsserviços apenas quando a escala justificar:

| Fase | Arquitetura | Critério de Transição |
|------|-------------|----------------------|
| **MVP** (até 50 clientes) | Monolito FastAPI com módulos bem separados | — |
| **Crescimento** (50–500) | Extração do Video Processing Service (GPU) e Notification Service | Quando inferência GPU precisar escalar independente da API |
| **Escala** (500+) | Microsserviços seletivos via Strangler Fig Pattern | Quando time ultrapassar 15 devs |

**Por que não microsserviços desde o início:**

- **Equipe pequena**: com menos de 5 desenvolvedores, a complexidade operacional de gerenciar Kubernetes, service mesh, distributed tracing e múltiplos bancos de dados é contraproducente
- **Custo**: microsserviços prematuros podem custar 3-5x mais em infraestrutura (múltiplos containers, load balancers, bancos separados)
- **Latência**: em um sistema de monitoramento em tempo real, chamadas de rede entre serviços adicionam latência crítica
- **Debugging**: um bug que seria um stack trace simples no monolito vira investigação distribuída em vários serviços

### Estimativa de Custos por Fase

| Fase | Clientes | Câmeras | Custo Mensal Estimado (USD) |
|------|----------|---------|---------------------------|
| **MVP** | 1–5 | 5–20 | ~US$ 150–300 (1 G4dn Spot + Fargate + RDS free tier) |
| **Crescimento** | 50 | 200 | ~US$ 1.500–2.500 (múltiplas G4dn + RDS Multi-AZ) |
| **Escala** | 500 | 2.000 | ~US$ 8.000–12.000 (Auto Scaling Group GPU + infra completa) |

Os custos de GPU cloud são absorvidos pela mensalidade SaaS e eliminam qualquer custo de hardware para o cliente.

---

## 5.3 Segurança Cibernética e Conformidade

### LGPD (Lei 13.709/2018)

Como o Vigilante.AI processa vídeo de trabalhadores na cloud, a responsabilidade sobre dados pessoais é centralizada e demanda conformidade rigorosa com a LGPD.

#### Classificação dos Dados Tratados

| Tipo de Dado | Classificação LGPD | Tratamento |
|-------------|-------------------|------------|
| Stream de vídeo (em processamento) | Dado pessoal | Processado em memória na instância GPU, nunca armazenado em estado bruto |
| Frames de alerta (armazenados) | Dado pessoal anonimizado | Blur facial automático aplicado antes de persistir no S3 |
| Metadados de alertas (horário, local, EPI ausente) | Dado pessoal (quando associável) | Criptografado em repouso (AES-256) |
| Relatórios de compliance agregados | Dado não pessoal | Dados agregados sem identificação individual |

#### Base Legal para Tratamento (Art. 7 e Art. 11)

A base legal primária é o **cumprimento de obrigação legal/regulatória** (Art. 11, II, a). A NR-6 (Norma Regulamentadora 6) obriga o empregador a fornecer, fiscalizar e registrar o uso de EPIs. O Vigilante.AI é uma ferramenta que operacionaliza essa obrigação legal, o que constitui base legítima para o tratamento de dados pessoais sem necessidade de consentimento individual do trabalhador.

O sistema não realiza reconhecimento facial — detecta presença/ausência de EPI, não identifica quem é a pessoa. Isso evita classificação como tratamento de dado biométrico para fins de identificação.

#### Estratégia de Anonimização

1. **Stream processado apenas em memória**: o vídeo é decodificado frame a frame na instância GPU, analisado pelo YOLOv8, e descartado imediatamente após a inferência. Nenhum vídeo bruto é persistido.
2. **Blur facial automático**: antes de armazenar qualquer frame de alerta no S3, faces detectadas são automaticamente pixelizadas. O dado armazenado é, portanto, anonimizado.
3. **Sem reconhecimento facial**: o modelo detecta classes de EPIs (capacete, óculos, máscara), não identidades. Nenhum dado biométrico para identificação é gerado ou armazenado.
4. **Retenção mínima**: frames anonimizados seguem política de lifecycle automática no S3.

### Criptografia

| Camada | Protocolo | Implementação |
|--------|-----------|---------------|
| **Câmera IP → Cloud** | RTSP over TLS (RTSPS) ou VPN site-to-site | Kinesis Video Streams suporta ingestão TLS nativa |
| **Browser → API** | HTTPS / TLS 1.2+ | Certificado ACM gratuito via CloudFront/ALB |
| **API → Banco de dados** | TLS 1.2+ | RDS com `require_ssl=true` |
| **Dados em repouso (S3)** | AES-256 (SSE-KMS) | Criptografia padrão habilitada na criação do bucket |
| **Dados em repouso (RDS)** | AES-256 via KMS | Inclui backups e snapshots automaticamente |

### Controle de Acesso

**Camada de serviços (IAM Roles — princípio do menor privilégio):**

- `VideoProcessingRole`: acesso ao Kinesis Video Streams (leitura de streams), S3 PutObject (somente bucket de alertas)
- `APIServiceRole`: S3 Read, RDS Access, Cognito Admin
- `DashboardRole`: S3 GetObject, API Read-only

**Camada de usuários finais (Cognito Groups):**

- `admin`: gerencia clientes, canteiros, câmeras e configurações globais
- `supervisor`: visualiza alertas e relatórios de todas as câmeras do seu canteiro
- `viewer`: acesso somente leitura ao dashboard

### Política de Retenção de Dados

| Tipo de Dado | Retenção | Justificativa |
|-------------|----------|---------------|
| Stream de vídeo bruto | 0 — processado em memória e descartado | Minimização de dados (LGPD Art. 6) |
| Frames de alertas (com blur facial) | 90 dias em S3 Standard → 1 ano em Glacier | Compliance e auditorias NR-6 |
| Metadados de alertas | 2 anos | Relatórios históricos de conformidade |
| Logs de sistema | 1 ano | Auditoria via CloudTrail e troubleshooting |

### Medidas Complementares de Segurança

- **AWS WAF**: proteção da API contra SQL injection, XSS e ataques DDoS
- **AWS GuardDuty**: detecção de acessos anômalos e credenciais comprometidas
- **AWS CloudTrail**: log imutável de todas as chamadas de API para auditoria LGPD
- **AWS Config**: monitoramento contínuo de conformidade (detecta buckets S3 sem criptografia, security groups abertos)
- **AWS Secrets Manager**: rotação automática de credenciais de banco de dados
- **Sinalização física**: placas informativas obrigatórias nos canteiros monitorados, conforme exigência da LGPD para transparência com os titulares dos dados

---

# PARTE 6 — CONCEITO DA SOLUÇÃO

## 6.1 O Problema

### Descrição Detalhada

O Brasil registra mais de **600 mil acidentes de trabalho por ano**, dos quais o setor de **construção civil responde pela maioria dos óbitos**. A causa predominante é a **não utilização ou uso incorreto de Equipamentos de Proteção Individual (EPIs)** — capacetes, óculos de proteção, máscaras, luvas e calçados de segurança.

A legislação brasileira é clara: a **NR-6** (Norma Regulamentadora 6) determina que toda empresa com funcionários CLT deve fornecer, fiscalizar e registrar o uso de EPIs. A **NR-5** (CIPA) torna obrigatória uma estrutura formal de prevenção de acidentes para empresas com 20 ou mais funcionários. A **NR-18** impõe requisitos específicos ao setor de construção civil. O descumprimento resulta em **autos de infração, embargos de obra e multas administrativas** aplicadas pelo Ministério do Trabalho.

### Situações Reais que Ilustram o Problema

**Situação 1 — A fiscalização manual é ineficaz.**

Em um canteiro de obras com 80 trabalhadores distribuídos em múltiplos andares, o técnico de segurança realiza rondas periódicas — tipicamente 2 a 3 vezes por turno. Entre uma ronda e outra, trabalhadores removem capacetes por desconforto térmico, retiram óculos de proteção ao operar esmerilhadeiras, ou dispensam máscaras em ambientes com poeira de cimento. O técnico flagra uma fração mínima das violações. O registro é feito em pranchetas de papel, sem rastreabilidade temporal e sem possibilidade de auditoria posterior.

**Situação 2 — O custo humano dos acidentes.**

Um trabalhador em uma obra de médio porte remove os óculos de proteção por alguns minutos enquanto faz cortes com serra circular. Um fragmento metálico atinge o olho. A lesão poderia ter sido evitada se a ausência do EPI fosse detectada em tempo real. O empregador é responsabilizado civil e criminalmente, a obra é embargada, e o trabalhador sofre sequelas permanentes. Além do drama humano, o custo para a empresa inclui indenizações, paralisação da obra e danos reputacionais.

**Situação 3 — A assimetria de soluções no mercado.**

Uma construtora de médio porte em Belo Horizonte, com 50 funcionários, busca uma solução tecnológica de monitoramento de EPIs. As opções disponíveis — Protex AI (EUA), Voxel AI (EUA), Intenseye (Europa) — exigem contratos enterprise em dólar, infraestrutura CCTV dedicada e integração que leva semanas a meses. O custo é incompatível com o orçamento da empresa. Ela continua com fiscalização manual e pranchetas.

### Dimensão do Problema

- O setor de construção civil brasileiro conta com **mais de 400 mil empresas ativas**, das quais **94,8% possuem menos de 50 funcionários**
- A fiscalização do Ministério do Trabalho tem sido intensificada com **campanhas crescentes** focadas no setor
- **Nenhuma solução existente** de safety computer vision atua no Brasil ou é acessível para PMEs brasileiras
- O mercado de workplace safety tech na América Latina está em **estágio inicial**, sem soluções locais consolidadas
- O custo de acidentes de trabalho ultrapassa **R$ 13 bilhões anuais** para a previdência social brasileira

---

## 6.2 A Solução: Vigilante.AI

### Visão Geral

O Vigilante.AI é uma **plataforma SaaS de monitoramento de segurança em tempo real** que utiliza visão computacional para detectar automaticamente a ausência de EPIs em ambientes de trabalho. O cliente conecta suas câmeras IP já existentes ao serviço cloud — **sem instalar hardware, software ou dependências locais**. Todo o processamento inteligente ocorre na nuvem da AWS.

### Como Funciona na Prática

1. **O cliente cadastra suas câmeras IP** no painel web do Vigilante.AI (informa a URL RTSP de cada câmera)
2. **O serviço cloud recebe os streams** de vídeo via Kinesis Video Streams (AWS)
3. **Instâncias GPU (NVIDIA T4) processam cada frame** com o modelo YOLOv8, detectando presença ou ausência de EPIs em tempo real
4. **Quando uma violação é detectada** (trabalhador sem capacete, sem óculos, etc.), o sistema gera um alerta instantâneo contendo: timestamp, tipo de EPI ausente, nível de confiança da detecção e captura de tela do momento da infração (com blur facial automático)
5. **Supervisores e técnicos de segurança acompanham tudo** pelo dashboard web, acessível de qualquer dispositivo com internet — computador, tablet ou celular

**O que o cliente precisa ter:** câmeras IP (muito comuns em canteiros por segurança patrimonial) e conexão de internet. Nada mais.

### Stack Tecnológico

#### Backend (Python / FastAPI)

- Servidor assíncrono FastAPI com Uvicorn, rodando em instâncias GPU na AWS
- Modelo YOLOv8 treinado especificamente para detectar **6 classes de EPIs**: capacete, óculos de proteção, máscara, luvas, colete e calçado de segurança
- Detecção facial via Haar Cascade (OpenCV) como proxy de presença humana — mais leve que detectar a pessoa inteira por YOLO
- Blur facial automático em frames de alerta para conformidade com LGPD
- Sistema de alertas com cooldown inteligente (10 segundos) para evitar spam de notificações repetidas
- Ingestão de streams RTSP via AWS Kinesis Video Streams

#### Frontend (Next.js / TypeScript)

- Dashboard de monitoramento em tempo real com visualização de múltiplas câmeras
- Painel de alertas com detalhes expandíveis e visualização do frame da infração
- Dashboard analítico com gráficos de compliance por período, taxa de violações por minuto e KPIs de sessão (usando biblioteca Recharts)
- Configuração dinâmica de quais EPIs monitorar, ajustável em tempo real via toggles visuais
- Interface completa em português, responsiva para acesso mobile
- Arquitetura multi-tenant: cada cliente vê apenas seus canteiros e câmeras

#### Infraestrutura (AWS)

- Processamento GPU em instâncias EC2 G4dn (NVIDIA T4) na região São Paulo (sa-east-1)
- Ingestão de vídeo via Kinesis Video Streams com buffer e retenção configurável
- Armazenamento de frames de alertas no S3 com lifecycle policies e criptografia AES-256
- Banco de dados PostgreSQL (RDS) para dados relacionais de clientes, câmeras e alertas
- Autenticação multi-tenant via Cognito com suporte a OAuth2 e MFA
- CDN via CloudFront para entrega do dashboard com baixa latência em todo o Brasil
- Proteção via WAF contra ataques web e GuardDuty para detecção de ameaças

### Endpoints da API

| Endpoint | Método | Função |
|----------|--------|--------|
| `/api/status` | GET | Estado do sistema (câmera ativa, modelo carregado, FPS, uptime) |
| `/api/stream/frame` | GET | Frame JPEG atual com anotações de detecção |
| `/api/stream/start` | POST | Inicia captura e processamento de um stream |
| `/api/stream/stop` | POST | Para o monitoramento de um stream |
| `/api/alerts` | GET | Lista de alertas com thumbnails e metadados |
| `/api/alerts` | DELETE | Limpa histórico de alertas |
| `/api/stats` | GET | Estatísticas da sessão (total de violações, taxa de compliance, timeline) |
| `/api/config/epis` | GET/POST | Consulta e configura quais EPIs estão sendo monitorados |

### Diferenciais Competitivos

Conforme a análise de benchmarks realizada na Parte 1 da pesquisa, o Vigilante.AI se diferencia em cinco dimensões estratégicas:

| Dimensão | Concorrentes (Protex AI, Voxel AI, Intenseye) | Vigilante.AI |
|----------|-----------------------------------------------|--------------|
| **Público-alvo** | Grandes corporações e indústrias | PMEs brasileiras (20–200 funcionários) |
| **Modelo de negócio** | Enterprise SaaS com contratos em dólar | SaaS acessível em reais, mensalidade simples sem contrato longo |
| **Infraestrutura do cliente** | CCTV dedicado + edge box proprietário | Câmeras IP existentes, zero hardware adicional |
| **Tempo de implantação** | Semanas a meses de integração | Cadastrar câmeras no painel, operacional no mesmo dia |
| **Presença no Brasil** | Nenhuma presença comercial | Nativo brasileiro, interface em português, suporte local |
| **Processamento** | Cloud proprietário ou edge boxes caros | Cloud AWS em São Paulo (sa-east-1), latência mínima |

### Modelo de Negócio: SaaS Fechado por Assinatura

O Vigilante.AI é uma plataforma de **código proprietário**, monetizada via assinatura mensal:

| Plano | Preço Mensal | Inclui |
|-------|-------------|--------|
| **Starter** | R$ 300/mês | Até 3 câmeras, 1 canteiro, alertas em tempo real, dashboard básico |
| **Pro** | R$ 600/mês | Até 10 câmeras, múltiplos canteiros, relatórios de compliance NR-6, suporte prioritário |
| **Enterprise** | Sob consulta | Câmeras ilimitadas, API de integração, SLA dedicado, treinamento personalizado do modelo |

**Por que código fechado:** o modelo proprietário protege a vantagem competitiva. Em um mercado onde nenhum concorrente atua diretamente no Brasil no segmento de PMEs, abrir o código permitiria que players maiores (ou novos entrantes) replicassem a solução sem custo de desenvolvimento, eliminando a vantagem de primeiro entrante. A propriedade intelectual do modelo treinado, da lógica de detecção e da interface são ativos centrais do negócio.

### Roadmap de Desenvolvimento

O roadmap executivo até a apresentação final está detalhado em
[`docs/roadmap-tcc-outubro-2026.md`](../../roadmap-tcc-outubro-2026.md). Esta
seção resume a evolução técnica do produto.

**Já implementado (MVP funcional):**

- Detecção em tempo real de 3 EPIs faciais (capacete, óculos de proteção, máscara) via YOLOv8
- Dashboard de monitoramento com feed ao vivo e painel de alertas
- Dashboard analítico com gráficos de compliance e KPIs de sessão
- Configuração dinâmica de quais EPIs monitorar
- Deploy containerizado via Docker Compose
- Suíte de testes automatizados (pytest)

**Próximas fases:**

- Deploy em nuvem para o TCC com VPS, domínio HTTPS, Postgres e storage
- GPU sob demanda com RunPod para retreinamento, validação cloud e eventual inferência na demo
- Validação com câmeras RTSP reais ou vídeos autorizados de canteiros via replay RTSP
- Workflow completo de melhoria contínua: revisão de alerta, exportação de amostras, retreino e promoção de modelo
- Ingestão de streams RTSP de câmeras IP remotas via AWS Kinesis Video Streams
- Processamento GPU cloud (EC2 G4dn) para múltiplos streams simultâneos
- Persistência de dados com PostgreSQL (RDS) para histórico de alertas e relatórios
- Multi-tenancy com Cognito para múltiplos clientes e canteiros
- Blur facial automático em todos os frames persistidos (conformidade LGPD)
- Detecção de corpo inteiro para EPIs não faciais (luvas, colete, calçado de segurança)
- Relatórios de compliance exportáveis em PDF para auditorias da NR-6
- Aplicativo mobile para supervisores receberem alertas push em tempo real
- Treinamento contínuo do modelo com dados anonimizados para melhoria progressiva da acurácia
