# Design Atual - Vigilante.ai

## Estrutura Geral

O Vigilante.ai atualmente e um painel operacional (nao uma landing page de downloads), com foco em monitoramento de seguranca em tempo real e analise da sessao.

- Header com identidade do produto e navegacao:
  - `Monitor`
  - `Dashboard`
- Conteudo principal dividido em duas paginas:
  - Pagina `Monitor` (`/`)
  - Pagina `Dashboard` (`/dashboard`)

## Secoes da Pagina Monitor

### 1. Cabecalho operacional
- Eyebrow: `Centro de monitoramento`
- Titulo principal de operacao em tempo real
- Texto de apoio sobre feed/processamento/incidentes
- Barra de status com chips:
  - Estado: `Parado`, `Inicializando`, `Monitorando`
  - Modelo: `Modelo pronto` ou `Modelo pendente`
  - Performance: `FPS` ou `Aguardando feed`

### 2. Controles de monitoramento
- Botao primario: `Iniciar`
  - Estado intermediario: `Iniciando...`
- Botao secundario: `Parar`
- Feedback de erro quando camera/backend nao respondem

### 3. Secao de video
- Titulo: `Camera operacional`
- Badge de contexto: `Feed em tempo real`
- Estados visuais:
  - Camera pronta para iniciar
  - Carregando stream
  - Erro ao carregar feed
  - Stream ao vivo

### 4. Configuracao de EPIs
- Titulo: `EPIs monitorados`
- Lista de toggles (checkboxes) por EPI
- Atualizacao em tempo real da configuracao ativa
- Mensagem de erro em caso de falha na atualizacao

### 5. Painel de alertas
- Titulo: `Alertas recentes`
- Contador de alertas ativos
- Acoes disponiveis:
  - Ativar/desativar som das notificacoes
  - `Limpar` alertas
- Lista de cards de alerta com:
  - Miniatura (quando disponivel)
  - Tipo de violacao
  - EPIs ausentes
  - Horario
  - Confianca (%)
  - Indicacao `Ver detalhes`

### 6. Modal de detalhes do alerta
- Exibicao da imagem do registro
- Lista de EPIs faltantes
- Momento exato do registro
- Sinal de deteccao (percentual de confianca)
- Botao de fechar

## Secoes da Pagina Dashboard

### 1. Resumo
- Eyebrow: `Resumo`
- Titulo: `Dashboard operacional`
- Texto de apoio sobre consolidacao da sessao

### 2. Cards de metricas
- `Total de violacoes`
- `Tempo de monitoramento`

### 3. Grafico historico
- Titulo: `Violacoes ao longo do tempo`
- Linha temporal com contagem por horario
- Estado vazio: `Sem dados de violacoes ainda`

## Direcao Visual (ajustada)

### Cores
- Fundo: claro/neutro com gradientes suaves
- Texto principal: grafite escuro
- Texto secundario: cinza medio
- Destaque principal: **azul escuro** (substitui verde neon)
  - Uso: botoes primarios, foco de status, elementos de acao
- Cores de apoio:
  - Alerta/erro: vermelho
  - Estados neutros: cinzas e off-white

### Tipografia
- Fonte principal ja adotada: Geist Sans
- Hierarquia com headings fortes e texto de apoio legivel
- Labels em uppercase para contextos operacionais (eyebrow/chips)

### Componentes e Comportamento
- Cards com bordas suaves e blur leve
- Botoes arredondados com feedback de hover/disabled
- Modais com foco em inspeção rapida
- Chips de status para leitura imediata

## Responsividade

- Layout mobile-first
- `Monitor` em uma coluna no mobile e duas colunas no desktop (feed + alertas)
- Navegacao superior adaptavel para telas menores
- Cards, painel de alertas e grafico mantem legibilidade em diferentes larguras

## Elementos Interativos Atuais

- Navegacao entre `Monitor` e `Dashboard`
- Acao de iniciar/parar monitoramento
- Polling automatico de status, alertas e metricas
- Toggling de EPIs monitorados
- Abertura de modal ao clicar em alerta
- Limpeza de alertas
