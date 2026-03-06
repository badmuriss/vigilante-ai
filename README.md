# Vigilante.AI

Sistema de seguranca do trabalho com visao computacional. Detecta EPIs (oculos de protecao e capacete) via webcam usando YOLOv8, exibe alertas visuais em tempo real.

## Arquitetura

- **Backend**: Python + FastAPI + OpenCV + YOLOv8 (Ultralytics)
- **Frontend**: Next.js 14 (App Router) + Tailwind CSS + Recharts

## Pre-requisitos

- Python 3.11+
- Node.js 18+
- Webcam conectada

## Docker

Para rodar tudo com Docker:

```bash
docker compose up --build
```

- Frontend: `http://localhost:3000`
- Backend/API: `http://localhost:8000/docs`

Para usar a webcam no container, descomente a secao `devices` no `docker-compose.yml`:

```yaml
devices:
  - /dev/video0:/dev/video0
```

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

O servidor inicia em `http://localhost:8000`. Documentacao da API em `/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

O frontend inicia em `http://localhost:3000`.

## Configuracao

Variaveis de ambiente (prefixo `VIGILANTE_`):

| Variavel | Padrao | Descricao |
|---|---|---|
| `VIGILANTE_CAMERA_INDEX` | `0` | Indice da webcam |
| `VIGILANTE_MODEL_PATH` | `yolov8n.pt` | Caminho do modelo YOLO |
| `VIGILANTE_CONFIDENCE_THRESHOLD` | `0.5` | Confianca minima para deteccao |
| `VIGILANTE_ALERT_COOLDOWN_SECONDS` | `10` | Cooldown entre alertas duplicados |
| `VIGILANTE_PORT` | `8000` | Porta do backend |

## API

| Metodo | Endpoint | Descricao |
|---|---|---|
| `GET` | `/api/status` | Status do sistema (camera, modelo, FPS) |
| `GET` | `/api/stream` | Stream MJPEG com deteccoes |
| `POST` | `/api/stream/start` | Iniciar monitoramento |
| `POST` | `/api/stream/stop` | Parar monitoramento |
| `GET` | `/api/alerts` | Lista de alertas recentes (max 50) |
| `DELETE` | `/api/alerts` | Limpar alertas |
| `GET` | `/api/stats` | Estatisticas da sessao |

## Paginas

- **/** - Monitoramento: feed de video ao vivo + painel de alertas
- **/dashboard** - Dashboard com estatisticas e grafico de violacoes
