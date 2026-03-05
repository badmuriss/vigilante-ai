# Vigilante.AI - Arquitetura Técnica

## Visão Geral

```
vigilante-ai/
├── backend/                  # Python FastAPI
│   ├── app/
│   │   ├── main.py          # Entry point FastAPI
│   │   ├── config.py        # Configurações (câmera, modelo, thresholds)
│   │   ├── detector.py      # Classe de detecção YOLO
│   │   ├── camera.py        # Captura de webcam via OpenCV
│   │   ├── stream.py        # MJPEG streaming endpoint
│   │   ├── alerts.py        # Gerenciamento de alertas in-memory
│   │   └── routes/
│   │       ├── stream.py    # Rotas de stream
│   │       ├── alerts.py    # Rotas de alertas
│   │       └── status.py    # Rotas de status
│   ├── models/              # Pesos do modelo YOLO
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/                 # Next.js 14 + React
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx     # Página de monitoramento
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx # Dashboard de estatísticas
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── video-feed.tsx
│   │   │   ├── alert-panel.tsx
│   │   │   ├── alert-card.tsx
│   │   │   ├── status-bar.tsx
│   │   │   ├── controls.tsx
│   │   │   └── dashboard/
│   │   │       ├── stats-cards.tsx
│   │   │       └── violations-chart.tsx
│   │   ├── hooks/
│   │   │   ├── use-alerts.ts
│   │   │   └── use-stream-status.ts
│   │   ├── lib/
│   │   │   └── api.ts       # Cliente HTTP para o backend
│   │   └── types/
│   │       └── index.ts     # Tipos compartilhados
│   ├── package.json
│   ├── tailwind.config.ts
│   └── tsconfig.json
├── docs/                     # Documentação
├── tasks/                    # PRDs
└── README.md
```

## Stack Tecnológica

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Backend | Python 3.11+ / FastAPI | Ecossistema maduro para CV, async nativo, auto-docs |
| Visão Computacional | YOLOv8 (ultralytics) | SOTA em detecção de objetos, fácil de usar, leve |
| Captura de Vídeo | OpenCV (cv2) | Padrão da indústria, suporte a webcam e RTSP |
| Frontend | Next.js 14 + React 18 | SSR, App Router, ecossistema rico |
| Styling | Tailwind CSS 3 | Rápido para prototipação, design system consistente |
| Gráficos | Recharts | Leve, React-nativo, suficiente para dashboard |

## Fluxo de Dados

```
1. Webcam captura frame (OpenCV VideoCapture)
         |
2. Frame enviado ao modelo YOLO (ultralytics predict)
         |
3. Resultado: lista de detecções [{class, confidence, bbox}]
         |
    ┌────┴────┐
    |         |
4a. Frame anotado       4b. Se violação detectada:
    com bounding boxes       - Cria objeto Alert
    (cv2.rectangle)          - Adiciona à lista in-memory
    |                        - Disponibiliza via GET /api/alerts
    |
5. Frame anotado encodado como JPEG
         |
6. Enviado via MJPEG stream (multipart/x-mixed-replace)
         |
7. Frontend exibe <img src="/api/stream"> + polling /api/alerts
```

## API Endpoints

### Stream
| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/stream` | Stream MJPEG do vídeo anotado |
| POST | `/api/stream/start` | Inicia captura da webcam |
| POST | `/api/stream/stop` | Para captura da webcam |

### Alertas
| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/alerts` | Lista últimos 50 alertas |
| DELETE | `/api/alerts` | Limpa todos os alertas |

### Status
| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/status` | Status do sistema (webcam, modelo, FPS, uptime) |
| GET | `/api/stats` | Estatísticas da sessão (total violações, taxa conformidade) |

## Modelo de Dados (In-Memory)

```python
@dataclass
class Detection:
    class_name: str        # "safety_glasses" | "no_safety_glasses" | "hardhat" | "no_hardhat" | "person"
    confidence: float      # 0.0 - 1.0
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2

@dataclass
class Alert:
    id: str                # UUID
    timestamp: datetime
    violation_type: str    # "no_safety_glasses" | "no_hardhat"
    confidence: float
    frame_thumbnail: str   # Base64 JPEG do frame capturado
    bbox: tuple[int, int, int, int]

@dataclass
class SessionStats:
    start_time: datetime
    total_frames: int
    total_violations: int
    violations_timeline: list[tuple[datetime, int]]  # (timestamp, count) por minuto
```

## Configurações

```python
# config.py
class Settings:
    # Câmera
    CAMERA_INDEX: int = 0           # 0 = webcam padrão
    CAMERA_WIDTH: int = 640
    CAMERA_HEIGHT: int = 480
    TARGET_FPS: int = 15

    # Modelo
    MODEL_PATH: str = "models/best.pt"  # Pesos YOLO
    CONFIDENCE_THRESHOLD: float = 0.5
    IOU_THRESHOLD: float = 0.45

    # Alertas
    MAX_ALERTS: int = 50
    ALERT_COOLDOWN_SECONDS: int = 5  # Evitar spam de alertas

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
```

## Decisões de Arquitetura

### 1. MJPEG vs WebSocket para vídeo
**Decisão:** MJPEG
**Motivo:** Mais simples de implementar, funciona com uma tag `<img>` no frontend, não requer lógica de reconexão. WebSocket seria necessário para latência < 100ms, que não é requisito do MVP.

### 2. Polling vs WebSocket para alertas
**Decisão:** Polling (GET /api/alerts a cada 2 segundos)
**Motivo:** Simplicidade. Com 50 alertas max e JSON leve, o overhead é negligível. WebSocket pode ser adicionado depois se necessário.

### 3. In-memory vs banco de dados
**Decisão:** In-memory (lista Python)
**Motivo:** MVP não precisa de persistência entre sessões. Elimina dependência externa e simplifica setup.

### 4. Modelo pré-treinado vs fine-tuning
**Decisão:** Começar com modelo pré-treinado de dataset público, fazer fine-tuning se necessário.
**Motivo:** Reduz tempo de desenvolvimento. Datasets de EPIs existem no Roboflow Universe. Fine-tuning só se a accuracy for insuficiente.

## Requisitos de Sistema

### Mínimos (para demo)
- CPU: Intel i5 / AMD Ryzen 5 (ou equivalente)
- RAM: 8 GB
- Webcam: Qualquer webcam USB ou integrada
- OS: Windows 10+, macOS 12+, ou Linux (Ubuntu 22.04+)
- Python: 3.11+
- Node.js: 18+

### Recomendados
- GPU: NVIDIA com CUDA (acelera inferência 5-10x)
- RAM: 16 GB
- Webcam: 720p ou superior
