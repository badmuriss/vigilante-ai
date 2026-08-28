# Plano — GPU on-demand inteligente (Opção A)

> Status: **planejado, não implementado.** Para o protótipo/apresentação roda
> tudo local via `docker compose` + `cloudflared tunnel` (ver "Fase 0"). Este
> doc descreve a evolução quando for pra valer.
>
> Este plano é uma peça do roadmap maior do TCC:
> [`docs/roadmap-tcc-outubro-2026.md`](./roadmap-tcc-outubro-2026.md).

## Problema

A parte pesada é a **inferência de visão** (`app/stream.py` + `app/detector.py`):
2 YOLO por frame × N câmeras, contínuo. CPU não tanca >~2 câmeras e VM GPU
sempre-ligada é cara. Quer GPU **on-demand** — liga só quando há streaming,
desliga (e para de cobrar) quando ocioso.

Não existe "wake-on-traffic" pra GPU com RTSP. A solução é um **control plane**
no VPS que liga/desliga o nó GPU via API do provider, guiado pelo estado das
câmeras.

## Comunicação nó↔VPS: TOKEN HTTP (não Tailscale)

O nó GPU é **efêmero** (sobe/morre por demanda). Tailscale nele é ruim: daemon +
TUN/NET_ADMIN no container, auth key na imagem, churn de device no tailnet a cada
cold start, +tempo de boot. E deixaria o Postgres alcançável pelo nó.

**Melhor: o nó é "burro" e fala SÓ com a API do VPS por HTTPS + bearer token.**
- Postgres **nunca** sai do VPS (não exposto, sem tailnet).
- O nó não tem credencial de DB nem de storage — só **1 token de serviço**.
- Usa o domínio que já tem TLS (Traefik/LE). Stateless, casa com nó efêmero.
- Rotação de token = trocar env nos 2 lados. Opcional: assinar corpo com HMAC.

## Topologia

```
  ┌──────────────────────────┐     HTTPS + Bearer token      ┌─────────────────────────┐
  │ VPS (sempre ligado)       │◄──────────────────────────────│ Nó GPU (on-demand)      │
  │  - frontend (Next)        │  GET /api/internal/cameras     │  - app/stream + detector│
  │  - API (FastAPI)          │  POST /api/internal/alerts     │  - puxa config (token)  │
  │  - Postgres (privado)     │  POST /api/internal/heartbeat  │  - manda alerta+jpeg    │
  │  - blob store (frames)    │                                │  - /health + /metrics   │
  │  - GPU Controller (novo)  │  ── provider API: start/stop ─►│    (token-protegido)    │
  │  - notifier WhatsApp      │                                └─────────────────────────┘
  └─────────────┬────────────┘
        domínio vigilanteai.outis.com.br (Dokploy + Traefik + LE)
```

- **VPS**: web + API + Postgres + blob store + Controller + notifier. Domínio público.
- **Nó GPU**: só inferência. Ligado por demanda. RunPod pod (recomendado para o TCC).
- **Link**: HTTPS autenticado por token. Sem tailnet, sem DB exposto.

## API interna (no VPS, prefixo `/api/internal`, auth = service token)

Dependency de auth separada do JWT de usuário (header `Authorization: Bearer <SERVICE_TOKEN>`):

- `GET /api/internal/cameras` → câmeras **ativas** que o nó deve transmitir
  (id, source_kind, rtsp_url, EPIs ativos, paletas). O nó faz poll (ex 15s) ou
  recebe via long-poll/SSE.
- `POST /api/internal/alerts` (multipart: JSON meta + jpeg thumb/full/raw) →
  o VPS faz o que o `AlertService.add_alert` faz hoje: dedup (`has_unreviewed`),
  `AlertRepository.create`, `blob_store.save_jpeg`, dispara push de revisão no
  WhatsApp. **A lógica de criação migra do nó pra cá** — o nó só detecta e envia.
- `POST /api/internal/heartbeat` → status/fps do nó; controller usa pra detectar crash.

Vantagem: frames (KB–~100KB, throttled por cooldown/has_unreviewed → poucos/min)
trafegam pela API sem problema. **Sem object storage separado** e **sem o nó ter
credencial de storage** — o blob store fica 100% no VPS (disco local ou R2 do
lado do VPS, transparente pro nó).

## GPU Controller (componente novo, no VPS)

Loop de reconciliação (estado desejado → real):

- **Desejado**: `nó ligado` se `count(câmeras ativas) > 0`.
- **Reconcile**:
  - desejado=ligado, nó=desligado → API do provider `start` → espera `healthy`.
  - desejado=desligado por > `IDLE_TIMEOUT` (ex 10–15min) → `stop` → $0.
- Estado em tabela `inference_node` (status, provider_pod_id, last_heartbeat_at, started_at).
- Status pra UI: `OFF → STARTING → ONLINE → STOPPING`.

Gatilhos:
- Usuário liga câmera / "iniciar monitoramento" → marca câmera ativa no DB → controller liga nó.
- Sem câmera ativa → timer ocioso → após timeout, desliga.
- Heartbeat perdido → controller religa / marca degradado.

