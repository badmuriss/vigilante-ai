# Technology Stack

**Analysis Date:** 2026-03-05

## Languages

**Primary:**
- TypeScript ^5 - Frontend (`frontend/src/`)
- Python >=3.11 - Backend (`backend/app/`)

**Secondary:**
- CSS (Tailwind) - Styling (`frontend/src/app/globals.css`)

## Runtime

**Environment:**
- Node.js 18 (Alpine) - Frontend runtime (specified in `frontend/Dockerfile`)
- Python 3.11 (slim) - Backend runtime (specified in `backend/Dockerfile`)

**Package Manager:**
- npm - Frontend (`frontend/package-lock.json` present)
- pip - Backend (`backend/requirements.txt`)

## Frameworks

**Core:**
- Next.js 14.2.35 - Frontend React framework (`frontend/package.json`)
  - Uses App Router (`frontend/src/app/`)
  - Standalone output mode (`frontend/next.config.mjs`: `output: "standalone"`)
- FastAPI >=0.109.0 - Backend REST API (`backend/app/main.py`)
- React ^18 - UI library (`frontend/package.json`)

**ML/CV:**
- Ultralytics (YOLOv8) >=8.1.0 - Object detection model (`backend/app/detector.py`)
- OpenCV (headless) >=4.9.0 - Video capture and image processing (`backend/app/camera.py`, `backend/app/stream.py`)

**Testing:**
- Not detected - No test framework configured in either frontend or backend

**Build/Dev:**
- Tailwind CSS ^3.4.1 - Utility-first CSS (`frontend/tailwind.config.ts`)
- PostCSS ^8 - CSS processing (`frontend/postcss.config.mjs`)
- ESLint ^8 with `next/core-web-vitals` and `next/typescript` (`frontend/.eslintrc.json`)
- mypy (strict mode) - Python type checking (`backend/pyproject.toml`)
- Docker + Docker Compose - Containerization (`docker-compose.yml`)

## Key Dependencies

**Critical:**
- `ultralytics` >=8.1.0 - YOLOv8 model loading and inference (`backend/app/detector.py`)
- `opencv-python-headless` >=4.9.0 - Camera capture, frame encoding, annotation drawing (`backend/app/camera.py`, `backend/app/detector.py`, `backend/app/stream.py`)
- `fastapi` >=0.109.0 - HTTP API and MJPEG streaming (`backend/app/main.py`)
- `next` 14.2.35 - Frontend framework and SSR (`frontend/package.json`)
- `recharts` ^3.7.0 - Dashboard chart visualization (`frontend/src/components/ViolationsChart.tsx`)

**Infrastructure:**
- `uvicorn` >=0.27.0 - ASGI server for FastAPI (`backend/Dockerfile`)
- `pydantic-settings` >=2.1.0 - Environment-based configuration (`backend/app/config.py`)
- `python-multipart` >=0.0.6 - Multipart form data support (`backend/requirements.txt`)
- `numpy` - Transitive via OpenCV/Ultralytics, used directly for frame typing (`backend/app/detector.py`)

## Configuration

**Environment:**
- Frontend: `NEXT_PUBLIC_API_URL` - Backend API base URL (defaults to `http://localhost:8000`)
- Backend: All settings prefixed with `VIGILANTE_` via pydantic-settings (`backend/app/config.py`)
  - `VIGILANTE_CAMERA_INDEX` (default: 0) - Webcam device index
  - `VIGILANTE_MODEL_PATH` (default: `yolov8n.pt`) - YOLO model weights file
  - `VIGILANTE_CONFIDENCE_THRESHOLD` (default: 0.5) - Detection confidence threshold
  - `VIGILANTE_CORS_ORIGINS` (default: `["http://localhost:3000"]`) - Allowed CORS origins
  - `VIGILANTE_HOST` (default: `0.0.0.0`) - Server bind host
  - `VIGILANTE_PORT` (default: 8000) - Server bind port
  - `VIGILANTE_ALERT_COOLDOWN_SECONDS` (default: 10) - Minimum time between duplicate alerts
  - `VIGILANTE_CAMERA_WIDTH` (default: 640) - Camera capture width
  - `VIGILANTE_CAMERA_HEIGHT` (default: 480) - Camera capture height

**Build:**
- `frontend/next.config.mjs` - Next.js standalone build output
- `frontend/tsconfig.json` - TypeScript strict mode, `@/*` path alias to `./src/*`
- `frontend/tailwind.config.ts` - Tailwind with CSS variable-based colors
- `frontend/.eslintrc.json` - ESLint extends `next/core-web-vitals`, `next/typescript`
- `backend/pyproject.toml` - mypy strict mode with pydantic plugin

**Docker:**
- `docker-compose.yml` - Orchestrates backend (port 8000) and frontend (port 3000)
- `frontend/Dockerfile` - Multi-stage Node 18 Alpine build (deps -> build -> runner)
- `backend/Dockerfile` - Python 3.11 slim with OpenGL/GLib system deps

## Platform Requirements

**Development:**
- Node.js 18+ for frontend
- Python 3.11+ for backend
- Webcam device (optional - camera index configurable)
- YOLO model weights file (`yolov8n.pt` included in backend root)

**Production:**
- Docker and Docker Compose
- Webcam device passthrough (via Docker device mapping, commented out by default)
- No external database required (all state is in-memory)

---

*Stack analysis: 2026-03-05*
