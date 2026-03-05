# Vigilante.AI

## What This Is

Sistema de seguranca do trabalho com visao computacional. Detecta EPIs (protecao na cabeca e protecao ocular) via webcam usando YOLOv8, exibe alertas visuais em tempo real. Backend em FastAPI + frontend em Next.js 14.

## Core Value

Detectar com precisao quando um trabalhador remove ou nao usa protecao (cabeca/ocular) e registrar cada infracao de forma clara e individual.

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

- [ ] Melhorar deteccao: substituir modelo generico por modelo pre-treinado especifico para EPIs
- [ ] Corrigir instabilidade da deteccao (piscando entre detectado/nao detectado)
- [ ] Eliminar falsos positivos (detectando objetos que nao sao pessoas)
- [ ] Mudar nomenclatura: "capacete" → "Protecao na cabeca" (aceitar capacete, chapeu, bone)
- [ ] Mudar nomenclatura: "oculos de protecao" → "Protecao ocular"
- [ ] Nova logica de infracao: so conta 1 infracao se a pessoa nunca colocou protecao (nao acumula)
- [ ] Nova logica de infracao: nova infracao cada vez que a pessoa coloca protecao e depois tira
- [ ] Mesma logica de infracao para cabeca e ocular, independentes
- [ ] Exibir infracoes separadas: se sem oculos E sem capacete, mostrar 2 alertas distintos (nao 1 so)
- [ ] Corrigir bug: ao parar e iniciar a deteccao, o sistema trava

### Out of Scope

- Deteccao de outros EPIs (luvas, botas, colete) — foco apenas em cabeca e ocular por ora
- App mobile — web-first
- Banco de dados — estado em memoria e suficiente para o momento

## Context

- O projeto ja tem backend (FastAPI) e frontend (Next.js 14) funcionais
- Deteccao atual usa YOLOv8 generico (`yolov8n.pt`) — nao e especifico para EPIs
- O modelo generico detecta classes COCO (person, etc), nao EPIs diretamente
- O `SafetyDetector` em `backend/app/detector.py` faz a inferencia e anotacao dos frames
- O `AlertManager` em `backend/app/alerts.py` gerencia alertas com cooldown
- O `StreamProcessor` em `backend/app/stream.py` controla o loop de captura/processamento
- Nao ha testes automatizados
- Estado todo em memoria (deque de alertas, stats on-the-fly)
- Docker setup recentemente adicionado

## Constraints

- **Stack**: Manter FastAPI + Next.js 14 + OpenCV + YOLOv8/Ultralytics
- **Modelo**: Buscar modelo pre-treinado para EPIs (Hugging Face/Roboflow) em vez de treinar do zero
- **Performance**: Deteccao precisa rodar em tempo real (~15+ FPS no stream)
- **Compatibilidade**: Webcam padrao via OpenCV

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Usar modelo pre-treinado para EPIs | Treinar do zero exige dataset e tempo; modelos pre-treinados ja existem para EPIs | — Pending |
| Nomenclatura "Protecao na cabeca"/"Protecao ocular" | Termos genericos que cobrem capacete/chapeu/bone e oculos de protecao | — Pending |
| Infracao nao-acumulativa sem protecao | Se nunca colocou, conta 1 so; nova infracao so ao remover apos colocar | — Pending |

---
*Last updated: 2026-03-05 after initialization*
