# Roadmap TCC — Vigilante.AI até outubro de 2026

> Objetivo: chegar na apresentação final com o Vigilante.AI rodando em nuvem,
> processando câmeras reais de canteiros de obra, com melhoria mensurável do
> modelo de detecção e um workflow funcional de revisão, feedback e retreinamento.

## Norte do projeto

Até outubro, o projeto não pode ser apenas uma demo local bonita. Ele precisa
provar quatro coisas:

1. **Produto utilizável**: login, cadastro de canteiros/câmeras, alertas,
   revisão, relatórios e notificações funcionando fora da máquina local.
2. **Detecção em cenário real**: modelo testado em ângulos de CCTV/canteiro,
   não só em imagens frontais ou vídeos controlados.
3. **Melhoria contínua**: alertas revisados viram dados de treino, e o modelo
   melhora por ciclo documentado.
4. **Operação apresentável**: deploy estável, observabilidade, plano de custo,
   segurança/LGPD e fallback de demonstração.

## Definição de pronto para a apresentação final

| Área | Critério mínimo para outubro |
|---|---|
| Nuvem | Frontend, API, banco e storage publicados com domínio HTTPS |
| Inferência | Pelo menos 1 fluxo RTSP real ou simulado em nuvem, com VPS validada e GPU dedicada no RunPod para inferência live |
| Câmeras reais | Pelo menos 2 fontes reais de canteiro/obra/ambiente industrial testadas, mesmo que por piloto curto |
| Detecção | Métricas por classe em conjunto de validação próprio: **capacete e colete** como promessa principal |
| Active learning | Fluxo completo: alerta gerado -> humano confirma/rejeita -> amostra exportada -> retreino -> comparação de métricas |
| Produto | Admin consegue cadastrar empresas, usuários, canteiros e câmeras pelo painel; operador consegue monitorar, revisar alertas e exportar relatório sem intervenção no código |
| Governança | Política de privacidade publicada, app Meta/WhatsApp configurado para produção, auditoria LGPD/NR documentada e blur facial aplicado antes de persistir evidências |
| Segurança | Segredos fora do repositório, HTTPS, roles de usuário, cadastro fechado por painel admin, retenção de frames e explicação LGPD documentada |
| Demonstração | Roteiro com demo ao vivo + vídeo/fallback gravado com o mesmo build |

## Estratégia técnica

O caminho recomendado é evoluir em duas camadas:

- **Camada pragmática para o TCC**: VPS sempre ligado para frontend/API/Postgres
  e storage, com **RunPod como GPU dedicada para inferência live e retreinamento
  sob demanda**. A VPS não deve ser tratada como nó de visão principal, porque a
  matemática de múltiplos streams RTSP + YOLO não fecha em CPU comum. Este
  caminho conversa com o plano em `docs/gpu-on-demand-plan.md` e reduz risco até
  outubro.
- **Arquitetura alvo de produto**: AWS com Kinesis Video Streams, EC2 G4dn, RDS,
  S3, CloudFront e Cognito, já descrita em
  `docs/fase-5-6-infra-solucao/parte5-e-6-infraestrutura-e-solucao.md`.

Para a banca, a narrativa fica clara: o TCC entrega um produto em nuvem funcional
em servidor próprio com GPU dedicada sob demanda para visão computacional, e demonstra o caminho
técnico para escalar para AWS gerenciada se o produto crescer.

## Premissas atuais

- A VPS já existe e deve ser a base do deploy do TCC.
- Os custos recorrentes já esperados são IA, número/serviço de mensagens
  (Twilio/WhatsApp ou equivalente) e pequenos serviços auxiliares, estimados em
  aproximadamente R$ 30-40/mês.
- Treinamentos principais podem usar GPU própria. RunPod entra na Fase 5 como GPU
  dedicada para inferência live em nuvem e também para retreinamento/validação
  sob demanda.
- Créditos de cloud podem ajudar, mas não devem virar dependência crítica da
  apresentação.
- A apresentação decisiva pode acontecer entre setembro e começo de outubro;
  portanto setembro é o deadline interno de produto pronto.
- O escopo de visão computacional deve priorizar **capacete e colete**. Máscara,
  óculos, luvas e botas só entram como extensão se houver dados reais e qualidade
  suficiente.
