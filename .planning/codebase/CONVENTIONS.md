# Coding Conventions

**Analysis Date:** 2026-03-05

## Languages

This is a bilingual codebase: **TypeScript** (frontend) and **Python** (backend). UI text is in **Brazilian Portuguese (pt-BR)**. Code identifiers (variables, functions, classes) are in **English**. Comments are minimal and in English.

## Naming Patterns

**Files (Frontend):**
- Components: PascalCase — `AlertCard.tsx`, `VideoFeed.tsx`, `StatsCards.tsx`
- Pages: lowercase `page.tsx` inside route directories (Next.js App Router convention)
- Library modules: camelCase — `api.ts`
- Type definitions: `index.ts` barrel file in `types/` directory

**Files (Backend):**
- Python modules: snake_case — `alert_manager.py`, `stream.py`, `detector.py`
- Single `__init__.py` in `app/` (empty)

**Functions (Frontend):**
- React components: PascalCase — `AlertCard`, `DashboardPage`, `VideoFeed`
- Helper functions: camelCase — `formatTimestamp`, `formatDuration`, `formatTime`
- API functions: camelCase verbs — `getStatus`, `getAlerts`, `clearAlerts`, `startStream`
- Event handlers: `handle` prefix — `handleStart`, `handleStop`, `handleClear`

**Functions (Backend):**
- Endpoint functions: snake_case — `get_status`, `get_alerts`, `clear_alerts`
- Class methods: snake_case with underscore prefix for private — `_capture_loop`, `_is_on_cooldown`, `_make_thumbnail`

**Variables (Frontend):**
- Local state: camelCase — `hasError`, `soundEnabled`, `prevCountRef`
- Constants: UPPER_SNAKE_CASE — `STREAM_URL`, `VIOLATION_LABELS`
- Refs: camelCase with `Ref` suffix — `prevCountRef`, `audioRef`

**Variables (Backend):**
- Constants: UPPER_SNAKE_CASE — `PPE_CLASSES`, `VIOLATION_CLASSES`, `GREEN`, `RED`
- Instance variables: underscore prefix for private — `self._model`, `self._running`, `self._lock`
- Settings: UPPER_SNAKE_CASE in `Settings` class — `CAMERA_INDEX`, `CONFIDENCE_THRESHOLD`

**Types (Frontend):**
- Interfaces: PascalCase with descriptive names — `SessionStats`, `SystemStatus`, `Alert`
- Props interfaces: ComponentName + `Props` suffix — `StatsCardsProps`, `ViolationsChartProps`
- Union types: PascalCase — `ViolationType`

**Types (Backend):**
- Pydantic models: PascalCase with `Response` suffix for API schemas — `AlertResponse`, `StatsResponse`, `ClearAlertsResponse`
- Dataclasses: PascalCase — `Detection`, `Alert`

## Code Style

**Formatting (Frontend):**
- No dedicated Prettier config — relies on ESLint defaults via `eslint-config-next`
- Double quotes for JSX attributes and imports
- Semicolons at end of statements
- 2-space indentation (TypeScript standard)
- Trailing commas used

**Formatting (Backend):**
- No explicit formatter configured (no `black`, `ruff`, or `isort` in dependencies)
- 4-space indentation (Python standard)
- `from __future__ import annotations` used at top of all modules for modern type syntax
- Line length appears to be ~100 characters

**Linting (Frontend):**
- ESLint with `next/core-web-vitals` and `next/typescript` presets
- Config: `frontend/.eslintrc.json`
- Run via: `npm run lint` (which calls `next lint`)

**Linting (Backend):**
- MyPy configured in `backend/pyproject.toml` with `strict = true`
- Pydantic MyPy plugin enabled with `init_forbid_extra`, `init_typed`, `warn_required_dynamic_aliases`
- No runtime linter (no `ruff` or `flake8`) in dependencies

## Import Organization

**Frontend (TypeScript):**
1. React/Next.js built-ins — `import { useState } from "react"`, `import Link from "next/link"`
2. Type imports with `import type` syntax — `import type { Alert } from "@/types"`
3. Internal modules via path alias — `import { getAlerts } from "@/lib/api"`
4. Relative imports for sibling components — `import AlertCard from "./AlertCard"`

**Path Aliases:**
- `@/*` maps to `./src/*` (configured in `frontend/tsconfig.json`)

