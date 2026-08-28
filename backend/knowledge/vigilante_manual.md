# Manual do Vigilante.AI

O Vigilante.AI é uma plataforma de visão computacional que monitora o uso de
EPI (Equipamento de Proteção Individual) em ambientes de trabalho. O produto
está iniciando pelo nicho de construção civil, mas foi desenhado para segurança
do trabalho em geral, incluindo obras, indústrias, galpões, áreas logísticas e
frentes operacionais. Conecta-se a câmeras existentes via RTSP ou webcam local,
detecta automaticamente quem está sem capacete ou colete, e avisa o responsável
com a imagem do flagrante.

## Escopo de segurança do trabalho

O Vigilante.AI não é um sistema exclusivo para obras. Construção civil é o
primeiro caso de uso porque o risco operacional e a exigência de EPI são muito
visíveis nesse contexto, mas os conceitos centrais da plataforma são de SST
geral: monitorar conformidade, registrar evidências, apoiar ação corretiva e
reduzir exposição a riscos.

A base de conhecimento inicial contém material sobre NR-6 e NR-18. A NR-6 vale
para EPI de forma ampla. A NR-18 deve ser usada quando a pergunta envolver
construção civil, canteiro de obra ou frente de trabalho da construção.

## Cadastrar uma câmera

1. Acesse a página **Câmeras** no menu lateral.
2. Clique em **Adicionar câmera**.
3. Escolha o tipo de fonte (`source_kind`):
   - **rtsp**: câmera IP. Informe a `rtsp_url` no formato
     `rtsp://usuario:senha@ip:554/stream`.
   - **local**: webcam conectada ao servidor. Informe o índice do dispositivo
     (`local_index`, geralmente 0).
4. Dê um nome e, opcionalmente, a localização (ex: "Portão 3 - entrada").
5. Clique em **Salvar**. A câmera aparece no grid.
6. Use o botão **Iniciar** para começar o processamento do stream.

Cada câmera roda um worker independente com reconexão automática. Se o stream
cair, o Vigilante.AI tenta reconectar sozinho e registra o evento.

## Testar uma URL RTSP antes de cadastrar

Na tela de adicionar câmera há o botão **Testar conexão** (`probe`). Ele tenta
abrir o stream por alguns segundos e informa se a URL é válida. Use isso para
evitar cadastrar câmeras com credenciais erradas.

## Simulador RTSP para desenvolvimento

Sem câmeras IP reais? Coloque vídeos `.mp4` na pasta `media/` e suba o stack com
`docker compose --profile rtsp up -d`. Cada arquivo vira um stream
`rtsp://mediamtx:8554/<nome-do-arquivo-sem-extensao>`.

## Tipos de violação detectados

O modelo experimental usa YOLOv8s fine-tunado. O mAP@0.5 de 0,944 pertence a uma divisão de validação com vazamento entre vídeos e não comprova desempenho em canteiro. Cada câmera precisa de calibração e validação antes de uso comercial. O sistema detecta por pessoa:

- **sem_capacete**: trabalhador sem capacete de proteção.
- **sem_colete**: trabalhador sem colete de alta visibilidade.

A detecção é por pessoa, não por cena — um capacete na imagem não "cobre" todos
os trabalhadores no quadro. Cada pessoa é avaliada individualmente.

## Revisar alertas (feedback)

Os alertas chegam como **soft alerts** (pendentes de revisão). Um revisor
(papel admin ou supervisor) confirma ou rejeita cada alerta:

- **Confirmar** (correto): registra como incidente real. Dispara notificação
  WhatsApp/Teams se configurado e gera amostra para retreino.
- **Rejeitar** (falso positivo): o modelo errou. Gera amostra negativa para
  o ciclo de active learning.

Enquanto um alerta de uma câmera + tipo de violação está pendente, o sistema
suprime novos alertas idênticos para não inundar a fila de revisão.

## Papéis de usuário

- **admin**: acesso total, configura integrações e gerencia usuários.
- **supervisor**: revisa alertas (confirma/rejeita), vê alertas pendentes.
- **viewer**: vê apenas o feed de alertas confirmados, sem poder revisar.

O primeiro usuário registrado vira admin do tenant (registro aberto).

## Histórico de alertas

A página **Histórico** lista alertas filtrados por período, câmera e tipo de
violação. Clique em um alerta para ver a imagem do flagrante e os detalhes
(confiança do modelo, EPIs ausentes, horário).

## Relatórios

A página **Relatórios** mostra gráficos de barras de violações por dia,
permite exportar PDF e abrir um modal de alertas diários. Útil para
auditorias e prestação de contas de segurança do trabalho.

## Configurar notificações WhatsApp

A plataforma usa **um único número WhatsApp**, compartilhado por todas as
organizações. As credenciais Meta (número, token, app secret, verify token e
template) ficam no servidor (variáveis de ambiente) e são configuradas pelo
operador da plataforma — você **não** preenche credenciais na interface.

Em **Configurações** → card **WhatsApp Business** o admin do tenant gerencia
apenas:

1. **Operadores**: telefones no formato E.164 (ex: `+5511999999999`), com nome
   opcional. Cada operador recebe os alertas confirmados e pode conversar com o
   assistente pelo WhatsApp em nome da organização. Um número pertence a uma
   única organização.
2. **Anexar imagem**: incluir ou não a foto do frame do alerta na mensagem.
3. **Ativar** as notificações e salvar. Use **Testar** para um envio de teste.

O card mostra **Plataforma conectada** quando o número global está configurado
no servidor. Se aparecer aviso de credenciais ausentes, o operador da
plataforma precisa preencher as variáveis `VIGILANTE_WHATSAPP_*` no servidor.

## Assistente conversacional via WhatsApp (inbound)

Além de enviar alertas, o Vigilante.AI recebe perguntas via WhatsApp pelo mesmo
número único. A organização do remetente é identificada pelo **telefone do
operador** cadastrado — por isso cada operador pertence a um só tenant. Não há
configuração de webhook por organização: o verify token e o app secret são
globais (servidor). Qualquer operador cadastrado pode mandar perguntas e o
assistente responde com base na mesma base de conhecimento e nos mesmos dados
operacionais da interface web.

## Configurar notificações Microsoft Teams

Em **Configurações** → card **Microsoft Teams**: cole a URL do webhook gerada
por um fluxo do Teams Workflows / Power Automate. A URL é secreta e fica
criptografada. Marque **Notificar em confirmados** para receber card no Teams
quando um alerta for confirmado.

## Assistente Vigilante.AI

A página **Assistente** e o widget flutuante de chat permitem perguntar em
linguagem natural sobre a operação. Exemplos:

- "Quantos alertas tive hoje?"
- "Qual câmera flagra mais violações esta semana?"
- "O que diz a NR-6 sobre fornecimento de EPI?"
- "Como cadastro uma câmera RTSP?"

O assistente consulta a base de conhecimento (este manual + normas) e os dados
ao vivo do banco (alertas, câmeras) para responder.