- Cadastro aberto é apenas conveniência de desenvolvimento. Para piloto real, o
  onboarding deve ser via **painel admin**: criar tenant/empresa, convidar
  usuários, atribuir papel, cadastrar canteiro e cadastrar câmera.
- WhatsApp/Meta em produção exige política de privacidade pública, URL de suporte,
  configuração do app Meta, webhook público e templates aprovados.

## Roadmap executivo por fases

| Fase | Janela | Objetivo | Evidência para a banca |
|---|---|---|---|
| **Fase 1 — Base funcional** | Junho | Consolidar o produto atual e fechar escopo em capacete/colete | Protótipo estável, fluxo de câmera-alerta-revisão-relatório funcionando |
| **Fase 2 — Nuvem do TCC** | Julho | Tirar do localhost e operar em servidor na nuvem com GPU dedicada para live | Domínio HTTPS, banco/storage persistentes, RunPod GPU, painel admin e câmera RTSP validada |
| **Fase 3 — Dados reais e melhoria contínua** | Agosto | Provar que o modelo aprende com uso real e que o produto é auditável | Frames revisados viram dataset, retreino gera métricas, relatórios NR e trilha LGPD |
| **Fase 4 — Versão pronta** | Setembro | Ter uma versão boa o suficiente para seleção/apresentação | Demo completa, métricas, relatório, LGPD, Meta/WhatsApp e fallback gravado |
| **Fase 5 — Banca final** | Outubro | Apresentar produto, validação e plano de escala | Produto em nuvem, câmera/replay real, alerta, revisão e roadmap AWS |

Este roadmap evita detalhar tarefas internas de código. Quando algum ponto exigir
implementação específica, o detalhe técnico fica em documentos próprios, como
`docs/gpu-on-demand-plan.md`.

## Roadmap por mês

### Junho de 2026 — estabilizar base e fechar escopo realista

**Produto**

- Revisar o fluxo atual de câmeras, alertas, histórico, relatórios e notificações.
- Fechar o conjunto de EPIs obrigatório para a apresentação: **capacete** e
  **colete**. Óculos, máscara, luvas e botas ficam fora da promessa principal,
  porque a resolução/ângulo das câmeras de canteiro tende a não sustentar uma
  detecção confiável desses itens no TCC.
- Criar uma lista de "não pode quebrar" para a demo: login, câmera, stream,
  alerta, feedback, relatório e notificação.
- Definir o modelo de onboarding real: cadastro fechado, painel admin, convite
  de usuários, papéis (`admin`, `supervisor`, `viewer`), canteiros e câmeras.
- Listar ajustes de Landing Page: proposta clara para PME/construtora, foco em
  capacete/colete, LGPD nativa, relatório NR e CTA para solicitar demonstração.

**ML**

- Auditar o modelo atual (`backend/best.pt`) em vídeos de CCTV/canteiro e separar
  erros por tipo: falso positivo, falso negativo, baixa luz, oclusão, distância,
  ângulo alto e compressão.
- Montar o primeiro dataset interno de validação com frames reais/simulados,
  mantendo split fixo para comparação entre versões.
- Definir métricas oficiais: mAP@0.5, recall por classe, precisão por classe,
  taxa de falso alerta por minuto e latência por frame.

**Dados reais**

- Mapear contatos para obter câmeras ou vídeos: obras conhecidas, construtoras
  pequenas, técnicos de segurança, condomínios em obra, fornecedores de CFTV,
  familiares/amigos em reforma.
- Preparar termo simples de autorização/uso acadêmico e política de anonimização:
  usar frames apenas para pesquisa, aplicar blur facial, não publicar imagens
  identificáveis.
- Rascunhar política de privacidade pública: finalidade do tratamento, base legal
  LGPD, retenção, direitos do titular, contato, uso de imagens e canais de
  notificação.

**Infra**

- Escolher o deploy de TCC: VPS + Docker Compose/Dokploy como caminho principal.
- Definir domínio, variáveis de ambiente, backup do Postgres e storage de frames.
- Definir orçamento operacional do TCC: VPS existente, mensagens/IA recorrentes
  e RunPod ligado em janelas controladas para inferência live, testes e retreino.

**Entrega do mês**

