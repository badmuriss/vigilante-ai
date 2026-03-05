---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `cd backend && .venv/bin/python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && .venv/bin/python -m pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && .venv/bin/python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && .venv/bin/python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 0 | BUG-01, BUG-02 | unit | `cd backend && .venv/bin/python -m pytest tests/test_stream.py -x` | Wave 0 | pending |
| 01-01-02 | 01 | 0 | MODL-01, MODL-02 | unit | `cd backend && .venv/bin/python -m pytest tests/test_detector.py -x` | Wave 0 | pending |
| 01-01-03 | 01 | 0 | CONF-01 | integration | `cd backend && .venv/bin/python -m pytest tests/test_api.py -x` | Wave 0 | pending |
| 01-02-01 | 02 | 1 | BUG-01 | unit | `cd backend && .venv/bin/python -m pytest tests/test_stream.py::test_stop_start_lifecycle -x` | Wave 0 | pending |
| 01-02-02 | 02 | 1 | BUG-02 | unit | `cd backend && .venv/bin/python -m pytest tests/test_stream.py::test_thread_safety -x` | Wave 0 | pending |
| 01-02-03 | 02 | 1 | MODL-03 | unit | `cd backend && .venv/bin/python -m pytest tests/test_stream.py::test_fps_throttle -x` | Wave 0 | pending |
| 01-03-01 | 03 | 1 | MODL-01, MODL-02 | unit | `cd backend && .venv/bin/python -m pytest tests/test_detector.py -x` | Wave 0 | pending |
| 01-03-02 | 03 | 1 | CONF-03 | unit | `cd backend && .venv/bin/python -m pytest tests/test_stream.py::test_epi_filter -x` | Wave 0 | pending |
| 01-04-01 | 04 | 2 | CONF-01 | integration | `cd backend && .venv/bin/python -m pytest tests/test_api.py::test_epi_config_endpoints -x` | Wave 0 | pending |
| 01-04-02 | 04 | 2 | CONF-02 | manual | N/A — visual UI | N/A | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/__init__.py` — package init
- [ ] `backend/tests/conftest.py` — shared fixtures (mock model, mock camera frames)
- [ ] `backend/tests/test_detector.py` — covers MODL-01, MODL-02
- [ ] `backend/tests/test_stream.py` — covers BUG-01, BUG-02, MODL-03, CONF-03
- [ ] `backend/tests/test_api.py` — covers CONF-01
- [ ] `backend/pyproject.toml` [tool.pytest] section
- [ ] Framework install: `pip install pytest pytest-asyncio httpx`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| EPI checkbox panel renders with 6 items, toggles work | CONF-02 | Visual UI component, layout verification | Open monitoring page, verify sidebar shows 6 checkboxes, toggle each, confirm immediate effect on stream |
| Portuguese labels display on bounding boxes | MODL-02 | Visual rendering on video stream | Start monitoring with EPIs selected, verify "Capacete 92%" style labels appear |
| Stopped state shows placeholder message | BUG-01 | Visual state transition | Stop monitoring, verify "Clique em Iniciar..." placeholder appears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