**Backend (Python):**
1. `from __future__ import annotations` (always first)
2. Standard library — `import logging`, `import threading`
3. Third-party — `import cv2`, `from ultralytics import YOLO`
4. Internal modules — `from app.config import settings`, `from app.models import Detection`

## Component Patterns (Frontend)

**Component Declaration:**
- Use `export default function ComponentName()` — no arrow function components
- Props typed inline for simple cases: `{ alert }: { alert: Alert }`
- Props typed via separate interface for complex cases: `{ stats }: StatsCardsProps`
- All components with state/effects marked with `"use client"` directive at top

**State Management:**
- Local state via `useState` — no global state library (no Redux, Zustand, etc.)
- Polling via `useEffect` + `setInterval` for real-time data (2-5 second intervals)
- `useCallback` for stable function references in polling effects
- `useRef` for mutable values that don't trigger re-renders

**Data Fetching Pattern:**
```typescript
// Pattern: poll in useEffect with cleanup
useEffect(() => {
  const fetchData = () => {
    apiFunction().then(setData).catch(() => setData(null));
  };
  fetchData();
  const interval = setInterval(fetchData, 2000);
  return () => clearInterval(interval);
}, []);
```

## Class Patterns (Backend)

**Manager Pattern:**
- Core services are classes with `Manager` or descriptive names: `CameraManager`, `AlertManager`, `SafetyDetector`, `StreamProcessor`
- Instantiated as module-level singletons in `backend/app/main.py`
- Use `threading.Lock` for thread safety on shared state
- Properties for read-only access: `@property` for `is_running`, `is_loaded`, `fps`
- Constructor initializes all instance variables to safe defaults (`None`, `False`, `0.0`)

**Configuration:**
- Single `Settings` class using `pydantic_settings.BaseSettings` in `backend/app/config.py`
- Singleton instance: `settings = Settings()`
- Environment prefix: `VIGILANTE_` (e.g., `VIGILANTE_CAMERA_INDEX`)

## Error Handling

**Frontend:**
- API errors silently caught with empty `catch` blocks — no error state surfaced to users
- `try/finally` pattern for loading states in `Controls` component
- Fallback UI for missing data (e.g., `"--"` when stats is null, empty state messages)
- No global error boundary
- No HTTP status code checking — `res.json()` called without verifying `res.ok`

**Backend:**
- `RuntimeError` raised for camera initialization failures
- Guard clauses with early returns (e.g., `if self._model is None: return []`)
- Logging at appropriate levels: `logger.info` for lifecycle events, `logger.warning` for non-fatal issues, `logger.error` for failures
- No structured error responses — endpoints return success objects only

## Logging

**Frontend:** No logging framework — relies on browser console (implicitly, no `console.log` calls in code)

**Backend:**
- Python standard `logging` module
- Logger per module: `logger = logging.getLogger(__name__)`
- Used in: `backend/app/detector.py`, `backend/app/camera.py`, `backend/app/stream.py`
- Pattern: `logger.info("descriptive message with %s", variable)`
- Not used in: `backend/app/alerts.py`, `backend/app/main.py`

## Styling (Frontend)

**Approach:** Tailwind CSS utility classes exclusively — no CSS modules, no styled-components
- Dark theme: `bg-gray-950`, `bg-gray-900`, `text-gray-100`, `border-gray-800`
- Color semantics: red for violations/danger, green for compliant/start, blue for info
- Responsive: `sm:` and `lg:` breakpoints for grid layouts
- Consistent spacing: `gap-4`, `p-4`, `py-3`, `px-4`
- Rounded borders: `rounded-lg` standard, `rounded-full` for badges
- Transitions: `transition-colors` on interactive elements

## Comments

**When to Comment:**
- Inline comments are rare — only used for explaining non-obvious behavior (e.g., `# type: ignore[attr-defined]` for untyped imports)
- No JSDoc/TSDoc anywhere in the codebase
- No file-level documentation headers
- TODO/FIXME comments: none found

## Module Design

**Frontend Exports:**
- Single default export per component file
- Named exports for API functions in `frontend/src/lib/api.ts`
- Named exports for types in `frontend/src/types/index.ts`
- No barrel files for components — each imported directly

**Backend Exports:**
- One class per module (except `models.py` with two dataclasses)
- Constants exported at module level alongside classes
- No `__all__` definitions

---

*Convention analysis: 2026-03-05*
