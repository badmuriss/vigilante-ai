# Entrega da Atividade 3 — Enterprise Challenge Claro

## Por que

A Atividade 3 pede vídeo pitch de até 5 minutos (com ênfase em demonstração funcional), slides em PDF com links de vídeo e repositório no primeiro slide, e o código versionado no GitHub. A plateia é a Claro, cujo tema é **convergência de interfaces conversacionais**, então o protagonista da entrega é o hub, não a visão computacional.

Três fatos do estado atual definem o escopo:

1. **A maior evolução do projeto está fora do git.** 35 mudanças não commitadas desde 28/05, concentradas na camada de canal: migração de WhatsApp por tenant para número único de plataforma com tenant resolvido por telefone (`whatsapp_operators`, migração `0005`), push de revisão com botões de decisão, hardening do webhook, e cobertura de teste quase dobrada. O pitch da Atividade 2 é do commit anterior, então **nada disso foi apresentado**. Delta não commitado é delta que não existe para o avaliador.

2. **Há uma dívida declarada à Claro que o roteiro depende.** A Atividade 1 prometeu "foto anonimizada" dentro do cenário principal e listou LGPD como risco número um com mitigação concreta. O código detecta faces mas não borra nada antes de persistir ou enviar. O roteiro da demo diz "com o rosto borrado" na tela, então sem o blur a fala é falsa.

3. **A Atividade 2 não deixou prova visual do WhatsApp.** Os cinco screenshots dos slides são todos de tela web. O canal foi afirmado no texto e provavelmente mostrado ao vivo, mas não ficou registrado. A demo desta entrega precisa colocar o celular na tela.

## O que

Entregar, nesta ordem de dependência:

1. **Commit e push do delta do hub**, incluindo a migração `0005_whatsapp_operators.py` e o teste `test_whatsapp_webhook.py`, que hoje estão untracked.
2. **Blur facial** nos artefatos destinados a humano (frame anotado, thumbnail e portanto a imagem enviada no WhatsApp), preservando o frame raw sem borrão para treino.
3. **Deploy em k3s**, com `/healthz` e `/readyz` como pré-requisito, mediamtx dentro do cluster e cloudflared como Deployment.
4. **`slides-atividade3.html`**, nove slides, no mesmo sistema visual de `slides-atividade2-implementacao.html`, com links de vídeo e repositório no slide 1.
5. **Ajuste do `roteiro-atividade3.md`** para valor qualitativo (sem número medido) e slide próprio de evolução de arquitetura.
6. **Captura dos assets de WhatsApp** e gravação do vídeo com plano B.

## Fora de escopo

- Coluna `feedback_source` para medir "resolução sem humano". O slide de valor será qualitativo por decisão do autor, então a migração não se paga neste ciclo.
- Contagem de token para custo por conversa. Mesma razão.
- Ciclo de retreino como protagonista do vídeo. É diferencial de banca de outubro, não de plateia Claro.
- Teams conversacional, Slack, handoff humano, agendamento. Ficam como roadmap declarado no slide.
- GPU on-demand / RunPod.
