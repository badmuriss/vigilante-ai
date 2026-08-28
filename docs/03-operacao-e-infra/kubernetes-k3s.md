# Rodar o Vigilante.AI em Kubernetes (k3s)

Guia de migração do `docker-compose.yml` atual para k3s numa única máquina.

**Por que:** o Compose sobe containers; o Kubernetes **mantém um estado verdadeiro**. Você declara "quero N réplicas saudáveis atendendo tráfego" e o cluster persegue isso sozinho — reinicia o que trava, tira do balanceador quem não responde, troca versão sem derrubar. Para um sistema que roda 24/7 lendo câmera, essa diferença é operacional, não acadêmica.

**Escopo honesto:** k3s numa máquina não é alta disponibilidade. É Kubernetes de verdade (mesma API, mesmos manifestos), com um nó só. Serve para aprender, para homologação e para o deploy atual — não substitui um cluster gerenciado.

---

## 1. O mapa mental

| `docker-compose.yml` | Kubernetes | O que muda de verdade |
|---|---|---|
| `services:` | **Deployment** | ganha réplicas e rolling update |
| `ports:` (publicar) | **Service** + **Ingress** | Service = IP interno estável; Ingress = entrada HTTP |
| `environment:` | **ConfigMap** | config versionada, separada da imagem |
| segredo em `.env` | **Secret** | some do repo e do `docker inspect` |
| `depends_on: condition: service_healthy` | **readinessProbe** | não é ordem de boot: é "só recebe tráfego quando responde" |
| `restart: unless-stopped` | **livenessProbe** | mata e recria quem travou vivo (processo de pé, mas pendurado) |
| `healthcheck:` | as duas probes acima | Compose junta os dois conceitos, K8s separa |
| `volumes:` nomeado | **PVC** | volume com ciclo de vida próprio, sobrevive ao pod |
| `devices:` / `group_add` | `securityContext` + device plugin | **é aqui que dói** — ver seção 5 |
| `profiles:` | namespace ou kustomize overlay | não existe equivalente direto |

**A parte que cai em entrevista:** readiness × liveness.
- **liveness** falhou → o pod é **morto e recriado**. Use para "travou".
- **readiness** falhou → o pod **sai do balanceador, mas continua vivo**. Use para "ainda não pronto" ou "dependência fora".

Trocar os dois é o erro clássico: liveness apontando para o banco derruba toda a aplicação em loop quando o banco pisca.

---

## 2. Pré-requisito no backend: endpoints de saúde

Hoje só existe `/api/status`, e ele **não serve como probe** — chama `_ensure_legacy_camera()`, ou seja, tem efeito colateral e depende de câmera. Probe tem que ser barata e sem efeito.

Adicionar em `backend/app/main.py`:

```python
@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness: o processo responde? Nada de I/O aqui."""
    return {"status": "ok"}


@app.get("/readyz")
def readyz(response: Response) -> dict[str, object]:
    """Readiness: dá para receber tráfego? Checa dependências."""
    db_ok = _ping_db()          # SELECT 1, com timeout curto
    ready = db_ok and detector.is_loaded
    if not ready:
        response.status_code = 503
    return {"ready": ready, "db": db_ok, "model": detector.is_loaded}
```

`detector.is_loaded` no readiness é o detalhe que importa aqui: carregar o YOLO leva segundos, e sem isso o Ingress manda requisição para um pod que ainda não sabe detectar nada.

---

## 3. Manifestos mínimos

Criar `k8s/`. Ordem de aplicação: namespace → secret/config → postgres → backend → frontend → ingress.

### 3.1 Namespace, config e secret

```yaml
# k8s/00-namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: vigilante
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: vigilante
data:
  VIGILANTE_DATABASE_URL: postgresql+psycopg2://vigilante:vigilante_dev@postgres:5432/vigilante
  VIGILANTE_BLOB_STORAGE_PATH: /data/alerts
  VIGILANTE_RETRAINING_EXPORT_PATH: /data/feedback
  VIGILANTE_LOCAL_TIMEZONE: America/Sao_Paulo
  VIGILANTE_LLM_MODEL: deepseek-v4-pro
  VIGILANTE_EMBEDDING_MODEL: text-embedding-3-small
  VIGILANTE_PUBLIC_APP_URL: https://vigilanteai.outis.com.br
```

Os segredos **não** entram em arquivo versionado:

```bash
kubectl -n vigilante create secret generic backend-secrets \
  --from-literal=VIGILANTE_OPENAI_API_KEY=... \
  --from-literal=VIGILANTE_HF_TOKEN=... \
  --from-literal=VIGILANTE_WHATSAPP_ACCESS_TOKEN=... \
  --from-literal=VIGILANTE_NOTIFY_ENCRYPTION_KEY=...
```

> Secret do Kubernetes é base64, **não é criptografia**. Em cluster de verdade: Sealed Secrets, SOPS ou External Secrets. Vale saber disso quando perguntarem.

### 3.2 Postgres (StatefulSet, não Deployment)

