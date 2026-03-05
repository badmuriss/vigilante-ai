# Vigilante.AI

## What This Is

Sistema de seguranca do trabalho com visao computacional. Detecta EPIs via webcam usando YOLOv8 com modelo pre-treinado para 6 classes de EPI, com painel configuravel para escolher quais equipamentos monitorar. Backend em FastAPI + frontend em Next.js 14.

## Core Value

Detectar com precisao quando um trabalhador remove ou nao usa EPIs selecionados e registrar cada infracao de forma clara e individual.

## Requirements

### Validated

- ✓ Stream de video ao vivo via MJPEG — existente
- ✓ API REST para status, alertas e estatisticas — existente
- ✓ Frontend com pagina de monitoramento e dashboard — existente
- ✓ Controle de iniciar/parar monitoramento — existente
- ✓ Painel de alertas na pagina de monitoramento — existente
- ✓ Dashboard com estatisticas e grafico de violacoes — existente
- ✓ Setup Docker (docker-compose) — existente

### Active

- [ ] Integrar modelo pre-treinado `Tanishjain9/yolov8n-ppe-detection-6classes` (6 classes: Gloves, Vest, goggles, helmet, mask, safety_shoe)
- [ ] Painel configuravel no frontend: checkboxes para selecionar quais EPIs monitorar (das 6 classes disponiveis)
- [ ] Backend recebe a lista de EPIs ativos e so gera infracoes para os selecionados
- [ ] Corrigir instabilidade da deteccao (piscando entre detectado/nao detectado)
- [ ] Eliminar falsos positivos (detectando objetos que nao sao pessoas)
- [ ] Nomenclatura em portugues para as 6 classes: Luvas, Colete, Protecao ocular, Capacete, Mascara, Calcado de seguranca
- [ ] Nova logica de infracao: so conta 1 infracao se a pessoa nunca colocou EPI (nao acumula)
- [ ] Nova logica de infracao: nova infracao cada vez que a pessoa coloca EPI e depois tira
- [ ] Logica de infracao independente por tipo de EPI
- [ ] Exibir infracoes separadas: se sem oculos E sem capacete, mostrar 2 alertas distintos (nao 1 so)
- [ ] Corrigir bug: ao parar e iniciar a deteccao, o sistema trava

### Out of Scope

- Treinamento de modelo custom — usar modelo pre-treinado do Hugging Face
- App mobile — web-first
- Banco de dados — estado em memoria e suficiente para o momento

## Context

- O projeto ja tem backend (FastAPI) e frontend (Next.js 14) funcionais
- Deteccao atual usa YOLOv8 generico (`yolov8n.pt`) — sera substituido por `Tanishjain9/yolov8n-ppe-detection-6classes`
- Modelo pre-treinado detecta 6 classes: Gloves (~0.69 mAP), Vest (~0.90), goggles (~0.90), helmet (~0.90), mask (~0.80), safety_shoe (~0.64)
- O `SafetyDetector` em `backend/app/detector.py` faz a inferencia e anotacao dos frames
- O `AlertManager` em `backend/app/alerts.py` gerencia alertas com cooldown
- O `StreamProcessor` em `backend/app/stream.py` controla o loop de captura/processamento
- Nao ha testes automatizados
- Estado todo em memoria (deque de alertas, stats on-the-fly)
- Docker setup recentemente adicionado

## Constraints

- **Stack**: Manter FastAPI + Next.js 14 + OpenCV + YOLOv8/Ultralytics
- **Modelo**: Usar `Tanishjain9/yolov8n-ppe-detection-6classes` do Hugging Face
- **Performance**: Deteccao precisa rodar em tempo real (~15+ FPS no stream)
- **Compatibilidade**: Webcam padrao via OpenCV

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Usar `Tanishjain9/yolov8n-ppe-detection-6classes` | Modelo pre-treinado com 6 classes de EPI, mAP alto para as classes principais | — Pending |
| Painel configuravel de EPIs | Permitir selecionar quais dos 6 EPIs monitorar via checkboxes no frontend | — Pending |
| Nomenclatura em portugues | Traduzir as 6 classes para portugues no frontend | — Pending |
| Infracao nao-acumulativa sem protecao | Se nunca colocou, conta 1 so; nova infracao so ao remover apos colocar | — Pending |

---
*Last updated: 2026-03-05 after initialization (updated with HF model and configurable EPIs)*
