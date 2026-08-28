# Vigilante.AI

## Estratégia de mercado, viabilidade financeira e evolução do MVP

Startup One, Fase 5
FIAP, agosto de 2026

**Repositório:** <https://github.com/badmuriss/vigilante-ai>
**Vídeo de apresentação:** {{YOUTUBE_URL}}

## 1. Equipe

| Nome | RM |
|---|---:|
| Felipe Neves Cavalcanti | 551619 |
| Mateus Vicente | 550521 |
| Gabriel Da Silva Freitas | 551195 |
| Murilo Alves de Moura | 98220 |
| Roberto Felix de Araújo Guedes | 99976 |

## 2. Resumo executivo

O Vigilante.AI é uma plataforma B2B de segurança do trabalho. O sistema usa visão computacional para verificar capacete e colete em streams de câmeras, cria alertas revisáveis e transforma ocorrências em indicadores para o técnico de segurança.

Desde a última entrega, o protótipo deixou de ser apenas um monitor de câmera. Hoje ele reúne operação multiempresa, revisão humana, notificações, assistente conversacional, base de conhecimento e um ciclo de melhoria do modelo. A aplicação sobe por Docker Compose e passou por validação funcional em 28 de agosto de 2026: build de produção aprovado, 128 testes de back-end aprovados, banco e modelo prontos nos health checks e auditoria visual responsiva em quatro formatos de tela.

O escopo de implementação está acima dos 80% desejáveis para esta etapa. A prova acadêmica usa Amazon RDS for PostgreSQL em nuvem. Front-end, API e inferência executam no k3s da máquina de demonstração e são publicados em `https://vigilanteai.outis.com.br` por Cloudflare Tunnel. O banco exige TLS, carrega `pgvector`, recebeu todas as migrations e preservou câmera e alerta depois do reinício do back-end. Isso não significa prontidão comercial. O checkpoint publicado marcou mAP@0.5 de 0,944 em uma divisão contaminada por frames semelhantes, mas falhou na avaliação de CCTV real: apenas 4% de cobertura e 100% de falsos alarmes de capacete na amostra disponível. O próprio plano de treinamento do repositório classifica o resultado anterior como memorização. Fonte: `ml/TRAINING_PLAN.md`, consultado em 28 de agosto de 2026. O retreinamento com imagens representativas e a validação por câmera real continuam pendentes.

## 3. Parte 1: versão atual do projeto

### 3.1 Evoluções desde a Fase 4

| Eixo | Fase 4 | Versão atual |
|---|---|---|
| Visão computacional | Detecção de capacete e colete em RTSP | Regra por pessoa, evidência positiva de EPI, avaliação por escala e recorte do infrator |
| Privacidade | Blur facial planejado | Anonimização automática da região da cabeça nos artefatos enviados para revisão |
| Alertas | Revisão no painel | Revisão no painel e no WhatsApp, com confirmação ou rejeição |
| Comunicação | Notificações previstas | WhatsApp Cloud API, Teams Workflows e webhook de mensagens recebidas |
| Inteligência | Dashboard e relatórios | Assistente conversacional com ferramentas, histórico, gráficos e RAG sobre normas e manuais |
| Conhecimento | Documentos estáticos | Base vetorial com `pgvector`, ingestão e recuperação de NR-06, NR-18 e manual do produto |
| Operação | Docker Compose local | Health checks, métricas Prometheus, logs estruturados, manifests Kubernetes/k3s e execução híbrida com AWS RDS |
| Dados | PostgreSQL e Alembic | Cinco migrations, isolamento multi-tenant, `pgvector`, TLS e persistência validada no RDS |
| Demonstração | Dependência de câmera ou RTSP externo | Fonte replay autorizada, cadastrável pela interface e reiniciada automaticamente no fim do arquivo |
| Qualidade | Testes do núcleo | 128 testes aprovados, build de produção e inspeção visual em desktop, notebook, tablet e celular em 28 ago. 2026 |

### 3.2 O que já funciona

- Cadastro e login com JWT e papéis `admin`, `supervisor` e `viewer`.
- Separação de tenants, usuários, locais, câmeras, alertas e configurações.
- Cadastro, teste, início e parada de fontes webcam ou RTSP.
- Cadastro de vídeo replay para uma demonstração repetível, sem depender de câmera externa.
- Inferência com YOLO, stream anotado e geração de alerta por pessoa.
- Histórico, filtros, feedback correto ou falso positivo e exportação para retreinamento.
- Relatórios visuais e exportação em PDF.
- Notificação de alerta confirmado por WhatsApp e Microsoft Teams.
- Assistente com conversas persistidas, ferramentas de câmeras, alertas, gráficos e base de conhecimento.
- PostgreSQL com `pgvector`, migrations e persistência no Amazon RDS.
- Métricas, logs estruturados, `/healthz` e `/readyz`.

