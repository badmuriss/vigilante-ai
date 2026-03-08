# Vigilante.AI 🛡️

Vigilante.AI is a real-time safety monitoring system powered by Computer Vision. It automatically detects Personal Protective Equipment (PPE) to ensure workplace safety and compliance.

## ✨ Features

- **Real-time PPE Detection**: Detects helmets, safety glasses, and other essential gear using YOLOv8.
- **Smart Violation Logic**: Integrated face detection (Haar Cascades) acts as a presence proxy to accurately flag missing equipment even when no gear is detected.
- **Performance Optimized**: Low-latency processing (640x480 resolution / 512px input) designed for CPU inference.
- **Interactive Dashboard**: Modern Next.js interface with real-time statistics, violation charts, and detailed alert history.
- **Stability Focused**: Reliable frame-based streaming refresh to prevent browser-side video hangs.

## 🏗️ Architecture

- **Backend**: Python 3.11+, FastAPI, OpenCV, YOLOv8 (Ultralytics).
- **Frontend**: Next.js 14 (App Router), Tailwind CSS, Radix UI, Recharts.
- **Deployment**: Docker and Docker Compose support.

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Webcam** (USB or Integrated)

### 🐋 Running with Docker

The easiest way to get started is using Docker Compose:

```bash
docker compose up --build
```

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000/docs](http://localhost:8000/docs)

> **Note**: To use your webcam inside a container on Linux, ensure the `devices` section in `docker-compose.yml` is uncommented.

### 🛠️ Manual Setup

#### Backend
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## ⚙️ Configuration

Environment variables (prefix `VIGILANTE_`):

| Variable | Default | Description |
|---|---|---|
| `VIGILANTE_CAMERA_INDEX` | `0` | System camera index. |
| `VIGILANTE_MODEL_PATH` | `best.pt` | Path to the trained YOLOv8 model. |
| `VIGILANTE_CONFIDENCE_THRESHOLD` | `0.5` | Minimum confidence for detections. |
| `VIGILANTE_CAMERA_WIDTH` | `640` | Capture width. |
| `VIGILANTE_CAMERA_HEIGHT` | `480` | Capture height. |

## 📡 API Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/status` | Current system state (FPS, Model, Camera). |
| `GET` | `/api/stream/frame` | Single frame JPEG endpoint for the frontend UI. |
| `GET` | `/api/alerts` | List of the last 50 safety violations. |
| `GET` | `/api/stats` | Session aggregate statistics. |

## 📊 Pages

- **Home (`/`)**: Real-time monitoring feed and active alerts.
- **Dashboard (`/dashboard`)**: Analytics, performance metrics, and historical trends.

---
*Built for safety. Engineered for performance.*
