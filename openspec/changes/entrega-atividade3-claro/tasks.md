# Tasks — Entrega da Atividade 3 (Claro)

Repositório: `/home/badmuriss/Documents/vigilante-ai`. Executar na ordem, as tarefas 1 a 4 são pré-requisito das 5 a 8.

---

## 0. Realinhar a suíte de testes (descoberta durante a execução)

**Contexto:** o gate de teste da tarefa 1 barrou o commit. A suíte já estava vermelha no HEAD `87def54`, com 10 falhas em `test_detector.py` e `test_stream.py`, confirmadas como pré-existentes via stash. Repo com suíte vermelha ia para o GitHub que o professor analisa.

**Diagnóstico:** todas as 10 eram teste desatualizado, zero bug de produção. Só 4 vinham do escopo de 2 classes (capacete e colete). As outras 6 eram deriva de arquitetura: o pipeline saiu de nível de cena (`detector.annotate_frame`) para nível de pessoa (`stream._evaluate_person`, `_annotate_per_person`, suavização temporal por track). O `test_fps_throttle` era deriva de assinatura: `detect()` ganhou `color_palettes=` e o stub de 1 argumento levantava `TypeError` matando a thread, o que aparecia como "0 frames".

- [x] Realinhar `backend/tests/test_detector.py` ao escopo de 2 classes e à paleta real (`GREEN`, `LABEL_BG`, `RED`).
- [x] Realinhar `backend/tests/test_stream.py` ao pipeline por pessoa, com fixture `fast_smoothing` e poller `_wait_for` em vez de sleep.
- [x] `backend/tests/conftest.py`: `detector.detect_persons.return_value = []` explícito.
- [x] Nenhum teste deletado. Adicionado `test_annotate_marks_missing_epi_in_red` para cobrir o branch vermelho.

**Critério de pronto (verificável):** `cd backend && .venv/bin/python -m pytest -q` sem falha. Confirmado de forma independente: **73 passed**.

**Achados de código morto, deixados de propósito para decisão do dono:** `SafetyDetector.annotate_frame` não tem chamador de produção (só os testes), e `EPI_ALERT_LABELS` é importado por `stream.py:18` e nunca usado.

---

## 1. Commitar e dar push no delta do hub

**Contexto:** 35 mudanças estão fora do git desde 28/05, concentradas na camada de canal do WhatsApp. Entre elas, dois arquivos **untracked** que são essenciais: a migração `backend/migrations/versions/0005_whatsapp_operators.py` e o teste `backend/tests/test_whatsapp_webhook.py`. Sem commit, a maior evolução do projeto não existe para o avaliador.

- [x] Rodar `git status --short` e conferir as 35 entradas.
- [x] Commitar em grupos temáticos, mensagens em conventional commits, sem mencionar ferramenta de IA:
  - `feat(whatsapp): resolve tenant by operator phone on shared platform number` → `backend/app/webhooks/whatsapp.py`, `backend/app/db/entities.py`, `backend/app/repositories.py`, `backend/migrations/versions/0005_whatsapp_operators.py`, `backend/app/config.py`
  - `feat(whatsapp): push alert review with decision buttons` → `backend/app/services/whatsapp_notifier.py`, `backend/app/services/alert_service.py`, `backend/app/registry.py`
  - `feat(notifications): rework whatsapp operator config api and ui` → `backend/app/notifications/router.py`, `backend/app/notifications/schemas.py`, `frontend/src/components/WhatsAppNotificationsCard.tsx`, `frontend/src/lib/api.ts`, `frontend/src/types/index.ts`
  - `feat(chat): sharpen agent tools and channel personas` → `backend/app/chat/prompts.py`, `backend/app/chat/tools/*.py`, `backend/app/kb/ingest.py`, `backend/knowledge/*.md`, `backend/scripts/seed_kb.py`
  - `test(whatsapp): cover webhook, notifier and notifications router` → `backend/tests/*`
  - `chore: update compose, env example and docs` → `docker-compose.yml`, `.env.example`, `README.md`, `frontend/next.config.mjs`, `frontend/src/lib/useLiveFrame.ts`, `descricao.txt`, `backend/app/main.py`
  - Remoção do `NEXT_STEPS.md` entra no commit de chore.
- [x] Decidir sobre `.claude-plugin/` e `harness.toml`: ou entram em `chore(tooling)`, ou vão para `.gitignore`. Não deixar untracked.
- [x] `git push`.

**Critério de pronto (verificável):** `git status --short` retorna vazio, e `git log --oneline -8` mostra os commits acima.

---

## 2. Blur facial nos artefatos de revisão

