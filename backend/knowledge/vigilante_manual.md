# Manual do Vigilante.AI

O Vigilante.AI é uma plataforma de visão computacional que monitora o uso de
EPI (Equipamento de Proteção Individual) em obras e indústrias. Conecta-se a
câmeras existentes via RTSP ou webcam local, detecta automaticamente quem está
sem capacete ou colete, e avisa o responsável com a imagem do flagrante.

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

O modelo (YOLOv8s fine-tunado, mAP@0.5 = 0.944) detecta por pessoa:

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

Em **Configurações** → card **WhatsApp Business**:

1. Informe o `phone_number_id` (numérico, 15 dígitos, vem do Meta Cloud API).
2. Cole o `access_token` (token de sistema com permissão
   `whatsapp_business_messaging`).
3. Defina o `template_name` (template pré-aprovado pela Meta) e o idioma.
4. Adicione os destinatários no formato E.164 (ex: `+5511999999999`).
5. Marque **Ativar** e salve. Use **Testar** para enviar uma mensagem de teste.

O token é criptografado em repouso com Fernet — nunca fica em texto puro.

## Configurar o assistente conversacional via WhatsApp (inbound)

Além de enviar alertas, o Vigilante.AI recebe perguntas via WhatsApp. No mesmo
card preencha:

- `webhook_verify_token`: um token qualquer que você define, usado pela Meta
  para validar o webhook.
- `app_secret`: o App Secret do seu app Meta, usado para verificar a assinatura
  HMAC de cada mensagem recebida.

Depois, no Meta Developer Console, configure a Webhook URL apontando para
`https://seu-dominio/api/webhooks/whatsapp`, com o mesmo verify token, e
inscreva o campo `messages`. A partir daí, qualquer pessoa autorizada pode
mandar perguntas pelo WhatsApp e o assistente responde com base na mesma base
de conhecimento e nos mesmos dados operacionais da interface web.

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