### 3.3 Pendências antes de um piloto comercial

- Validar uma câmera RTSP real pela internet ou por túnel seguro.
- Separar o worker de inferência do serviço web antes de hospedar o processamento de vídeo integralmente em nuvem.
- Fechar política de retenção, termos, base legal e fluxo operacional de atendimento aos titulares.
- Medir precisão, recall, latência e falsos alertas no ambiente do primeiro cliente.
- Concluir o painel de onboarding administrativo. O cadastro aberto já fica bloqueado na configuração AWS da demonstração.
- Criar rotina de backup, restauração e resposta a incidentes.

### 3.4 Limitação atual do modelo

O número de mAP publicado não representa desempenho em um canteiro real. A separação aleatória do dataset colocou frames semelhantes dos mesmos vídeos em treino e validação. Em imagens de CCTV disponíveis no projeto, trabalhadores aparecem pequenos, comprimidos e vistos de cima. O modelo anterior perdeu objetos e transformou ausência de detecção em acusação de ausência de EPI.

Por isso, o primeiro uso externo será um piloto de codesenvolvimento, sem promessa de detecção autônoma. Toda ocorrência continuará sujeita a revisão humana. O objetivo do piloto é construir um conjunto de dados representativo, calibrar cada câmera e medir precisão, recall, cobertura e falsos alertas antes da venda comercial.

## 4. Parte 2: Go to Market Canvas

### 4.1 Segmento de clientes

**Beachhead:** construtoras pequenas e médias com até quatro câmeras em canteiros ativos, técnico de segurança responsável e infraestrutura IP compatível com acesso por VPN.

**Usuário diário:** técnico ou engenheiro de segurança do trabalho.

**Comprador:** diretor de operações, dono da construtora ou gestor de SMS/SST.

**Influenciadores:** consultorias de SST, corretores de seguros empresariais e integradores de CFTV.

A escolha reduz a complexidade inicial. O produto começa com dois EPIs visuais e reaproveita a infraestrutura de vídeo existente, sem exigir hardware proprietário no canteiro.

### 4.2 Proposta de valor

> Transformar câmeras existentes em uma camada preventiva de segurança, com alertas verificáveis e histórico de conformidade, sem substituir o técnico de SST.

O valor está no fluxo completo. O sistema identifica EPI, preserva uma evidência anonimizada, pede revisão humana, registra a decisão, notifica a equipe e alimenta o retreinamento.

### 4.3 Canais de aquisição

1. Venda consultiva pelo LinkedIn e indicação, com lista curta de construtoras regionais.
2. Parcerias com consultorias de SST e integradores de câmeras, remuneradas por indicação.
3. Demonstração remota de 20 minutos usando um stream autorizado do potencial cliente.
4. Conteúdo técnico com exemplos de implantação, privacidade e redução de ruído operacional.
5. Eventos e comunidades de construção civil, segurança e tecnologia industrial.

O canal principal no MVP é outbound consultivo. Mídia paga entra apenas após o grupo conhecer taxa de conversão e ciclo de venda.

### 4.4 Estratégia de preço e promoção

Valores abaixo são hipóteses comerciais para teste, não preços já validados por contratos.

| Oferta | Preço | Escopo |
|---|---:|---|
| Piloto de codesenvolvimento | R$ 0 por 90 dias | Um parceiro, até quatro câmeras, calibração, revisão semanal e coleta autorizada de amostras |
| Plano fundador após o piloto | R$ 990,00/mês por três meses | Continuidade assistida, ainda sem SLA de detecção, condicionada aos resultados do piloto |
| Plano Operação, hipótese futura | R$ 2.490,00/mês | Até quatro câmeras, cobertura de segunda a sexta, das 7h às 18h, após validação por câmera |
| Câmera adicional | R$ 249,00/mês | Processamento e retenção conforme política contratada |

O piloto gratuito não é uma promoção aberta. Apenas uma empresa entra como parceira de desenvolvimento. Ela fornece acesso autorizado ao ambiente, ajuda a revisar amostras e permite o uso contratualmente delimitado de imagens para treinamento. Custos de adaptação física, câmera, NVR ou integrador permanecem com a empresa parceira. Ao final de 90 dias, as partes analisam as métricas. Não existe conversão automática nem promessa de desempenho.