Banco tem identidade e disco: `StatefulSet` é a peça certa. `Deployment` com PVC funciona com 1 réplica, mas ensina o hábito errado.

```yaml
# k8s/10-postgres.yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: vigilante
spec:
  clusterIP: None          # headless: o StatefulSet resolve por DNS estável
  selector:
    app: postgres
  ports:
    - port: 5432
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: vigilante
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: pgvector/pgvector:pg16
          env:
            - name: POSTGRES_USER
              value: vigilante
            - name: POSTGRES_PASSWORD
              value: vigilante_dev     # trocar por secret fora de dev
            - name: POSTGRES_DB
              value: vigilante
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          ports:
            - containerPort: 5432
          readinessProbe:
            exec:
              command: ["pg_isready", "-U", "vigilante", "-d", "vigilante"]
            initialDelaySeconds: 5
            periodSeconds: 5
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
```

O k3s já vem com `local-path` como StorageClass padrão, então o PVC é atendido sem configurar nada.

### 3.3 Backend

```yaml
# k8s/20-backend.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: alerts-data
  namespace: vigilante
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 20Gi
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: vigilante
spec:
  selector:
    app: backend
  ports:
    - port: 8000
      targetPort: 8000
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: vigilante
spec:
  replicas: 1                     # ver seção 5 antes de aumentar
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: vigilante-backend:latest
          imagePullPolicy: IfNotPresent
          envFrom:
            - configMapRef:
                name: backend-config
            - secretRef:
                name: backend-secrets
          ports:
            - containerPort: 8000
          startupProbe:               # dá tempo do YOLO carregar
            httpGet:
              path: /healthz
              port: 8000
            failureThreshold: 30
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8000
            periodSeconds: 20
          readinessProbe:
            httpGet:
              path: /readyz
              port: 8000
            periodSeconds: 10
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              memory: "4Gi"
          volumeMounts:
            - name: alerts
              mountPath: /data/alerts
      volumes:
        - name: alerts
          persistentVolumeClaim:
            claimName: alerts-data
```

**`startupProbe` é o detalhe que separa quem já operou de quem só leu tutorial.** Sem ela, o liveness começa a contar durante o carregamento do modelo e mata o pod antes dele subir — loop infinito de restart. Com ela, o liveness só entra em cena depois que o startup passou.

### 3.4 Frontend e Ingress

```yaml
# k8s/30-frontend.yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: vigilante
spec:
  selector:
    app: frontend
  ports:
    - port: 3000
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: vigilante
spec:
  replicas: 2                    # o front é stateless: escala de graça
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend
          image: vigilante-frontend:latest
          env:
            - name: NEXT_BACKEND_INTERNAL_URL
              value: http://backend:8000     # DNS interno do Service
          ports:
            - containerPort: 3000
          readinessProbe:
            httpGet:
              path: /
              port: 3000
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: vigilante
  namespace: vigilante
spec:
  ingressClassName: traefik       # k3s já traz o Traefik
  rules:
    - host: vigilanteai.outis.com.br
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 3000
```

Mantém o desenho atual: o Next faz rewrite de `/api/*` para o backend, então uma entrada só serve app, API, frames e webhook.

---

## 4. Subir

```bash
curl -sfL https://get.k3s.io | sh -
sudo k3s kubectl get nodes

# build local + importar no containerd do k3s (não existe registry aqui)
docker build -t vigilante-backend:latest ./backend
docker build -t vigilante-frontend:latest ./frontend
docker save vigilante-backend:latest  | sudo k3s ctr images import -
docker save vigilante-frontend:latest | sudo k3s ctr images import -

kubectl apply -f k8s/
kubectl -n vigilante get pods -w
kubectl -n vigilante logs -f deploy/backend
```

Testar o que o Compose não testa:

```bash
kubectl -n vigilante delete pod -l app=backend     # some e volta sozinho
kubectl -n vigilante scale deploy/frontend --replicas=3
kubectl -n vigilante rollout restart deploy/backend  # rolling, sem downtime
kubectl -n vigilante rollout undo deploy/backend     # volta a versão anterior
```

---

## 5. As partes difíceis deste projeto especificamente

Não são detalhes: é onde a migração realmente pensa.

### 5.1 Webcam local (`/dev/video0`)
O Compose mapeia o device direto. No Kubernetes o caminho correto é um **device plugin**; o atalho é `privileged: true` + `hostPath`, que funciona mas prende o pod naquele nó e abre o container.

**Decisão recomendada:** tratar webcam como coisa de desenvolvimento e, no cluster, consumir **só RTSP**. Câmera de verdade em canteiro é IP/RTSP; a webcam existe para teste local. Isso remove o problema em vez de contorná-lo — e é uma resposta forte em entrevista: *"a saída não foi fazer o Kubernetes suportar meu setup de dev, foi separar dev de produção."*

