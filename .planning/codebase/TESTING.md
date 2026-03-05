# Testing Patterns

**Analysis Date:** 2026-03-05

## Current State

**No tests exist in this codebase.** There are zero test files, no test framework configured, no test runner, and no coverage tooling for either the frontend or the backend.

## Test Framework

**Runner:**
- Not configured for frontend or backend
- No `jest.config.*`, `vitest.config.*`, `pytest.ini`, `conftest.py`, or similar files exist

**Assertion Library:**
- Not configured

**Run Commands:**
```bash
# No test commands defined in frontend/package.json
# No test commands defined in backend/pyproject.toml
```

## Recommended Setup

### Frontend (Next.js / React)

**Recommended Framework:** Vitest + React Testing Library

**Why:** Vitest integrates natively with the Vite ecosystem, is fast, and has first-class TypeScript support. React Testing Library aligns with Next.js recommendations.

**Install:**
```bash
cd frontend
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom @vitejs/plugin-react
```

**Config file to create:** `frontend/vitest.config.ts`
```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

**Setup file to create:** `frontend/src/test/setup.ts`
```typescript
import "@testing-library/jest-dom/vitest";
```

**Add to `frontend/package.json` scripts:**
```json
{
  "test": "vitest run",
  "test:watch": "vitest",
  "test:coverage": "vitest run --coverage"
}
```

**Test File Organization:**
- Co-locate tests next to source files
- Naming: `ComponentName.test.tsx` for components, `module.test.ts` for utilities
- Example: `frontend/src/components/AlertCard.test.tsx`
- Example: `frontend/src/lib/api.test.ts`

**Test Structure Pattern:**
```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import AlertCard from "./AlertCard";

describe("AlertCard", () => {
  const mockAlert = {
    id: "test-1",
    timestamp: "2026-03-05T10:00:00Z",
    violation_type: "no_hardhat",
    confidence: 0.95,
    frame_thumbnail: "",
  };

  it("renders violation label and confidence", () => {
    render(<AlertCard alert={mockAlert} />);
    expect(screen.getByText("Sem capacete")).toBeInTheDocument();
    expect(screen.getByText("95%")).toBeInTheDocument();
  });
});
```

**Mocking Pattern for API calls:**
```typescript
import { vi } from "vitest";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getAlerts: vi.fn(),
  clearAlerts: vi.fn(),
  getStatus: vi.fn(),
  getStats: vi.fn(),
  startStream: vi.fn(),
  stopStream: vi.fn(),
}));

// In test:
vi.mocked(api.getAlerts).mockResolvedValue([mockAlert]);
```

### Backend (FastAPI / Python)

**Recommended Framework:** pytest + httpx (for async FastAPI testing)

**Install:**
```bash
cd backend
pip install pytest pytest-cov httpx
```

**Add to `backend/pyproject.toml`:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"
```

**Test File Organization:**
```
backend/
├── app/          # Source code
├── tests/        # Test directory (separate from source)
│   ├── __init__.py
│   ├── conftest.py       # Shared fixtures
│   ├── test_alerts.py    # AlertManager tests
│   ├── test_detector.py  # SafetyDetector tests
│   ├── test_camera.py    # CameraManager tests
│   ├── test_endpoints.py # API endpoint tests
│   └── test_schemas.py   # Pydantic schema tests
```

**Test Structure Pattern:**
```python
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.alerts import AlertManager
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def alert_manager() -> AlertManager:
    return AlertManager()


class TestAlertManager:
    def test_add_alert_creates_alert(self, alert_manager: AlertManager) -> None:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        alert = alert_manager.add_alert("no_hardhat", 0.95, frame)
        assert alert is not None
        assert alert.violation_type == "no_hardhat"

    def test_cooldown_prevents_duplicate_alerts(self, alert_manager: AlertManager) -> None:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        first = alert_manager.add_alert("no_hardhat", 0.95, frame)
        second = alert_manager.add_alert("no_hardhat", 0.90, frame)
        assert first is not None
        assert second is None  # On cooldown
```