Guard-rails de custo:
- `IDLE_TIMEOUT` (desliga ocioso).
- **Hard cap** de runtime por sessão (auto-stop após X h) — evita conta fugindo.
- Alerta se nó ligado sem câmera ativa (órfão).

Cold start: boot + driver + pull imagem + load modelo ≈ **30s–2min** (RunPod com
imagem cacheada em network volume é mais rápido; GCP ~1–2min). UI mostra
"iniciando inferência…"; botão **pré-aquecer** antes de demo.

## Nó GPU — boot sequence

1. Pull da imagem **CUDA** (torch cu12 — venv de dev já tem; imagem atual é CPU).
   Cachear em network volume (RunPod) p/ acelerar.
2. `GET /api/internal/cameras` (com token) → lista de câmeras ativas.
3. Inicia streams (reusa `registry`/`StreamProcessor`), mas o `AlertService` do
   nó vira um **client HTTP** que faz `POST /api/internal/alerts` em vez de
   escrever no DB/disco local.
4. Expõe `/health` + `/metrics` (token-protegido). Manda heartbeat periódico.
5. Entrypoint **só inferência** (sem montar routers de web/API/chat).

## Decoupling necessário (o "split")

1. **API interna no VPS**: `GET /cameras`, `POST /alerts` (multipart), `heartbeat`
   sob `require_service_token`. Move a lógica de `AlertService.add_alert` pra trás
   do `POST /alerts`.
2. **AlertService client no nó**: mesma interface `add_alert(...)`, mas em vez de
   DB+disco faz HTTP autenticado pro VPS. Plugado no `StreamProcessor` sem mudar
   o loop de detecção.
3. **Service token**: `VIGILANTE_INFERENCE_TOKEN` (env nos 2 lados); dependency de
   auth dedicada (não o JWT de usuário). HTTPS only; opcional HMAC do corpo + rate limit.
4. **Provider control**: módulo controller usando API do RunPod (ou gcloud) start/stop.
5. **Entrypoint só-inferência** + **flag de câmera ativa** no DB (API/controller gerencia).
6. (Opcional v2) live MJPEG: nó expõe via seu próprio tunnel token-protegido, ou
   pula no v1 (preview ao vivo cross-node degradado).

Fica **inalterado** no VPS: notifier WhatsApp/Teams, RAG/chat, auth, blob store.
Postgres e storage permanecem privados ao VPS.

## Provider

- **RunPod (recomendado para o TCC)**: API REST p/ create/start/stop pod, billing **por
  segundo**, network volume cacheia imagem+modelos (cold start ~30–60s). Crédito
  pré-pago, sem validade. 3090 ~$0.2/h, 4090 ~$0.4/h.
- **GCP/AWS GPU (alternativas)**: úteis se créditos cobrirem a demo, mas com mais
  burocracia operacional. Não devem ser dependência crítica da apresentação.

## Fluxo de dados (ponta a ponta)

```
RTSP → nó GPU (detect) → POST /api/internal/alerts {meta + jpeg} (token, HTTPS)
     → VPS: dedup + cria Alert + salva frame + dispara push de revisão no WhatsApp
     → operador toca botão (Confirmar/Falso positivo) → feedback no DB
```

## Failure modes

- **Crash do nó** → heartbeat perdido → controller religa / marca degradado.
- **Falha ao ligar** (sem capacidade GPU) → retry / outra região / erro na UI.
- **VPS/rede indisponível** → nó faz buffer dos alertas + retry com backoff; se
  estourar, descarta os mais antigos (alerta é throttled, perda limitada).
- **Token vazado** → rotaciona env nos 2 lados; HTTPS + (opcional) HMAC + rate limit reduzem risco.
- **Preempção** (se spot) → controller religa; **demo ao vivo usa on-demand não-spot**.

## Fases

- **Fase 0 (agora — apresentação)**: tudo local, `docker compose up` +
  `cloudflared tunnel --url http://localhost:8000` p/ o webhook Meta. **Nada a construir.**
- **Fase 1 — split**: API interna (`/cameras`, `/alerts`, `/heartbeat`) +
  `AlertService` client no nó + service token. Roda o container de inferência
  **manualmente** num pod GPU (start/stop na mão).
- **Fase 2 — controller**: auto start/stop por câmera ativa + idle timeout +
  status na UI + entrypoint só-inferência.
- **Fase 3 — hardening**: HMAC no corpo, hard cap de runtime, multi-nó por nº de
  câmeras (node-per-site), pré-aquecer, live MJPEG.

## Decisões em aberto

- RunPod manual vs RunPod controlado automaticamente pelo VPS.
- Frame pela API (simples, escolhido) vs object storage direto (só se volume crescer).
- 1 nó pra todas as câmeras vs nó-por-site (escala) → quando multi-nó, atribuição câmera→nó.
- Poll vs SSE pra o nó receber mudanças de câmera.

## Imagem CUDA (pré-requisito da Fase 1)

A imagem do backend hoje é CPU (`python:3.11-slim`, sem CUDA). Pro nó GPU:
`Dockerfile.gpu` com base CUDA + torch cu12 + ultralytics (autodetecta GPU, sem
mudar `detector.py`). VPS continua CPU.
