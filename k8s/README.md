# Runbook — Vigilante.AI em k3s

> **Estes comandos são para o operador da máquina rodar.** Nada aqui foi
> executado por automação: instalar k3s, importar imagem no containerd e criar
> Secret são decisões de quem é dono do nó. Este arquivo é a receita, não o log.

**Escopo honesto:** k3s numa máquina **não é alta disponibilidade**. É
Kubernetes de verdade (mesma API, mesmos manifestos, mesmas probes), com um nó
só. Serve para aprendizado, homologação e para este deploy. Um nó cai e a
aplicação cai com ele: não substitui cluster gerenciado.

O que os manifestos declaram:

| Arquivo | Objetos |
|---|---|
| `00-namespace.yaml` | Namespace `vigilante` + ConfigMap `backend-config` |
| `10-postgres.yaml` | Service headless + StatefulSet com `volumeClaimTemplates` e `pg_isready` |
| `20-backend.yaml` | PVC `vigilante-data` + Service + Deployment (`replicas: 1`, três probes) |
| `30-frontend.yaml` | Service + Deployment (`replicas: 2`) |
| `40-mediamtx.yaml` | Service ClusterIP RTSP/TCP + Deployment com sidecar `ffmpeg-loop` |
| `50-cloudflared.yaml` | Deployment do tunnel (saída, sem Service) |
| `60-ingress.yaml` | Ingress Traefik em `vigilanteai.outis.com.br` |

---

## 1. Instalar k3s

```bash
curl -sfL https://get.k3s.io | sh -
sudo k3s kubectl get nodes          # Ready antes de seguir
```

Para usar `kubectl` sem `sudo k3s` na frente:

```bash
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown "$USER:$USER" ~/.kube/config
kubectl get nodes
```

O k3s já traz Traefik como Ingress Controller e `local-path` como StorageClass
padrão. Nenhum dos dois precisa de instalação.

## 2. Buildar as duas imagens

```bash
cd /home/badmuriss/Documents/vigilante-ai
docker build -t vigilante-backend:latest  ./backend
docker build -t vigilante-frontend:latest ./frontend
```

`backend/best.pt` (22 MB) entra na imagem pelo `COPY . .`, então o modelo
viaja com o container. O entrypoint roda `alembic upgrade head` antes do
uvicorn: migração acontece no start do pod, não em passo separado.

## 3. Importar no containerd do k3s

Não há registry nesta máquina. O k3s não vê o daemon do Docker, então a imagem
precisa ser injetada no containerd dele:

```bash
docker save vigilante-backend:latest  | sudo k3s ctr images import -
docker save vigilante-frontend:latest | sudo k3s ctr images import -
sudo k3s ctr images ls | grep vigilante
```

Os manifestos usam `imagePullPolicy: IfNotPresent` por causa disso. Com
`Always` o pod tentaria puxar de registry inexistente e ficaria em
`ErrImagePull`.

Repetiu o build? Importa de novo **e** força a troca:

```bash
kubectl -n vigilante rollout restart deploy/backend
```

`:latest` não muda de nome, então o Kubernetes não percebe sozinho que o
conteúdo mudou. Tag versionada (`:a3`, `:git-sha`) resolve isso de verdade.

## 4. Criar os Secrets

Nenhum segredo está em arquivo versionado, e nenhum vai entrar. Os valores
saem do `.env` local (que é gitignored). Prefixo `VIGILANTE_` obrigatório: é o
`env_prefix` do `Settings` em `backend/app/config.py`.

```bash
kubectl create namespace vigilante   # ou aplique 00-namespace.yaml antes

# Senha do Postgres. A MESMA senha aparece na DATABASE_URL do backend abaixo.
kubectl -n vigilante create secret generic postgres-secrets \
  --from-literal=POSTGRES_PASSWORD='TROQUE-ESTA-SENHA'

# Backend. A DATABASE_URL é Secret, não ConfigMap, porque carrega a senha.
kubectl -n vigilante create secret generic backend-secrets \
  --from-literal=VIGILANTE_DATABASE_URL='postgresql+psycopg2://vigilante:TROQUE-ESTA-SENHA@postgres:5432/vigilante' \
  --from-literal=VIGILANTE_JWT_SECRET="$(openssl rand -hex 32)" \
  --from-literal=VIGILANTE_NOTIFY_ENCRYPTION_KEY='<fernet key>' \
  --from-literal=VIGILANTE_WHATSAPP_PHONE_NUMBER_ID='<id do número da plataforma>' \
  --from-literal=VIGILANTE_WHATSAPP_ACCESS_TOKEN='<token Meta>' \
  --from-literal=VIGILANTE_WHATSAPP_APP_SECRET='<app secret Meta>' \
  --from-literal=VIGILANTE_WHATSAPP_VERIFY_TOKEN='<verify token do webhook>' \
  --from-literal=VIGILANTE_WHATSAPP_TEMPLATE_NAME='<nome do template aprovado>' \
  --from-literal=VIGILANTE_DEEPSEEK_API_KEY='<chave DeepSeek>' \
  --from-literal=VIGILANTE_OPENROUTER_API_KEY='<chave OpenRouter>' \
  --from-literal=VIGILANTE_OPENAI_API_KEY='<chave OpenAI>' \
  --from-literal=VIGILANTE_HF_TOKEN='<token Hugging Face>'

# Cloudflare Tunnel (token do Named Tunnel no Zero Trust).
kubectl -n vigilante create secret generic cloudflared-secrets \
  --from-literal=TUNNEL_TOKEN='<token do tunnel>'
```

