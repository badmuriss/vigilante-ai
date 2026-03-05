# Vigilante.AI - Documentação Startup One

## Parte 1: Dados do Grupo

| Nome Completo | RM |
|---|---|
| [Preencher] | [Preencher] |
| [Preencher] | [Preencher] |
| [Preencher] | [Preencher] |
| [Preencher] | [Preencher] |
| [Preencher] | [Preencher] |

---

## Parte 2: Escolha da Área de Interesse

### Área escolhida: SafetyTech / IndustrialTech

A área de **segurança do trabalho com inteligência artificial** se enquadra na intersecção entre SafetyTech e IndustrialTech, utilizando visão computacional para resolver problemas críticos em ambientes industriais.

### Por que esta área?

A segurança do trabalho é um dos setores mais regulados e, paradoxalmente, mais dependentes de fiscalização humana. Segundo dados do Observatório de Segurança e Saúde no Trabalho, o Brasil registra cerca de 600 mil acidentes de trabalho por ano, com custos que ultrapassam R$ 13 bilhões anuais para a previdência social. A tecnologia de visão computacional, que amadureceu significativamente nos últimos 3 anos com modelos como YOLO, permite hoje criar soluções de monitoramento autônomo que eram impraticáveis há pouco tempo.

A inspiração vem da categoria **"AI for Real-World Applications"** do catálogo da YCombinator, que destaca oportunidades em aplicar IA a problemas tangíveis da indústria. Empresas como a Voxel (YC W18) já levantaram mais de US$ 100M validando este mercado.

---

## Parte 3: Identificação de Problemas

### Problema 1: Fiscalização humana de EPIs é falha e cara

**Descrição:** A verificação do uso correto de Equipamentos de Proteção Individual (EPIs) depende de fiscais humanos que não conseguem estar em todos os lugares simultaneamente. Um fiscal cobre, em média, uma área limitada e seu turno tem intervalos, pausas e distrações. Nos momentos sem supervisão direta, trabalhadores frequentemente relaxam o uso de EPIs.

**Quem é afetado:** Trabalhadores de indústrias, construtoras e centros logísticos (mais de 30 milhões de trabalhadores no Brasil), além das próprias empresas que arcam com custos de acidentes.

**Impacto:** Acidentes de trabalho causam: mortes e lesões permanentes, processos trabalhistas milionários, multas do Ministério do Trabalho (que podem chegar a R$ 6.700 por infração), interrupção da produção e danos à reputação da empresa. O custo médio de um acidente grave para a empresa é estimado em R$ 500 mil entre indenizações, multas e perda de produtividade.

### Problema 2: Falta de dados e rastreabilidade em incidentes de segurança

**Descrição:** A maioria das empresas não possui registros detalhados de quase-acidentes e violações de segurança. Quando um acidente acontece, é difícil reconstruir o que ocorreu, quais normas foram violadas e com que frequência. Relatórios são feitos manualmente, de forma inconsistente, e raramente geram insights acionáveis.

**Quem é afetado:** Gestores de segurança do trabalho, equipes de compliance, seguradoras e órgãos reguladores.

**Impacto:** Sem dados, empresas não conseguem identificar padrões de risco, áreas críticas ou turnos problemáticos. Decisões de segurança são tomadas de forma reativa (após o acidente) ao invés de preventiva. Seguradoras cobram prêmios mais altos de empresas sem histórico documentado de conformidade.

### Problema 3: Tempo de resposta lento em situações de risco

**Descrição:** Mesmo quando uma violação de segurança é identificada por um fiscal, o tempo entre a detecção e a ação corretiva pode ser longo demais. O fiscal precisa se deslocar até o local, comunicar o problema e garantir a correção. Em ambientes dinâmicos como canteiros de obras, segundos podem separar uma violação de um acidente.

**Quem é afetado:** Trabalhadores em ambientes de alto risco (construção civil, indústria pesada, logística com empilhadeiras).

**Impacto:** A demora na correção de violações aumenta exponencialmente o risco de acidentes. Estudos da OSHA (Occupational Safety and Health Administration) indicam que a maioria dos acidentes ocorre nos primeiros minutos após a violação de uma norma de segurança, quando o trabalhador ainda está em situação de risco.

---

## Parte 4: Reflexão sobre a Solução

### Possíveis clientes

- **Indústrias de médio e grande porte** com linhas de produção e exigências rigorosas de EPI
- **Construtoras** com canteiros de obras dinâmicos e alto índice de acidentes
- **Centros logísticos e armazéns** (estilo Amazon, Mercado Livre) com operação de empilhadeiras e esteiras
- **Empresas de mineração** com ambientes de alto risco
- **Consultorias de segurança do trabalho** que podem revender a solução

### Estratégia de convencimento (micro e macro momentos)

**Macro momentos:**
- Após um acidente de trabalho grave na empresa ou no setor (momento de dor aguda)
- Durante auditorias de segurança e renovação de certificações (ISO 45001)
- Na negociação de seguros corporativos (demonstrar conformidade reduz prêmios)
- Em feiras e eventos do setor (FISP, Prevenção)

**Micro momentos:**
- Conteúdo educativo sobre custos reais de acidentes (blog, LinkedIn, YouTube)
- Demos ao vivo mostrando detecção em tempo real (impacto visual forte)
- Cases de ROI: "Empresa X reduziu incidentes em Y% e economizou Z"
- Trial gratuito de 30 dias com a câmera do próprio cliente

### Foco no cliente no desenvolvimento

