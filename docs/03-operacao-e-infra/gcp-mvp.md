# GCP e Modal para a demonstração do MVP

Este plano publica o stack atual com o menor número de mudanças. Ele serve para a atividade acadêmica. Não define a arquitetura de produção.

## Estado local em 12 de agosto de 2026

O `gcloud` desta máquina está autenticado como `murilo@outis.com.br` e aponta para o projeto `outis-prospecta`. Nenhum recurso foi criado ou alterado. Antes do deploy, autentique `badmuriss@gmail.com` e selecione um projeto exclusivo do Vigilante.AI.

## Desenho da prova de conceito

| Componente | Serviço | Configuração inicial |
|---|---|---|
| Front-end | Cloud Run | Sem GPU, mínimo 0, máximo 2 |
| API | Cloud Run | CPU, mínimo 0, máximo 2 |
| Coletor de câmeras | Compute Engine | `e2-small`, ligado no horário de cobertura |
| Inferência | Modal | T4, mínimo 0, janela ociosa de 10 segundos |
| Banco | Cloud SQL PostgreSQL | `db-f1-micro`, apenas demonstração |
| Frames | Cloud Storage | Bucket regional e retenção curta |
| Imagens Docker | Artifact Registry | Um repositório regional |
| Segredos | Secret Manager | JWT, criptografia e tokens externos |

O replay da entrega pode usar o back-end atual. O piloto real exige separar API, coletor e inferência. O coletor acessa o RTSP pela VPN, identifica movimento em CPU e envia apenas lotes de frames para a Modal.

## Controles de custo antes do deploy

1. Fazer upgrade da conta de faturamento. O modo gratuito não libera GPU em VM nem aumento de quota.
2. Criar budget de US$ 50. O budget alerta, mas não desliga recursos.
3. Configurar alertas em 50%, 80% e 100%.
4. Fixar mínimo zero, concorrência máxima inicial de uma T4 e janela de desligamento de 10 segundos na Modal.
5. Remover IP reservado que não estiver em uso.
6. Desligar o coletor e a prova após a gravação.

## Ordem de implantação

```text
1. Projeto e billing
2. APIs e Artifact Registry
3. Cloud SQL e usuário do banco
4. Bucket de frames
5. Segredos
6. Build e push dos contêineres
7. Back-end Cloud Run em CPU para o primeiro smoke test
8. Front-end Cloud Run
9. Migrations
10. Função T4 na Modal
11. Smoke test e gravação
```

## Variáveis necessárias

```text
VIGILANTE_DATABASE_URL
VIGILANTE_JWT_SECRET
VIGILANTE_NOTIFY_ENCRYPTION_KEY
VIGILANTE_BLOB_STORAGE_PATH=/mnt/alerts
VIGILANTE_MODEL_PATH=/app/best.pt
VIGILANTE_ALLOW_OPEN_REGISTRATION=0
NEXT_BACKEND_INTERNAL_URL=<URL DO BACK-END>
```

Tokens de WhatsApp, Teams e provedores de LLM devem entrar pelo Secret Manager. Não coloque segredo em YAML, histórico do shell ou imagem Docker.

## Critérios de aceite

- `/healthz` retorna HTTP 200.
- `/readyz` confirma banco e modelo.
- O front-end abre pela URL pública.
- Login persiste após nova revisão do Cloud Run.
- Um replay RTSP autorizado gera alerta.
- O alerta permanece no banco após reinício da instância.
- O frame anonimizado abre pelo fluxo autenticado.
- A função Modal volta a zero contêineres após a demonstração.
- Billing mostra budget ativo e nenhuma GPU ociosa.

## Limites conhecidos

- `db-f1-micro` não tem SLA e a documentação do Google restringe seu uso a teste e desenvolvimento.
- O worker de câmera vive no processo do back-end. Escala a zero encerra o stream, o que é desejável fora da demonstração.
- O piloto precisa separar o worker antes de oferecer cobertura por horário.
- Modal e GCP têm créditos e limites de gastos separados.

O cálculo atual e as fontes oficiais estão em [`research/gpu-serverless-por-movimento-2026-08-12.md`](../../research/gpu-serverless-por-movimento-2026-08-12.md). O estudo anterior de Cloud Run GPU permanece como alternativa e histórico de decisão.