**Contexto:** a Atividade 1 prometeu "foto anonimizada" no alerta do WhatsApp e o roteiro do vídeo diz "com o rosto borrado" na tela. Hoje não existe nenhum blur no código (`grep -rn "blur" backend/app/` não retorna nada). O detector já acha faces.

**Onde:** `backend/app/services/alert_service.py`, método `add_alert` (começa na linha ~52). Ele recebe `frame` (anotado, destinado a humano) e `raw_frame` (limpo, destinado a treino) e produz três JPEGs: `thumb_jpeg`, `full_jpeg` e `raw_jpeg` (linhas ~84 a 92). O notificador de WhatsApp consome os caminhos persistidos, então borrar aqui cobre painel e WhatsApp de uma vez.

- [x] Adicionar em `alert_service.py` uma função de módulo `_blur_faces(frame, boxes)` que devolve **uma cópia** do frame com `cv2.GaussianBlur` aplicado em cada região `(x1, y1, x2, y2)`. Kernel proporcional ao tamanho da caixa, ímpar. Caixa fora dos limites do frame deve ser recortada, nunca estourar índice.
- [x] Adicionar parâmetro `face_bboxes: list[tuple[int, int, int, int]] | None = None` na assinatura de `add_alert`.
- [x] Aplicar o blur **antes** de encodar `thumb_jpeg` e `full_jpeg`. **Não aplicar em `raw_jpeg`**: capacete fica adjacente ao rosto e borrar degrada o sinal de treino do YOLO. Deixar comentário no código dizendo isso.
- [x] No chamador `backend/app/stream.py` (chamada de `add_alert` na linha ~540), passar `face_bboxes=[d.bbox for d in visible_faces]`. A variável `visible_faces` já existe em escopo (definida na linha ~371 filtrando por `FACE_CLASS_KEY`) e cada item é um `Detection` de `backend/app/models.py`, cujo campo `bbox` é `tuple[int, int, int, int]`. `cv2` já está importado em `alert_service.py`.
- [x] Criar `backend/tests/test_alert_blur.py`. Imitar o estilo de `backend/tests/test_whatsapp_notifier.py` (mesmo diretório, pytest puro, sem framework extra). O teste deve construir um frame sintético com uma região de cor uniforme, chamar o blur com uma caixa cobrindo parte dela, e afirmar que: (a) os pixels dentro da caixa mudaram, (b) os pixels fora da caixa são idênticos, (c) o frame original não foi mutado.

**Critério de pronto (verificável):** `cd backend && python -m pytest tests/test_alert_blur.py -q` passa, e `grep -n "raw_jpeg" app/services/alert_service.py` mostra que o raw é encodado a partir de `raw_frame` sem passar por `_blur_faces`.

---

## 3. Endpoints de saúde para as probes do Kubernetes

**Contexto:** `docs/kubernetes-k3s.md` seção 2 explica por que `/api/status` não serve como probe (chama `_ensure_legacy_camera()`, tem efeito colateral e depende de câmera) e já traz o código de referência.

**Onde:** `backend/app/main.py`.

- [x] Adicionar `GET /healthz`: liveness, sem I/O, retorna `{"status": "ok"}`.
- [x] Adicionar `GET /readyz`: readiness, checa banco com `SELECT 1` de timeout curto e `detector.is_loaded`. Responde 503 quando não está pronto, 200 quando está.

**Critério de pronto (verificável):** com o stack no ar, `curl -s -o /dev/null -w '%{http_code}' localhost:8000/healthz` retorna `200`, e `curl -s localhost:8000/readyz | grep -q '"ready"'` casa.

---

## 4. Manifestos k3s e subir o cluster

> CONCLUÍDA 26/07. Cluster no ar com `--docker --write-kubeconfig-mode 644`, domínio respondendo 200, quatro provas de rollout verdes. O que quebrou no caminho está na seção 8 de `docs/kubernetes-k3s.md`.

**Contexto:** `docs/kubernetes-k3s.md` traz os YAML de namespace, ConfigMap, StatefulSet do Postgres, Deployment do backend com as três probes, Deployment do frontend e Ingress. Copiar de lá e ajustar. Dois desvios decididos em `design.md`: mediamtx entra no cluster como ClusterIP com RTSP sobre TCP (sem NodePort, sem UDP), e não há GPU.

