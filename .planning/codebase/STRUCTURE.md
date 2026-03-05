# Codebase Structure

**Analysis Date:** 2026-03-05

## Directory Layout

```
vigilante-ai/
├── backend/                # Python FastAPI backend (AI detection + API)
│   ├── app/                # Application source code
│   │   ├── __init__.py     # Empty package marker
│   │   ├── main.py         # FastAPI app, routes, service wiring
│   │   ├── camera.py       # CameraManager - webcam capture
│   │   ├── detector.py     # SafetyDetector - YOLO inference
│   │   ├── stream.py       # StreamProcessor - pipeline orchestrator
│   │   ├── alerts.py       # AlertManager - alert storage & stats
│   │   ├── models.py       # Domain dataclasses (Detection, Alert)
│   │   ├── schemas.py      # Pydantic API response models
│   │   └── config.py       # Settings via pydantic-settings
│   ├── pyproject.toml      # Python project config & dependencies
│   └── requirements.txt    # Pip requirements (generated)
├── frontend/               # Next.js 14 TypeScript frontend
│   ├── src/
│   │   ├── app/            # Next.js App Router pages
│   │   │   ├── layout.tsx  # Root layout (header, nav, shell)
│   │   │   ├── page.tsx    # "/" - Monitoring page
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx # "/dashboard" - Stats dashboard
│   │   │   └── fonts/      # Local Geist font files
│   │   ├── components/     # React components
│   │   │   ├── VideoFeed.tsx       # MJPEG stream viewer
│   │   │   ├── AlertPanel.tsx      # Alert list with polling
│   │   │   ├── AlertCard.tsx       # Single alert display
│   │   │   ├── Controls.tsx        # Start/Stop stream buttons
│   │   │   ├── StatusBar.tsx       # Online/Offline + FPS indicator
│   │   │   ├── StatsCards.tsx      # Dashboard metric cards
│   │   │   └── ViolationsChart.tsx # Recharts timeline chart
│   │   ├── lib/
│   │   │   └── api.ts      # Backend API client functions
│   │   └── types/
│   │       └── index.ts    # TypeScript interfaces
│   ├── package.json        # Node dependencies
│   ├── tsconfig.json       # TypeScript config
│   ├── tailwind.config.ts  # Tailwind CSS config
│   ├── next.config.mjs     # Next.js config (standalone output)
│   └── next-env.d.ts       # Next.js type declarations
├── docs/                   # Project documentation (Portuguese)
│   ├── arquitetura-tecnica.md
│   └── documentacao-startup-one.md
├── tasks/                  # Product requirements
│   └── prd-vigilante-ai-mvp.md
├── scripts/                # Automation scripts
│   └── ralph/              # Ralph AI assistant config
│       ├── CLAUDE.md
│       ├── prd.json
│       ├── progress.txt
│       ├── prompt.md
│       └── ralph.sh
├── .planning/              # GSD planning documents
│   └── codebase/           # Codebase analysis (this file)
├── docker-compose.yml      # Container orchestration
├── .gitignore
├── progress.txt            # Development progress tracking
└── README.md               # Project overview
```

## Directory Purposes

**`backend/app/`:**
- Purpose: All backend Python source code
- Contains: Service classes, domain models, API schemas, configuration
- Key files: `main.py` (entry point), `stream.py` (core pipeline), `detector.py` (AI model)

**`frontend/src/app/`:**
- Purpose: Next.js App Router pages and layouts
- Contains: Page components and the root layout
- Key files: `layout.tsx` (shell), `page.tsx` (monitoring), `dashboard/page.tsx` (stats)

**`frontend/src/components/`:**
- Purpose: Reusable React UI components
- Contains: All client-side interactive components
- Key files: `VideoFeed.tsx`, `AlertPanel.tsx`, `Controls.tsx`

**`frontend/src/lib/`:**
- Purpose: Shared utilities and API client
- Contains: HTTP fetch wrappers
- Key files: `api.ts`

**`frontend/src/types/`:**
- Purpose: TypeScript type definitions
- Contains: Interfaces mirroring backend API response shapes
- Key files: `index.ts`

**`docs/`:**
- Purpose: Project documentation written in Portuguese
- Contains: Architecture docs, startup documentation

**`tasks/`:**
- Purpose: Product requirement documents
- Contains: MVP PRD

**`scripts/ralph/`:**
- Purpose: Ralph AI assistant configuration and scripts
- Contains: Prompt config, progress tracking, shell script