- Documento de escopo fechado.
- Baseline de métricas do modelo atual em dados CCTV.
- Lista de fontes potenciais de câmera real.
- Ambiente de staging em nuvem iniciado ou provisionado.

### Julho de 2026 — colocar em nuvem e validar RTSP real

**Produto**

- Publicar frontend e backend com domínio HTTPS.
- Criar painel admin para operar piloto real: empresas/tenants, usuários, papéis,
  canteiros, câmeras, integrações e parâmetros básicos.
- Remover dependência de cadastro aberto em produção; primeiro usuário/tenant
  pode continuar existindo só como bootstrap/dev.
- Garantir que cadastro de câmera via painel admin, status da câmera,
  iniciar/parar stream e histórico funcionem fora do localhost.
- Refinar a Landing Page para venda/validação: problema, proposta, como funciona,
  LGPD, relatório NR, preço/CTA e prova visual do produto.
- Melhorar UX de câmera indisponível: erro claro, retry, status offline e logs.

**Infra**

- Subir Postgres persistente e storage de frames.
- Configurar deploy reproduzível com `.env.example`, volumes, health checks e
  logs.
- Separar a responsabilidade operacional: VPS roda produto e persistência; RunPod
  roda inferência live com GPU dedicada.
- Criar monitoramento mínimo: uptime da API, uso de CPU/RAM, FPS por câmera,
  número de alertas e erros de stream.

**Compliance e canais**

- Publicar a política de privacidade em URL estável do domínio do produto.
- Preparar publicação/configuração do app Meta: Business/App, webhook público,
  permissões, número, templates, política de privacidade e página de suporte.
- Definir textos de opt-in/uso de WhatsApp e retenção de mídia enviada por canal.

**RTSP e canteiros**

- Validar 3 tipos de fonte:
  - câmera IP real em rede acessível;
  - vídeo de obra servido como RTSP via MediaMTX;
  - câmera remota via túnel/VPN/port-forward controlado.
- Registrar no doc quais configurações funcionaram: codec, resolução, FPS,
  bitrate, latência e estabilidade.

**ML**

- Coletar frames de erros reais e enviar para Label Studio.
- Anotar pelo menos um lote inicial de melhoria, priorizando capacete/colete em
  ângulo de câmera de segurança.
- Rodar primeiro retreino e comparar contra o baseline de junho.

**Entrega do mês**

- App acessível publicamente por HTTPS.
- Pelo menos 1 câmera RTSP real ou simulada rodando em ambiente de nuvem.
- Relatório "Modelo v1 -> v2" com métricas e exemplos de erros corrigidos.

### Agosto de 2026 — fechar workflow de melhoria contínua

**Produto**

- Transformar revisão de alertas em parte central do produto: confirmar, rejeitar,
  classificar motivo do erro e exportar para retreino.
- Ajustar relatórios para responder perguntas de segurança do trabalho: horários
  críticos, câmeras com mais violações, EPIs mais ausentes e evolução semanal.
- Criar trilha de auditoria para ações relevantes: quem cadastrou câmera, quem
  iniciou monitoramento, quem confirmou/rejeitou alerta, quem exportou relatório.
- Criar visão de auditoria LGPD/NR: retenção de frames, base legal, evidências
  anonimizadas, histórico de revisão e relatório NR-6/NR-18 exportável.
- Aplicar blur facial antes de persistir ou enviar qualquer frame por canal
  externo. Se algum frame raw existir para revisão interna, acesso restrito a
  admin/supervisor e retenção curta.
- Garantir que WhatsApp/Teams funcione para alerta confirmado, não para todo
  falso positivo bruto.

**ML/MLOps**

- Formalizar o ciclo:
  1. sistema gera alerta;
  2. supervisor revisa;
  3. amostra vai para `ml/data/feedback`;
  4. dataset é mesclado;
  5. modelo é retreinado;
  6. métricas são comparadas;
  7. novo `best.pt` é promovido se melhorar.
- Criar versionamento simples de modelo: nome, data, dataset, métricas, pesos e
  decisão de promoção/rejeição.
- Exportar modelo para ONNX/TensorRT se a GPU escolhida exigir otimização.

**Dados reais**