O contrato comercial de R$ 2.490 só será oferecido quando uma câmera cumprir o critério de aceite definido com o técnico de SST. O plano fundador de R$ 990 mantém o primeiro parceiro durante a estabilização e não serve como referência definitiva de preço.

### 4.5 Programa do parceiro de desenvolvimento

O piloto precisa de um termo próprio, revisado por assessoria jurídica, com estes pontos:

- empresa parceira como controladora das imagens de seus trabalhadores e Vigilante.AI como operador, salvo decisão jurídica diferente para alguma finalidade;
- finalidade separada para operar o piloto e para selecionar imagens de treinamento;
- informação clara aos trabalhadores, canal para exercício de direitos e definição da base legal pelo controlador;
- áreas filmadas, horários, câmeras e pessoas autorizadas delimitados;
- imagens brutas fora do conjunto selecionado eliminadas em até sete dias;
- amostras selecionadas passam por recorte, redução de identificadores e controle de acesso, mas continuam tratadas como dados pessoais enquanto houver possibilidade razoável de reidentificação;
- proibição de reconhecimento facial, avaliação disciplinar automática e compartilhamento do dataset bruto;
- registro de quem aprovou cada amostra, versão do dataset e pedido de eliminação;
- transferência internacional e suboperadores, incluindo AWS e provedores de mensageria, descritos no contrato e no aviso de privacidade;
- encerramento do acesso e devolução ou eliminação dos dados quando o piloto terminar.

O blur facial reduz risco, mas não garante anonimização jurídica. Roupa, uniforme, local e horário podem permitir reidentificação. A LGPD exige finalidade específica, necessidade, transparência, segurança e prestação de contas. A base legal não deve ser escolhida pelo sistema sem análise do contexto do empregador.

### 4.6 Principais métricas

| Dimensão | Métrica | Meta inicial |
|---|---|---:|
| Aquisição | Reuniões qualificadas por mês | 12 |
| Conversão | Reunião para piloto | 25% |
| Venda | Piloto para contrato | 50% |
| Produto | Câmeras ativas no piloto | Até 4 |
| Operação | Disponibilidade mensal do painel | 99% no piloto |
| IA | Precisão, recall e cobertura | Medir por câmera; meta definida após a primeira semana rotulada |
| Uso | Tempo mediano de revisão | Menor que 5 min |
| Retenção | Churn mensal usado no modelo | 2,5% |
| Unidade econômica | LTV/CAC | Maior que 3 |

Metas de IA só viram compromisso comercial depois da medição no cenário do cliente. Uma precisão global de dataset não substitui desempenho por câmera.

## 5. Análise financeira

### 5.1 Premissas

Esta análise usa um cenário-base de seis meses. Os valores de negócio estão em reais. A seção de nuvem preserva preços oficiais em dólares e usa R$ 6,00 por dólar apenas como margem interna de planejamento, não como cotação.

- Receita do piloto de codesenvolvimento: R$ 0 nos três primeiros meses.
- Receita do plano fundador: R$ 990 por mês do quarto ao sexto mês, se o parceiro optar pela continuidade.
- Plano comercial futuro: R$ 2.490 por cliente ativo, ainda não usado no caixa do piloto.
- Custo variável recorrente: R$ 500 por cliente/mês.
- Custo variável de onboarding: R$ 600 por cliente novo.
- Custo fixo mensal até quatro clientes: R$ 2.500, sem pró-labore.
- Custo fixo mensal a partir de cinco clientes: R$ 12.500, incluindo R$ 10.000 de pró-labore total.
- Churn mensal para cálculo de LTV: 2,5%.
- CAC-meta: R$ 6.000 por novo contrato.

### 5.2 Estrutura de custos

| Custos fixos mensais, até quatro clientes | Valor |
|---|---:|
| Ferramentas, domínio e observabilidade | R$ 500 |
| Contabilidade e apoio jurídico | R$ 500 |
| Comercial e deslocamentos | R$ 1.000 |
| Reserva operacional | R$ 500 |
| Pró-labore | R$ 0 |
| **Total** | **R$ 2.500** |

Os fundadores mantêm seus empregos e absorvem a operação inicial. As horas trabalhadas serão registradas como custo econômico, mas não saem do caixa. Ao atingir cinco clientes ativos, entra um pró-labore total de R$ 10.000. O custo fixo mensal passa para R$ 12.500.