- [x] Criar `k8s/` na raiz com: `00-namespace.yaml`, `10-postgres.yaml`, `20-backend.yaml`, `30-frontend.yaml`, `40-mediamtx.yaml`, `50-cloudflared.yaml`, `60-ingress.yaml`.
- [x] Backend com `startupProbe` (`failureThreshold: 30`, `periodSeconds: 5`) apontando para `/healthz`, mais `livenessProbe` em `/healthz` e `readinessProbe` em `/readyz`. Sem startupProbe o liveness mata o pod durante o carregamento do YOLO.
- [x] `replicas: 1` no backend, com comentário explicando que `StreamSource` por câmera vive na memória do processo. Frontend com `replicas: 2`.
- [x] Segredos por `kubectl create secret`, nunca em arquivo versionado. Incluir `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN`, chave da OpenAI, token do HF e o token do cloudflared.
- [x] Instalar k3s, importar as imagens no containerd (`docker save ... | sudo k3s ctr images import -`), aplicar `kubectl apply -f k8s/`.
- [x] Exercitar o cluster: `kubectl -n vigilante delete pod -l app=backend`, `scale deploy/frontend --replicas=3`, `rollout restart deploy/backend`, `rollout undo deploy/backend`. Anotar no fim de `docs/kubernetes-k3s.md` o que quebrou e por quê.

**Critério de pronto (verificável):** `kubectl -n vigilante get pods` mostra todos `Running` e `READY 1/1` (frontend 2/2), e `curl -s -o /dev/null -w '%{http_code}' https://vigilanteai.outis.com.br/api/webhooks/whatsapp` retorna algo diferente de `502`.

---

## 5. Capturar os assets de WhatsApp

> Atualização 26/07: o dono já tem 2 dos prints (alerta com blur e revisão aplicada). Falta só o de áudio, que fica como placeholder no deck até ele rodar o WhatsApp. O print de outra empresa (`wa_tenant_b`) foi **cortado por decisão dele**, junto com o passo correspondente da demo.

**Contexto:** os cinco screenshots dos slides da Atividade 2 (`docs/enterprise-challenge-claro/assets-hub/`) são todos de tela web. Nenhum de celular. Esse é o buraco visual que a Atividade 3 precisa fechar.

- [x] Criar `docs/enterprise-challenge-claro/assets-a3/` e capturar. FEITO em 07/08,
      tudo da mesma execução real na câmera Canteiro 2:
  - `wa_alert_blur.jpg`: alerta no WhatsApp, rosto borrado, os dois botões
  - `wa_review_confirmed.jpg`: o toque em Confirmar Infração e a resposta do sistema
  - `panel_historico.png`: histórico com tudo decidido e **0 aguardando revisão**
  - `panel_assistente.png`: assistente respondendo ao gestor com gráfico
  - `alerta_zoom.jpg`: o recorte cru do alerta, para uso no vídeo

O print de áudio (`wa_audio.png`) ficou de fora do deck: o passo existe e vai ao ar
na demonstração gravada, mas exigia o dono mandar um áudio, e um placeholder
tracejado no PDF entregue custa mais do que o passo vale numa página estática.

**Critério de pronto (verificável):** `ls docs/enterprise-challenge-claro/assets-a3/ | wc -l` retorna 5 ou mais.

---

## 6. Criar `slides-atividade3.html`

> Atualização 26/07, depois de review do dono ("muito poluído, não sei para onde olhar"): o deck foi de 9 para **8 slides**. Os antigos 3 e 4 (identidade e evolução de arquitetura) fundiram num só, porque gastavam duas telas com a mesma mudança. Regras de densidade aplicadas em todos: no máximo 1 título + 1 zona visual, grid de no máximo 3 itens, texto de card em 1 linha, faixas `.cross` e painéis laterais redundantes eliminados, rodapés longos removidos. O roteiro foi realinhado e passou por `/unslop`.

**Onde:** `docs/enterprise-challenge-claro/slides-atividade3.html`.

**Exemplar a imitar:** `docs/enterprise-challenge-claro/slides-atividade2-implementacao.html`. Copiar o bloco `<style>` inteiro e o `<script>` de navegação **verbatim**. Reusar as classes existentes: `.slide`, `.chrome`, `.brand`, `.claro-tag`, `.foot`, `.eyebrow`, `.member`, `.showcase`, `.browser`, `.hub-grid`, `.hub-diagram`, `.ch-grid`, `.under-grid`, `.status-grid`, `.closing`, `.lc`. Fonte Geist, fundo `#0a0a0b`, âmbar `#f5a623`, tag Claro em `#da291c`. Logo e fotos vêm de `../fase-4-prototipando-solucao/assets/`.