- Fechar pelo menos um piloto de baixa fricção: algumas horas de vídeo, uma
  câmera de canteiro, ou gravações autorizadas.
- Se não houver acesso contínuo, gravar um pacote de vídeos reais para replay
  RTSP durante a demo.

**Infra**

- Implementar o split mínimo descrito em `docs/gpu-on-demand-plan.md` se a CPU/VPS
  não sustentar a demo: API interna, token de serviço e container de inferência
  separado.
- Definir se a demo final usa RunPod manual ou RunPod on-demand com controller.
  CPU otimizada fica apenas como fallback degradado, não como arquitetura da demo
  live.

**Entrega do mês**

- Workflow de active learning funcionando ponta a ponta.
- Modelo v3 treinado com dados revisados do próprio sistema.
- Relatórios e notificações alinhados ao uso real do técnico de segurança.

### Setembro de 2026 — produto pronto para seleção/apresentação

Setembro deve ser tratado como o prazo real. Mesmo que a banca final aconteça no
fim de outubro, a versão capaz de convencer avaliadores precisa estar pronta no
fim de setembro ou começo de outubro.

**Confiabilidade**

- Rodar teste de longa duração: pelo menos 2 horas contínuas com stream RTSP.
- Corrigir vazamentos de memória, travamentos de stream, reconexão e duplicação
  de alertas.
- Definir fallback de demo: vídeo local, RTSP simulado e gravação curta do produto
  funcionando em nuvem.

**Segurança e LGPD**

- Revisar segredos, CORS, autenticação, roles e exposição de endpoints.
- Garantir blur/anonimização dos frames persistidos e enviados por WhatsApp/Teams.
- Documentar retenção de dados, finalidade acadêmica, não reconhecimento facial
  e limites de uso.
- Validar política de privacidade publicada, textos de opt-in e configuração do
  app Meta/WhatsApp em modo pronto para produção.
- Testar painel admin com cadastro fechado: criar tenant, usuário, canteiro,
  câmera, integração e permissões sem mexer no banco ou código.

**ML**

- Congelar conjunto de validação final.
- Rodar avaliação comparativa dos modelos principais: baseline, v2, v3 e final.
- Preparar imagens de exemplo: acerto, falso positivo, falso negativo e caso
  difícil, sem expor identidade.

**Produto**

- Polir fluxo da apresentação: criar tenant demo, canteiro demo, câmeras demo e
  dados históricos plausíveis.
- Garantir relatório PDF/visual exportável para mostrar valor de compliance.
- Garantir que a LP pública aponte para login/demo, política de privacidade e
  proposta de valor sem depender de cadastro aberto.

**Entrega do mês**

- Release candidate do TCC, já bom o suficiente para apresentação seletiva.
- Métricas finais preliminares.
- Roteiro da apresentação com demo ao vivo e fallback.

### Outubro de 2026 — apresentação final

**Semana 1**

- Congelar código da versão apresentada.
- Rodar smoke test completo em nuvem.
- Gerar relatório final de métricas e custos.
- Validar política de privacidade, app Meta, webhook e templates de WhatsApp.

**Semana 2**

- Ensaiar apresentação com cronômetro.
- Validar internet, domínio, credenciais de demo e plano B offline.
- Gravar vídeo curto da demo real em nuvem para backup.

**Semana 3/4**

- Apresentar:
  - problema real de fiscalização de EPI;
  - produto rodando em servidor na nuvem;
  - câmera/RTSP processada;
  - alerta e revisão humana;
  - melhoria contínua do modelo;
  - relatório de compliance;
  - plano de escala para AWS/Kinesis/GPU quando houver demanda comercial.

## Backlog priorizado

### P0 — obrigatório

- Deploy público com HTTPS.
- Painel admin para cadastro fechado de tenants, usuários, canteiros, câmeras e integrações.
- Cadastro e operação de câmera RTSP.
- Inferência live em GPU dedicada no RunPod.
- Alertas persistidos com frame.
- Revisão de alerta com feedback.
- Blur facial antes de persistir/enviar evidência.
- Política de privacidade pública.
- App Meta/WhatsApp configurado para operação real.
- Relatórios e trilha de auditoria LGPD/NR.
- Pipeline de retreino usando feedback.
- Métricas reais do modelo em dataset CCTV.
- Relatório ou dashboard de compliance.
- Fallback de demo reproduzível.