## Key File Locations

**Entry Points:**
- `backend/app/main.py`: FastAPI app creation, route definitions, `uvicorn.run()` for local dev
- `frontend/src/app/layout.tsx`: Next.js root layout with header navigation
- `frontend/src/app/page.tsx`: Monitoring page (home route `/`)
- `docker-compose.yml`: Container orchestration for both services

**Configuration:**
- `backend/app/config.py`: Backend settings (camera, model, CORS, alert cooldown)
- `backend/pyproject.toml`: Python dependencies and mypy config
- `frontend/package.json`: Node dependencies and scripts
- `frontend/tsconfig.json`: TypeScript compiler options (strict mode, `@/*` path alias)
- `frontend/tailwind.config.ts`: Tailwind content paths and theme
- `frontend/next.config.mjs`: Next.js standalone output mode

**Core Logic:**
- `backend/app/stream.py`: Central processing pipeline (camera -> detect -> alert -> encode)
- `backend/app/detector.py`: YOLO model inference and frame annotation
- `backend/app/alerts.py`: Alert storage, cooldown logic, stats computation
- `backend/app/camera.py`: Threaded webcam capture

**API Contract:**
- `backend/app/schemas.py`: Pydantic response models (source of truth for API shapes)
- `frontend/src/types/index.ts`: TypeScript mirrors of backend schemas
- `frontend/src/lib/api.ts`: Client-side fetch functions

**Testing:**
- No test files exist in the codebase

## Naming Conventions

**Files:**
- Backend Python: `snake_case.py` (e.g., `camera.py`, `detector.py`)
- Frontend Components: `PascalCase.tsx` (e.g., `VideoFeed.tsx`, `AlertPanel.tsx`)
- Frontend Utilities: `camelCase.ts` (e.g., `api.ts`)
- Frontend Pages: `page.tsx` (Next.js App Router convention)

**Directories:**
- All lowercase, single words (e.g., `components`, `lib`, `types`, `app`)
- Route directories match URL segments (e.g., `dashboard/`)

**Classes (Backend):**
- PascalCase with descriptive suffixes: `CameraManager`, `SafetyDetector`, `AlertManager`, `StreamProcessor`

**Interfaces (Frontend):**
- PascalCase: `Alert`, `SystemStatus`, `SessionStats`
- Props interfaces: `{ComponentName}Props` (e.g., `StatsCardsProps`, `ViolationsChartProps`)

## Where to Add New Code

**New Backend Endpoint:**
- Add route handler in `backend/app/main.py`
- Add response model in `backend/app/schemas.py`
- Add corresponding type in `frontend/src/types/index.ts`
- Add fetch function in `frontend/src/lib/api.ts`

**New Backend Service/Module:**
- Create file in `backend/app/` following `snake_case.py` naming
- Import and wire in `backend/app/main.py`

**New Frontend Page:**
- Create `frontend/src/app/{route}/page.tsx`
- Add navigation link in `frontend/src/app/layout.tsx`

**New Frontend Component:**
- Create `frontend/src/components/{ComponentName}.tsx` using PascalCase
- Mark as `"use client"` if it uses hooks or browser APIs

**New Domain Model:**
- Backend dataclass: add to `backend/app/models.py`
- API response schema: add to `backend/app/schemas.py`
- Frontend type: add to `frontend/src/types/index.ts`

**Utilities:**
- Backend: Create new module in `backend/app/`
- Frontend: Add to `frontend/src/lib/` or create new file in that directory

**Configuration:**
- Backend: Add field to `Settings` class in `backend/app/config.py` (env var with `VIGILANTE_` prefix)
- Frontend: Use `NEXT_PUBLIC_` prefixed env vars, reference in `frontend/src/lib/api.ts`

## Special Directories

**`backend/.venv/`:**
- Purpose: Python virtual environment
- Generated: Yes
- Committed: No (in `.gitignore`)

**`frontend/.next/`:**
- Purpose: Next.js build output
- Generated: Yes
- Committed: No (in `.gitignore`)

**`frontend/node_modules/`:**
- Purpose: Node.js dependencies
- Generated: Yes
- Committed: No (in `.gitignore`)

**`backend/.mypy_cache/`:**
- Purpose: mypy type checking cache
- Generated: Yes
- Committed: No

**`.planning/`:**
- Purpose: GSD planning and codebase analysis documents
- Generated: By tooling
- Committed: Yes

---

*Structure analysis: 2026-03-05*