O desenvolvimento deve priorizar:
1. **Facilidade de uso:** O sistema será operado por técnicos de segurança, não por engenheiros de software. A interface deve ser intuitiva e autoexplicativa.
2. **Confiabilidade:** Falsos positivos excessivos fazem o usuário ignorar alertas (efeito "cry wolf"). O modelo deve ter alta precisão antes de ser implantado.
3. **Feedback imediato:** O valor do produto está na prevenção em tempo real. Latência alta anula o propósito.
4. **Transparência:** O usuário deve entender por que um alerta foi gerado (mostrar o frame, o bounding box, a confiança).

### Estratégia Mobile e Divulgação

O produto principal é uma aplicação web desktop (para monitoramento em telas grandes em salas de controle). Porém, o **smartphone entra como canal de notificação e acompanhamento**:

- **Notificações push** para gerentes quando violações são detectadas (versão futura)
- **Dashboard responsivo** acessível pelo celular para acompanhar métricas
- **PWA (Progressive Web App)** ao invés de app nativo, para reduzir custo de desenvolvimento e manter experiência mobile adequada
- **Divulgação:** Vídeos curtos no TikTok/Instagram Reels mostrando a IA detectando EPIs em tempo real (conteúdo viral pelo fator "uau")

Não há necessidade de desenvolvimento nativo iOS/Android no MVP. A abordagem PWA atende as necessidades mobile sem duplicar esforços de desenvolvimento.

---

## Parte 5: Reflexão sobre Cybersegurança

A cybersegurança é **crítica** para o Vigilante.AI por três razões:

### 1. Dados sensíveis de vídeo
O sistema processa imagens de trabalhadores em tempo real, o que envolve:
- **LGPD (Lei Geral de Proteção de Dados):** Imagens de pessoas são dados pessoais. O sistema deve ter consentimento dos trabalhadores, política de retenção de dados clara e não armazenar imagens além do necessário.
- **Segurança do stream de vídeo:** O feed da câmera não pode ser acessível publicamente. Mesmo em rede local, deve haver controle de acesso.

### 2. Integridade dos alertas
Se um atacante comprometer o sistema, ele pode:
- **Desabilitar alertas**, criando uma falsa sensação de segurança
- **Gerar alertas falsos**, causando fadiga de alertas e desconfiança no sistema
- **Alterar logs**, comprometendo a rastreabilidade

### 3. Superfície de ataque
- **Backend FastAPI:** Endpoints devem ser protegidos contra injeção de comandos, especialmente se receberem parâmetros de configuração do modelo ou câmera.
- **Dependências Python:** Bibliotecas como OpenCV e ultralytics devem ser mantidas atualizadas para evitar CVEs conhecidas.
- **Rede local:** Mesmo rodando localmente no MVP, boas práticas de segurança (CORS, rate limiting, input validation) devem ser implementadas desde o início.

### Medidas planejadas para o MVP
- CORS configurado para permitir apenas o frontend local
- Validação de inputs em todos os endpoints da API
- Nenhum armazenamento persistente de imagens/vídeo (processamento in-memory)
- Dependências fixadas com versões específicas (lock file)
- Headers de segurança básicos (Helmet equivalente para FastAPI)

---

## Parte 6: Reflexão sobre Sistemas Distribuídos e Arquiteturas

### No MVP (desenvolvimento e demonstração)

O MVP roda como **sistema monolítico local**:
- Backend Python (FastAPI + OpenCV + YOLO) em um único processo
- Frontend Next.js servido localmente
- Comunicação via HTTP/MJPEG na mesma máquina

Nesta fase, sistemas distribuídos **não são necessários**. A simplicidade é uma virtude para a demonstração e validação do conceito.

### Após conclusão e lançamento (escala)

Quando o produto escalar para múltiplos clientes e câmeras, sistemas distribuídos se tornam **essenciais**:

1. **Processamento distribuído de vídeo:**
   - Cada câmera gera um fluxo de dados significativo. Com 10+ câmeras, um único servidor não suporta a carga de inferência.
   - Solução: Workers distribuídos (um por câmera ou grupo de câmeras) com fila de mensagens (Redis/RabbitMQ) para coordenação.

2. **Separação de serviços:**
   - **Serviço de captura:** Conecta-se às câmeras e distribui frames
   - **Serviço de inferência:** Roda o modelo YOLO (pode escalar horizontalmente com GPU)
   - **Serviço de alertas:** Processa detecções e despacha notificações
   - **API Gateway:** Serve o frontend e gerencia autenticação

3. **Disponibilidade:**
   - Em ambiente de segurança do trabalho, o sistema não pode cair. Redundância e failover são obrigatórios.
   - Deploy com Kubernetes para auto-healing de containers.
   - Health checks e monitoring (Prometheus + Grafana).

4. **Edge Computing:**
   - Para reduzir latência e dependência de rede, o modelo pode rodar em dispositivos edge (NVIDIA Jetson) diretamente no chão de fábrica.
   - Apenas alertas e métricas são enviados para a nuvem.

### Arquitetura futura simplificada

```
[Câmeras IP]
     |
[Edge Devices - YOLO Inference]
     |
[Message Queue (Redis)]
     |
[Alert Service] -> [Notifications (Push, Email)]
     |
[API Service] -> [Database (PostgreSQL)]
     |
[Frontend (CDN)]
```

Esta arquitetura permite escalar cada componente independentemente, manter baixa latência (inferência no edge) e alta disponibilidade (redundância em cada camada).

---

## Links e Referências

- Vídeo da apresentação: [Inserir link YouTube não listado]
- Repositório GitHub: [Inserir link]
- Observatório de Segurança e Saúde no Trabalho: https://smartlabbr.org/sst
- YCombinator RFS: https://www.ycombinator.com/rfs/
- Ultralytics YOLOv8: https://docs.ultralytics.com/
- OSHA (Occupational Safety and Health Administration): https://www.osha.gov/