### P1 — forte diferencial

- Notificação WhatsApp/Teams após alerta confirmado.
- GPU separada ou on-demand com RunPod.
- Versionamento de modelo e comparação de métricas no README/relatório.
- Monitoramento de FPS, latência e saúde das câmeras.
- Integração com pelo menos uma câmera real de canteiro.
- Landing Page refinada para validação comercial e solicitação de demo.

### P2 — se sobrar tempo

- Controller automático de GPU com idle timeout.
- Multi-nó por canteiro.
- Export TensorRT/INT8.
- Mapa de canteiros.
- Convites de usuários e permissões mais granulares.

## Plano para conseguir câmeras de canteiro

O maior risco do projeto é não ter dados reais. A estratégia precisa começar em
junho, não em setembro.

1. **Abordagem por acesso pessoal**: procurar obras pequenas, reformas,
   construtoras locais e conhecidos com câmera de segurança apontada para obra.
2. **Proposta simples**: pedir apenas algumas horas de vídeo ou acesso temporário,
   com rostos borrados e uso acadêmico.
3. **Alternativa controlada**: montar uma cena própria com câmera alta,
   baixa resolução, colete/capacete e fundo de obra/reforma.
4. **Replay RTSP**: qualquer vídeo real autorizado vira fonte RTSP via MediaMTX
   para testar o produto como se fosse câmera ao vivo.
5. **Banco de casos difíceis**: separar frames de sombra, distância, oclusão,
   capacete parcial, colete coberto e trabalhadores pequenos na imagem.

## Métricas que devem aparecer no TCC

| Métrica | Por que importa |
|---|---|
| mAP@0.5 por classe | Mede qualidade geral da detecção |
| Recall de ausência de EPI | Evita deixar risco passar sem alerta |
| Precisão dos alertas | Evita fadiga por falso positivo |
| Falso alerta por minuto/câmera | Métrica mais próxima da experiência do supervisor |
| Latência alerta fim a fim | Mostra se a ação corretiva é viável |
| FPS por câmera | Mostra limite operacional |
| Tempo de uptime do teste | Mostra confiabilidade |
| Custo mensal estimado | Mostra viabilidade de negócio |

## Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Não conseguir câmera real | Alto | Usar vídeos autorizados + replay RTSP + cena própria com câmera alta |
| Modelo bom em dataset e ruim em obra | Alto | Criar validação CCTV fixa e ciclo de feedback desde junho |
| GPU cara/instável | Médio | Demo com janela curta, RunPod manual/on-demand, pré-aquecimento antes da banca e CPU fallback apenas degradado |
| RTSP remoto difícil por rede/NAT | Médio | MediaMTX, túnel controlado, gravação/replay e documentação da limitação |
| Falso positivo excessivo | Alto | Revisão humana antes de notificar, cooldown, ajuste de threshold por câmera |
| Piloto parecer demo interna | Alto | Cadastro fechado por painel admin, LP refinada, política pública e app Meta configurado |
| Bloqueio Meta/WhatsApp | Médio | Política de privacidade pública, webhook estável, templates aprovados e canal alternativo Teams |
| Evidência sem anonimização | Alto | Blur facial antes de persistir/enviar, acesso raw restrito e retenção curta |
| Perder tempo em escala prematura | Alto | P0 primeiro; AWS completa fica como arquitetura alvo, não bloqueio da demo |
| Exposição de dados pessoais | Alto | Blur facial, retenção mínima, autorização e não publicar frames identificáveis |

## Narrativa final recomendada

"O Vigilante.AI começou como um protótipo local de visão computacional. Até a
entrega final, evoluiu para uma plataforma SaaS em nuvem capaz de receber
câmeras RTSP, detectar ausência de capacete e colete, gerar alertas revisáveis,
registrar evidências anonimizadas e alimentar um ciclo de melhoria contínua do
modelo. A arquitetura entregue usa uma VPS para o produto e uma GPU dedicada sob
demanda no RunPod para inferência live, enquanto a arquitetura alvo documentada
mostra como o produto escala para AWS com ingestão gerenciada de vídeo e GPU
dedicada quando houver demanda comercial."