- [x] Nove slides, `data-i` de 1 a 9, contador do rodapé `NN / 09`:
  1. **Capa, grupo e NEXT.** Cinco integrantes com foto e RM (Murilo 98220, Gabriel 551195, Mateus 550521, Roberto 99976, Felipe 551619). **Links do vídeo no YouTube e do repositório GitHub têm que estar neste slide**, é exigência explícita do enunciado. Tag do chrome: `ATIVIDADE 3 · DESENVOLVIMENTO`.
  2. **O que mudou desde a Atividade 2.** Quatro cards (`.under-grid`): identidade por telefone, canal que executa ação, hardening do webhook, cobertura de teste dobrada.
  3. **Um número, várias empresas.** O núcleo. Diagrama de identidade mais o tradeoff: trocou isolamento de credencial por onboarding sem fricção.
  4. **Evolução de arquitetura.** Antes e depois explícitos: credencial por cliente resolvida por `phone_number_id`, contra número de plataforma resolvido pelo telefone do remetente. Assumir a mudança em relação ao slide 7 da Atividade 2.
  5. **Arquitetura geral.** Reusar o diagrama de convergência do slide 3 da Atividade 2 (`.hub-diagram`), acrescentando a camada de identidade na entrada do WhatsApp e a camada de orquestração k3s embaixo.
  6. **Tecnologias adotadas.** FastAPI, Next.js, TypeScript, Postgres com pgvector, DeepSeek com fallback, embeddings OpenAI, reranker Hugging Face, Whisper, YOLOv8s próprio (mAP 0,944), WhatsApp Cloud API, Docker, k3s, Prometheus, pytest.
  7. **Demonstração.** Cinco passos numerados com os assets de `assets-a3/`, moldura de celular para os prints de WhatsApp.
  8. **Governança e valor.** Rosto borrado antes de sair, webhook assinado, isolamento por empresa. Valor em linguagem qualitativa, **sem número medido**.
  9. **Roadmap e fechamento.** `.status-grid` com entregue, em andamento e próximas ondas, mais `.closing` com quote e os links de GitHub e Hugging Face.
- [x] Manter o bloco `@media print` do exemplar, que é o que permite exportar 1920x1080 por página.

**Critério de pronto (verificável):** `grep -c 'class="slide"' docs/enterprise-challenge-claro/slides-atividade3.html` retorna `9`, e o comando abaixo não imprime nada (nenhuma imagem quebrada):

```bash
cd docs/enterprise-challenge-claro && grep -o 'src="[^"]*"' slides-atividade3.html | sed 's/src="//;s/"//' | sort -u | while read -r f; do [ -f "$f" ] || echo "FALTA: $f"; done
```

---

## 7. Ajustar `roteiro-atividade3.md`

**Onde:** `docs/enterprise-challenge-claro/roteiro-atividade3.md` (já existe).

- [x] Substituir o SLIDE 8 de valor: sair os placeholders numéricos `«X%»`, `«X»` e `«R$ X»`, entrar valor qualitativo. Motivo em `design.md`, decisão 4.
- [x] Adicionar em "PERGUNTAS PROVÁVEIS" a resposta para "qual o número de resolução sem humano": ainda não medido, o que existe hoje é o mecanismo, e a série histórica vem com o piloto. Nunca inventar número no ar.
- [x] Alinhar a numeração com o deck de nove slides da tarefa 6: entra o slide 4 de evolução de arquitetura, e os atuais "Governança do canal" e "Valor medido" **fundem** no slide 8. Refazer a tabela de tempo mantendo 150s de demo e a lista de cortes para fechar em 5:00.
- [x] Conferir que a seção de frases-armadilha mantém o aviso de não repetir "credenciais do WhatsApp de cada cliente cifradas por tenant", que era verdade na Atividade 2 e deixou de ser.

**Critério de pronto (verificável):** `grep -c '«' docs/enterprise-challenge-claro/roteiro-atividade3.md` retorna `0`, e `grep -c '^## SLIDE' ...` retorna `9`.

---

## 8. Gravar, publicar e fechar o PDF

- [ ] Antes de gravar: subir o stack e conferir que o webhook da Meta aponta para a URL viva. Template com botões: **já aprovado na Meta**, confirmado pelo dono em 26/07.
- [ ] Gravar um take isolado só do fluxo WhatsApp e guardar como plano B.
- [ ] Gravar o pitch completo. Alvo 5:00, com 150s de demonstração. Nada de código na tela.
- [ ] Publicar no YouTube como **não listado**.
- [ ] Colar o link do YouTube em `docs/enterprise-challenge-claro/link-video-pendente.txt` e entregar
      esse link junto do PDF. Decisão do dono em 07/08: o card do vídeo saiu do slide 1,
      porque o link só existe depois da gravação e o deck não vai ser reaberto para recebê-lo.
      Placeholder impresso no PDF pesa mais contra do que a ausência do card.
- [x] Exportar os slides para PDF (print do navegador, 1920x1080, sem margem). FEITO: `slides-atividade3.pdf`, 8 páginas, 1440x810pt, via `google-chrome --headless=new --print-to-pdf`.

**Critério de pronto (verificável):** existe `docs/enterprise-challenge-claro/slides-atividade3.pdf` com 8 páginas, e o link do GitHub sai como anotação clicável (`grep -c "/URI" ...` maior que zero).