### 5.2 GPU
Precisa de driver NVIDIA no nó + `nvidia-device-plugin`, e aí se pede recurso:

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
```

Consequência prática: só cabe um pod por GPU. Escalar réplica de inferência exige mais GPU ou fila na frente. Vale registrar isso no `docs/gpu-on-demand-plan.md`, que já existe.

### 5.3 Workers por câmera — o motivo de `replicas: 1`
O backend hoje mantém um `StreamSource` por câmera **em memória do processo**. Subir para 2 réplicas faz as duas conectarem nas mesmas câmeras: trabalho duplicado, alerta duplicado.

Escalar de verdade pede uma das duas:
- separar o processamento de câmera em um **Deployment próprio**, com atribuição de câmeras por réplica (sharding) ou eleição de líder;
- ou uma fila, com o worker consumindo trabalho em vez de descobrir câmera sozinho.

Enquanto isso não existir, **`replicas: 1` no backend é a resposta correta**, não uma limitação envergonhada. Saber *por que* não dá para escalar vale mais que escalar errado.

### 5.4 RTSP (mediamtx) e Cloudflare Tunnel
- **mediamtx:** RTSP usa UDP; o Ingress só entende HTTP. Exponha como `Service` do tipo `NodePort`/`LoadBalancer` com `protocol: UDP`, ou deixe o stack de teste no Compose mesmo.
- **cloudflared:** vira um `Deployment` simples com o token em `Secret`. É saída, não entrada — não precisa de Ingress.

### 5.5 Bind mount de `./ml/data/feedback`
Hoje o feedback do admin cai direto na pasta do repo para o `merge_feedback.sh` achar. No cluster isso vira PVC, e o script não enxerga mais.

Opções: `kubectl cp` para extrair, ou um `CronJob` que empacota o feedback e envia para storage. O `CronJob` é o caminho natural e fecha o loop de active learning sem intervenção manual — bom item de roadmap.

---

## 6. Ordem sugerida (um fim de semana)

1. `/healthz` e `/readyz` no backend — é pré-requisito de tudo
2. k3s instalado, imagens importadas
3. Postgres com PVC de pé, `pg_isready` verde
4. Backend com as três probes (startup/liveness/readiness)
5. Frontend com 2 réplicas + Ingress
6. Matar pod, escalar, rollout restart, rollout undo — ver o cluster se curar
7. Anotar aqui o que quebrou e por quê

---

## 7. O que isso destrava

Depois do passo 6, a frase verdadeira passa a ser:

> "Rodei o Vigilante.AI em k3s: Deployments, StatefulSet para o Postgres, Service, Ingress, ConfigMap/Secret, PVC e as três probes. O backend fica em réplica única de propósito, porque o estado de câmera vive no processo — escalar exige sharding de câmera ou fila antes. Operar cluster gerenciado em produção corporativa, ainda não."

Isso é honesto e cobre a maior parte do que se pergunta sobre Kubernetes numa entrevista de backend/IA. O parágrafo do meio é o que separa quem entende de quem decorou `kubectl apply`.

---

## 8. Execução real (26/07/2026) — o que quebrou e por quê

Cluster subiu e o domínio voltou. Quatro coisas quebraram no caminho, nenhuma
prevista neste doc:

1. **`DiskPressure` travou tudo em `Pending`.** O disco estava em 98% e o kubelet
   aplicou a taint `node.kubernetes.io/disk-pressure:NoSchedule`. Nenhum pod
   agenda com essa taint. Liberamos 172 GB de build cache do Docker
   (`docker builder prune -af`) e a taint caiu sozinha, mas só depois de ~4 min:
   o kubelet tem um período de transição antes de limpar a condição.

2. **O kubelet apagou as imagens da aplicação.** Enquanto o node estava sob
   `DiskPressure`, o garbage collector de imagem do kubelet remove imagens sem
   container ativo. Como o `docker compose down` tinha acabado de rodar, as
   imagens do vigilante ficaram órfãs e foram coletadas. Foi preciso rebuildar.
   Lição: com `--docker`, o kubelet manda nas SUAS imagens do Docker também.

3. **OpenCV 5 quebrou o import.** `ultralytics` puxa `opencv-python` transitivo
   sem teto, e o rebuild sem cache resolveu para 5.0.0, que tirou
   `cv2.CascadeClassifier` do módulo principal. `AttributeError` no import,
   CrashLoopBackOff. Corrigido com teto `<5` nas duas variantes em
   `backend/requirements.txt`. **Isto quebraria o compose também**, em qualquer
   rebuild limpo, não é problema de Kubernetes.

4. **`/readyz` pedia algo que nunca acontecia.** A probe afirma `model`, mas o
   `load_model()` só era chamado por `StreamSource`. Pod sem câmera ativa nunca
   ficava `Ready` e nunca recebia tráfego. Passamos a carregar o YOLO no
   startup, o que também usa o `startupProbe` para o que ele foi dimensionado.

**Provas de cluster executadas:** `delete pod` (auto-recuperou em ~5s),
`scale --replicas=3` e volta para 2, `rollout restart` e `rollout undo`
(revisão 3), todas verdes.

**Instalação usada**, que dispensa `ctr images import` e sudo no dia a dia:

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--docker --write-kubeconfig-mode 644" sh -
```