| Custos variáveis por cliente/mês | Valor |
|---|---:|
| Infraestrutura cloud, inferência e armazenamento | R$ 270 |
| Mensageria e APIs | R$ 30 |
| Suporte variável e revisão operacional | R$ 150 |
| Reserva de consumo por câmera | R$ 50 |
| **Total** | **R$ 500** |

O valor de R$ 270 é um envelope comercial conservador para banco, processamento, armazenamento e tráfego de um cliente. Ele não se limita à infraestrutura temporária da entrega. Na prova acadêmica, apenas o banco está na AWS. Front-end, API e inferência executam no k3s local, com acesso público pelo Cloudflare Tunnel. O RDS público custa US$ 17,63 por 730 horas nas tarifas consultadas, antes de créditos. A estimativa para sete dias é US$ 4,06. Os créditos promocionais reduzem o desembolso temporário, mas não reduzem o custo variável usado na margem. Fontes: [AWS Price List Bulk API](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-1/index.json) e [AWS VPC pricing](https://aws.amazon.com/vpc/pricing/), acesso em 28 ago. 2026.

### 5.3 Modelo de receita

O modelo tem três estágios. Nos primeiros 90 dias, um único parceiro participa gratuitamente do codesenvolvimento e autoriza, em contrato próprio, a seleção de amostras para treinamento. Se os resultados justificarem continuidade, o plano fundador custa R$ 990 por mês durante três meses e mantém operação assistida, sem SLA de detecção. A assinatura comercial de R$ 2.490 por mês só começa depois da validação por câmera. Não existe taxa de implantação na projeção de seis meses. Serviços fora do escopo, novas classes de EPI e integrações especiais poderão ser orçados separadamente no estágio comercial.

### 5.4 Fluxo de caixa do estágio de validação

| Mês | Parceiros gratuitos | Parceiros no plano fundador | Receita total | Marco |
|---:|---:|---:|---:|---|
| 1 | 1 | 0 | R$ 0 | Instalação e baseline por câmera |
| 2 | 1 | 0 | R$ 0 | Rotulagem e primeiro retreinamento |
| 3 | 1 | 0 | R$ 0 | Avaliação independente por câmera |
| 4 | 0 | 1 | R$ 990 | Continuidade assistida, se aprovada |
| 5 | 0 | 1 | R$ 990 | Ajuste de limiares e operação assistida |
| 6 | 0 | 1 | R$ 990 | Decisão sobre contrato comercial |

| Mês | Custos variáveis | Custos fixos | Fluxo do mês | Acumulado |
|---:|---:|---:|---:|---:|
| 1 | R$ 1.100 | R$ 2.500 | -R$ 3.600 | -R$ 3.600 |
| 2 | R$ 500 | R$ 2.500 | -R$ 3.000 | -R$ 6.600 |
| 3 | R$ 500 | R$ 2.500 | -R$ 3.000 | -R$ 9.600 |
| 4 | R$ 500 | R$ 2.500 | -R$ 2.010 | -R$ 11.610 |
| 5 | R$ 500 | R$ 2.500 | -R$ 2.010 | -R$ 13.620 |
| 6 | R$ 500 | R$ 2.500 | -R$ 2.010 | -R$ 15.630 |

O estágio de validação consome R$ 15.630 em seis meses no cenário conservador. Esse é o investimento para obter dados representativos e reduzir risco técnico. Não há pró-labore nesse período. O crédito de nuvem pode reduzir o desembolso, mas a projeção mantém o custo normal da infraestrutura.

### 5.5 Breakeven e métricas unitárias

**Margem de contribuição mensal por cliente**

```text
R$ 2.490 - R$ 500 = R$ 1.990
Margem de contribuição = 1.990 / 2.490 = 79,9%
```

**Ponto de equilíbrio do estágio de validação**

```text
O piloto não atinge breakeven em seis meses.
Capital necessário no cenário: R$ 15.630.
```

**Ponto de equilíbrio da hipótese comercial futura**

```text
Sem pró-labore: R$ 2.500 / R$ 1.990 = 1,26, portanto 2 clientes.
Com pró-labore total de R$ 10.000: R$ 12.500 / R$ 1.990 = 6,28, portanto 7 clientes.
```

**CAC**

O CAC-meta é R$ 6.000 por contrato. Ele deve incluir mídia, ferramentas, deslocamentos e horas comerciais. No início, o grupo deve apurar o CAC realizado pela fórmula `gastos de aquisição / novos clientes`.

**LTV**

Pelo método de margem dividido pelo churn:

```text
LTV = R$ 1.990 / 2,5% = R$ 79.600
```

Esse valor é sensível a uma hipótese de churn ainda não observada. Para decisão de caixa, usamos um LTV conservador de 12 meses:

```text
LTV conservador = R$ 1.990 × 12 = R$ 23.880
LTV/CAC conservador = 23.880 / 6.000 = 3,98
Payback do CAC = 6.000 / 1.990 = 3,02 meses
```

## 6. Parte 3: protótipo funcional de alta fidelidade

### 6.1 Arquitetura implementada

```text
Câmera RTSP ou vídeo autorizado
            |
            v
Worker FastAPI + OpenCV + YOLO
     |                    |
     v                    v
PostgreSQL/pgvector   Frame anonimizado
     |                    |
     +----------+---------+
                v
     API JWT multi-tenant
       |       |       |
       v       v       v
    Next.js  WhatsApp  Teams
       |
       v
Assistente com RAG e ferramentas
```

### 6.2 Stack

| Camada | Tecnologia |
|---|---|
| Interface | Next.js 15, React 18, TypeScript e Tailwind CSS |
| API | Python 3.11, FastAPI e Pydantic |
| Dados | PostgreSQL 16, SQLAlchemy, Alembic e pgvector |
| Visão | Ultralytics YOLO, OpenCV e FFmpeg |
| Vídeo | RTSP, MediaMTX e MJPEG para visualização |
| Integrações | Meta WhatsApp Cloud API e Teams Workflows |
| Operação | Docker Compose, Kubernetes/k3s, Prometheus e logs estruturados |

### 6.3 Banco de dados em nuvem

A entrega usa a instância `vigilante-fase5` no Amazon RDS, em `us-east-1`. A configuração validada em 28 de agosto de 2026 é PostgreSQL 16.15, `db.t4g.micro`, Single-AZ, 20 GiB gp3 e armazenamento criptografado. O parameter group exige TLS, e o security group aceita PostgreSQL somente do IP público atual em `/32`. A instância é temporária e não representa uma configuração de produção.

As migrations chegaram à revisão `0005`; `pgvector 0.8.2` foi carregado; `/healthz` retornou HTTP 200; e `/readyz` confirmou banco e modelo prontos. Um vídeo replay criou um alerta pendente. Depois do reinício do back-end, a câmera e o alerta permaneceram no RDS. A evidência técnica está em `research/sources/aws-cost/account-verification-2026-08-28.md`. Referências: [AWS RDS API](https://docs.aws.amazon.com/cli/latest/reference/rds/describe-db-instances.html) e [extensões PostgreSQL no RDS](https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-extensions.html), acesso em 28 ago. 2026.

### 6.4 Arquitetura da demonstração

O fluxo de demonstração separa componentes por necessidade operacional:

```text
Navegador -> Cloudflare Tunnel -> Ingress do k3s
                                      |
                                      v
                              Next.js -> FastAPI + YOLO
                                             |
                                             | TLS
                                             v
                                  Amazon RDS + pgvector
```

O processamento de vídeo permanece no nó k3s porque precisa acessar o arquivo replay e o modelo YOLO sem manter uma máquina de inferência ociosa na nuvem. O banco fica na AWS, conforme o requisito da atividade. O Cloudflare Tunnel publica o Ingress sem abrir uma porta residencial. O script de implantação atualiza as imagens, configura o backend para o RDS e valida login e câmera pelo domínio público. O PostgreSQL interno do cluster permanece disponível apenas como retorno e não recebe as operações desse modo. Segredos, senha e endpoint não entram no Git nem no pacote acadêmico.

### 6.5 Custo da entrega e rateio do grupo

| Item | Base | Valor de referência |
|---|---|---:|
| RDS `db.t4g.micro` | 730 h, 20 GiB gp3 e IPv4 público | US$ 17,63/mês |
| RDS durante a janela de entrega | 7 dias | US$ 4,06 |
| Saldo AWS autenticado | crédito promocional elegível | US$ 160,00 |
| Desembolso previsto de AWS | enquanto o crédito cobrir a cobrança | US$ 0,00 |
| Twilio já pago | valor informado pelo grupo, comprovante pendente | R$ 70,00 |
| Número Twilio recorrente | valor informado pelo grupo, comprovante pendente | US$ 4,60/mês |

As tarifas do RDS e do IPv4 vêm da [AWS Price List Bulk API](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-1/index.json) e da [AWS VPC pricing](https://aws.amazon.com/vpc/pricing/), acesso em 28 ago. 2026. O saldo foi consultado pela [AWS Free Tier API](https://docs.aws.amazon.com/cli/latest/reference/freetier/get-account-plan-state.html), acesso em 28 ago. 2026. O valor do número Twilio foi informado pelo grupo e não foi corroborado pela [página pública de preços do WhatsApp](https://www.twilio.com/en-us/whatsapp/pricing?locale=en), acesso em 28 ago. 2026; a fatura deve ser anexada ao controle interno.

O gasto histórico de R$ 70,00 equivale a R$ 14,00 por integrante em um grupo de cinco pessoas. Usando apenas como referência a PTAX de R$ 5,1642 por dólar em 27 de agosto de 2026, o número Twilio de US$ 4,60 equivale a R$ 23,75 por mês, ou R$ 4,75 por integrante. Assim, a cobrança acumulada conhecida seria R$ 18,75 por pessoa depois de incluir o primeiro mês do número, sem adicionar APIs ainda não faturadas. Fonte cambial: [Banco Central do Brasil](https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/10?formato=json), acesso em 28 ago. 2026.

### 6.6 Estado de conclusão

| Área | Conclusão estimada | Evidência | Falta |
|---|---:|---|---|
| Front-end | 90% | Páginas funcionais, build Docker e HTTP 200 | Ajustes finais e onboarding |
| Back-end e dados | 92% | API, migrations, RDS PostgreSQL e 128 testes | Backup e hardening de produção |
| Pipeline de visão | 85% | Modelo carregado, RTSP e avaliação local | Benchmark por câmera real |
| Validação do modelo em campo | 20% | Falha de generalização identificada e documentada | Dataset representativo, retreinamento e aceite por câmera |
| Integrações | 85% | WhatsApp, Teams, webhooks e assistente | Credenciais finais e testes externos |
| Nuvem | 90% | RDS implantado, TLS, `pgvector`, budget, k3s e domínio público validados | Backup e hospedagem gerenciada antes de produção |
| **MVP funcional** | **aprox. 86%** | Fluxo funcional com banco em nuvem | Piloto em câmera real e validação do modelo |

Os percentuais são estimativas de escopo, não métricas de desempenho.

## 7. Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Falso positivo em câmera distante | Fadiga de alerta | Revisão humana, calibração por câmera e active learning |
| Recurso cloud ocioso | Crédito consumido | Budget de US$ 10, janela curta de demonstração e script de remoção explícita |
| Exposição de trabalhadores | Risco de privacidade | Blur antes do envio, retenção curta e acesso por tenant |
| RTSP externo indisponível | Demo interrompida | Replay autorizado montado localmente e alerta já persistido no RDS |
| Dependência de WhatsApp/Teams | Notificação indisponível | Painel permanece como fonte de verdade e registra falhas |
| Crédito promocional acabar | Margem artificial | Precificação inclui custo normal de infraestrutura |

## 8. Referências

- Amazon Web Services. [Amazon RDS pricing data for `us-east-1`](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-1/index.json). Acesso em 28 ago. 2026.
- Amazon Web Services. [Amazon VPC pricing](https://aws.amazon.com/vpc/pricing/). Acesso em 28 ago. 2026.
- Amazon Web Services. [Storage for Amazon RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Storage.html). Acesso em 28 ago. 2026.
- Amazon Web Services. [PostgreSQL extensions supported by Amazon RDS](https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-extensions.html). Acesso em 28 ago. 2026.
- Amazon Web Services. [Free Tier account plan API](https://docs.aws.amazon.com/cli/latest/reference/freetier/get-account-plan-state.html). Acesso em 28 ago. 2026.
- Banco Central do Brasil. [Cotação do dólar, série 1](https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/10?formato=json). Acesso em 28 ago. 2026.
- Twilio. [WhatsApp pricing](https://www.twilio.com/en-us/whatsapp/pricing?locale=en). Acesso em 28 ago. 2026.
- Brasil. [Lei nº 13.709/2018, Lei Geral de Proteção de Dados Pessoais](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm). Acesso em 12 ago. 2026.
- ANPD. [Guia orientativo sobre tratamento de dados pessoais pelo legítimo interesse](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia_legitimo_interesse.pdf). Acesso em 12 ago. 2026.
- Vigilante.AI. Repositório e histórico do projeto. <https://github.com/badmuriss/vigilante-ai>. Acesso em 28 ago. 2026.