`VIGILANTE_NOTIFY_ENCRYPTION_KEY` é uma Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Atalho preguiçoso, se o `.env` já tem tudo e **só** variáveis sensíveis:
`--from-env-file=.env`. Não use aqui: o `.env` deste repo mistura config e
segredo, e o Secret viraria depósito de tudo.

> Secret do Kubernetes é **base64, não criptografia**. Quem tem `get secret` no
> namespace lê o valor em claro. Em cluster de verdade: Sealed Secrets, SOPS ou
> External Secrets, e RBAC restringindo `get secret`.

Rotação de credencial:

```bash
kubectl -n vigilante create secret generic backend-secrets \
  --from-literal=... --dry-run=client -o yaml | kubectl apply -f -
kubectl -n vigilante rollout restart deploy/backend   # envFrom só lê no start
```

## 5. Ajustar o hostPath do mediamtx

`40-mediamtx.yaml` monta `./media` e `./scripts` do nó por `hostPath`. Se o
checkout não está em `/home/badmuriss/Documents/vigilante-ai`, corrija os dois
caminhos no fim do arquivo antes de aplicar — `type: Directory` faz o pod
falhar cedo e explícito se o caminho não existir, em vez de subir vazio.

## 6. Aplicar

A ordem importa: namespace e config antes de tudo, banco antes do backend.
`kubectl apply -f k8s/` já aplica em ordem alfabética, e é por isso que os
arquivos têm prefixo numérico.

```bash
kubectl apply -f k8s/
kubectl -n vigilante get pods -w
```

Esperado: `postgres-0` pronto primeiro; `backend` fica `0/1` por até ~2min
enquanto roda a migração e carrega o YOLO (é o `startupProbe` trabalhando, não
é travamento); `frontend` sobe 2 pods.

```bash
kubectl -n vigilante get pods,svc,ingress,pvc
kubectl -n vigilante logs -f deploy/backend
```

Conferir as probes por fora:

```bash
kubectl -n vigilante port-forward deploy/backend 8000:8000 &
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/healthz   # 200
curl -s localhost:8000/readyz                                     # {"ready":true,...}
```

Cadastrar a câmera RTSP no painel apontando para o DNS interno:

```
rtsp://mediamtx:8554/canteiro2
```

(um path por MP4 em `./media`; `RTSPSource` já usa transporte TCP).

Entrada pública, com o tunnel de pé:

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://vigilanteai.outis.com.br/api/webhooks/whatsapp
```

Qualquer coisa diferente de `502` significa que a cadeia
Cloudflare → frontend → Next rewrite → backend está fechada. `403`/`405` são
respostas legítimas do webhook.

## 7. Os quatro comandos de prova

É aqui que o Kubernetes deixa de ser "compose com YAML mais longo". Rode com
`kubectl -n vigilante get pods -w` em outro terminal.

```bash
# 1. Autocura: o pod some e o ReplicaSet recria sozinho.
kubectl -n vigilante delete pod -l app=backend

# 2. Escala horizontal: o frontend é stateless, então escala de graça.
#    NÃO faça isso com o backend: StreamSource por câmera vive na memória do
#    processo e duas réplicas duplicariam inferência e alerta.
kubectl -n vigilante scale deploy/frontend --replicas=3

# 3. Rolling update: sobe o novo, espera readiness, aí mata o velho.
kubectl -n vigilante rollout restart deploy/backend
kubectl -n vigilante rollout status deploy/backend

# 4. Rollback: volta para a revisão anterior.
kubectl -n vigilante rollout undo deploy/backend
kubectl -n vigilante rollout history deploy/backend
```

O que observar em cada um:

1. `delete pod` — sem downtime? **Não**, com `replicas: 1` o backend fica fora
   durante o restart. Isso é a consequência honesta do estado em memória, não
   um bug do cluster.
2. `scale` — o Service passa a balancear entre 3 endpoints imediatamente
   (`kubectl -n vigilante get endpoints frontend`).
3. `rollout restart` — com `maxUnavailable: 0` o pod velho só morre depois que
   o novo passa readiness. Como `replicas: 1`, isso significa 2 pods
   simultâneos por alguns segundos, e ambos abrindo a mesma câmera nesse
   intervalo. Alerta duplicado durante a janela é esperado.
4. `rollout undo` — com tag `:latest` nas duas revisões, o rollback volta a
   config, não o binário. Tag versionada é o que torna o rollback real.

Depois, anotar em `docs/kubernetes-k3s.md` o que quebrou e por quê.

## 8. Diagnóstico rápido

```bash
kubectl -n vigilante describe pod <pod>            # Events primeiro, sempre
kubectl -n vigilante logs <pod> --previous         # log do container que morreu
kubectl -n vigilante logs deploy/mediamtx -c ffmpeg-loop
kubectl -n vigilante get events --sort-by=.lastTimestamp | tail -20
```

| Sintoma | Causa provável |
|---|---|
| `ErrImagePull` / `ImagePullBackOff` | imagem não importada no containerd (passo 3) |
| backend em `CrashLoopBackOff` no boot | Secret ausente ou `VIGILANTE_DATABASE_URL` com senha errada |
| backend `Running` mas `0/1` para sempre | `/readyz` em 503: banco fora ou modelo não carregou |
| `Pending` no `postgres-0` | PVC sem StorageClass; `kubectl get sc` deve mostrar `local-path (default)` |
| mediamtx sobe e não tem stream | `hostPath` errado (passo 5) ou nenhum MP4 em `./media` |
| 502 no domínio público | frontend sem endpoint pronto, ou hostname do tunnel apontando para lugar errado |

## 9. Derrubar

```bash
kubectl delete -f k8s/                 # mantém os PVCs
kubectl -n vigilante delete pvc --all  # apaga o banco e os alertas de vez
```

`kubectl delete namespace vigilante` leva tudo junto, PVC incluído.
