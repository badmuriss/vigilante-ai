# Documentação do Vigilante.AI

Este diretório separa material acadêmico, documentação ativa do produto, operação e arquivos históricos. Novas entregas devem nascer na pasta da fase correspondente. O ZIP final só entra em `entrega/` dentro dessa fase.

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `01-academico/startup-one/` | Entregas da FIAP organizadas por fase |
| `01-academico/enterprise-challenge/` | Materiais do Enterprise Challenge |
| `02-produto/` | Visão e arquitetura funcional do produto |
| `03-operacao-e-infra/` | Nuvem, Kubernetes, integrações e roadmap técnico |
| `participantes/` | Fotos da equipe reutilizadas nas apresentações |
| `90-arquivo/` | Pacotes finais e cópias históricas, sem uso como fonte ativa |

## Startup One

- [Fase 2: validação do problema](./01-academico/startup-one/fase-02-validacao-do-problema/)
- [Fase 3: modelagem do negócio](./01-academico/startup-one/fase-03-modelagem-do-negocio/)
- [Fase 4: protótipo](./01-academico/startup-one/fase-04-prototipo/)
- [Fase 5: mercado e MVP](./01-academico/startup-one/fase-05-mercado-mvp/)

## Documentação ativa

- [Arquitetura técnica](./02-produto/arquitetura-tecnica.md)
- [Documento inicial do Startup One](./02-produto/documentacao-startup-one.md)
- [Plano de GPU sob demanda](./03-operacao-e-infra/gpu-on-demand-plan.md)
- [Plano GCP para o MVP](./03-operacao-e-infra/gcp-mvp.md)
- [Operação em Kubernetes/k3s](./03-operacao-e-infra/kubernetes-k3s.md)
- [Roadmap do TCC](./03-operacao-e-infra/roadmap-tcc-outubro-2026.md)
- [Integração WhatsApp](./03-operacao-e-infra/whatsapp-template-guia.md)

## Convenção para novas fases

Cada fase pode conter:

```text
fase-N-nome/
├── fontes/       # Markdown, planilhas e arquivos editáveis
├── assets/       # Imagens usadas no documento e nos slides
├── build/        # Scripts de geração
└── entrega/      # Apenas arquivos finais e o ZIP enviado
```

Não edite arquivos em `90-arquivo/`. Eles existem para rastreabilidade de entregas anteriores.