**Mocking Pattern for OpenCV/YOLO:**
```python
from unittest.mock import MagicMock, patch

import numpy as np


@patch("app.detector.YOLO")
def test_detector_loads_model(mock_yolo: MagicMock) -> None:
    mock_model = MagicMock()
    mock_model.names = {0: "no_hardhat", 1: "hardhat"}
    mock_yolo.return_value = mock_model

    detector = SafetyDetector()
    detector.load_model()
    assert detector.is_loaded
```

## Priority Test Targets

**High Priority (core business logic):**
1. `backend/app/alerts.py` — `AlertManager` class: cooldown logic, stats calculation, timeline aggregation
2. `backend/app/detector.py` — `SafetyDetector.detect()`: detection filtering, PPE class handling, fallback behavior
3. `frontend/src/lib/api.ts` — API client functions: correct URL construction, response parsing

**Medium Priority (data integrity):**
4. `backend/app/schemas.py` — Pydantic schema validation
5. `frontend/src/types/index.ts` — Type definitions match backend schemas
6. `frontend/src/components/AlertCard.tsx` — Violation label mapping, confidence formatting
7. `frontend/src/components/StatsCards.tsx` — Duration formatting, compliance rate display

**Lower Priority (infrastructure):**
8. `backend/app/camera.py` — Thread lifecycle (requires mocking cv2.VideoCapture)
9. `backend/app/stream.py` — MJPEG generation, FPS calculation
10. `backend/app/main.py` — API endpoint integration tests

## Coverage

**Requirements:** None enforced — no coverage tooling configured

**Recommended Targets:**
- Backend business logic (`alerts.py`, `detector.py`): 80%+
- Frontend utility functions (`api.ts`, helper functions): 80%+
- Frontend components: 60%+ (focus on behavior, not rendering)
- Overall: 70%+ as initial goal

**View Coverage (once configured):**
```bash
# Frontend
cd frontend && npm run test:coverage

# Backend
cd backend && pytest --cov=app --cov-report=html tests/
```

## Test Types

**Unit Tests:**
- Target pure functions and class methods with deterministic behavior
- `AlertManager` methods, `formatDuration`, `formatTimestamp`, violation label mapping
- Mock external dependencies (cv2, YOLO, fetch)

**Integration Tests:**
- FastAPI `TestClient` for endpoint testing
- Verify request/response schemas match frontend types
- Test CORS middleware configuration

**E2E Tests:**
- Not configured, not recommended as immediate priority
- Consider Playwright if browser-level testing is needed later

## What to Mock

**Always mock:**
- `cv2.VideoCapture` — requires physical camera
- `ultralytics.YOLO` — requires model file and GPU
- `fetch` / API calls in frontend components
- `AudioContext` in `AlertPanel` notification sound
- `setInterval` / timers in polling components

**Do not mock:**
- Pydantic model validation
- Pure utility functions (`formatDuration`, `formatTimestamp`)
- `AlertManager` internal logic (test the real implementation)
- TypeScript types (tested implicitly via compilation)

## Fixtures and Factories

**Recommended test data locations:**
- Frontend: `frontend/src/test/fixtures/` — mock API responses
- Backend: `backend/tests/conftest.py` — shared pytest fixtures

**Common test data needed:**
```typescript
// frontend/src/test/fixtures/alerts.ts
export const mockAlert: Alert = {
  id: "test-alert-1",
  timestamp: "2026-03-05T10:30:00Z",
  violation_type: "no_hardhat",
  confidence: 0.92,
  frame_thumbnail: "base64encodedstring",
};

export const mockStats: SessionStats = {
  total_violations: 5,
  session_duration_seconds: 3600,
  compliance_rate: 0.85,
  violations_timeline: [
    { timestamp: "2026-03-05T10:00:00Z", count: 3 },
    { timestamp: "2026-03-05T10:01:00Z", count: 2 },
  ],
};
```

```python
# backend/tests/conftest.py
import numpy as np
import pytest

from app.alerts import AlertManager


@pytest.fixture
def sample_frame() -> np.ndarray:
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def alert_manager() -> AlertManager:
    return AlertManager()
```

---

*Testing analysis: 2026-03-05*
