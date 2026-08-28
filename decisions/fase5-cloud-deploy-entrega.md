# Decisão: concluir a entrega da Fase 5 com AWS RDS

- Revision: 2
- Mode: light_spec
- Status: approved by user request
- Date: 2026-08-28
- Decision ID: `decision-97939a88a032429d`

## Objective

Entregar o MVP funcional, comprovar PostgreSQL em nuvem, registrar os custos e gerar o pacote que o grupo usará para gravar o pitch e enviar à FIAP ON.

## Decision

Usar Amazon RDS for PostgreSQL em `us-east-1` como banco em nuvem. Executar frontend, API e processamento YOLO no k3s da máquina de demonstração, com publicação pelo Cloudflare Tunnel. Essa divisão atende o requisito literal da atividade e preserva o runtime que já funciona.

Configurar RDS PostgreSQL 16, `db.t4g.micro`, Single-AZ, 20 GiB gp3, sem retenção prolongada de backup. Habilitar `pgvector`, exigir TLS e liberar a porta do banco apenas para o IP público usado na entrega.

Não migrar a aplicação completa para EC2, ECS, Lambda, Cloud Run ou Cloudflare nesta fase. Esses serviços aumentariam o custo, o tempo de estabilização e o número de pontos de falha sem melhorar a rubrica, que exige banco em nuvem e uma demonstração funcional.

## Invariants

- Não imprimir, versionar ou embutir senhas, tokens, chaves ou URLs de banco com credenciais.
- Criar recursos apenas na conta AWS confirmada e na região `us-east-1`.
- Não usar a identidade raiz para a rotina de implantação. Um usuário IAM temporário e limitado executa as operações do projeto.
- Manter o acesso ao PostgreSQL limitado a um CIDR `/32` e exigir SSL.
- Preservar PostgreSQL, `pgvector`, SQLAlchemy, Alembic e o modelo YOLO atual.
- Manter uma única instância RDS e nenhum recurso de alta disponibilidade.
- Criar orçamento antes do banco. O orçamento é alerta, não bloqueio de cobrança.
- Tratar os créditos AWS como saldo de cobrança, não como autorização para deixar recursos ociosos.
- Tratar R$ 70,00 e US$ 4,60 da Twilio como valores informados pela equipe, com comprovantes pendentes.
- Preservar todas as mudanças locais existentes no checkout.
- Não excluir o banco automaticamente. A limpeza exige comando explícito após gravação ou correção.

## Scope

### Included

- Revisar e concluir a fonte de replay usada na demonstração.
- Criar automação AWS idempotente para orçamento, rede, segurança, RDS, migrations, verificação e limpeza.
- Gerar credenciais localmente sem exibi-las e manter os segredos fora do Git.
- Implantar PostgreSQL com `pgvector` e executar as migrations existentes.
- Validar conexão TLS, persistência, autenticação, replay, alerta, histórico e evidência.
- Atualizar documentação acadêmica, custos, arquitetura, progresso do MVP e referências.
- Atualizar os slides e exportar a apresentação em PDF.
- Preparar roteiro de até cinco minutos, plano de gravação e checklist de handoff.
- Gerar um ZIP final validável, com espaço explícito para o link do vídeo.
- Criar um verificador único em `scripts/verify-fase5.sh`.

### Excluded

- Gravar, editar ou publicar o vídeo.
- Enviar o ZIP à FIAP ON ou cadastrar o grupo.
- Piloto com câmera de cliente, VPN de obra ou dados pessoais reais.
- Hospedagem permanente de frontend, API ou inferência.
- GPU dedicada e migração de PostgreSQL para D1.
- Remoção automática do RDS antes de o grupo concluir a gravação.

## Cost guardrail

- Saldo autenticado depois do deploy: US$ 160,00. A diferença em relação ao screenshot anterior de US$ 120,00 corresponde a dois créditos de atividade de US$ 20,00.
- Custo estimado do RDS público: US$ 17,63 por 730 horas.
- Janela recomendada: até sete dias, estimada em US$ 4,06.
- Budget AWS: US$ 10,00 mensais, com notificações quando houver destinatário configurado.
- Stop condition financeiro: não criar recurso cuja estimativa ultrapasse US$ 10,00 durante a janela da entrega.
- A atividade AWS de criação de RDS pode conceder mais US$ 20,00, mas o bônus não entra no orçamento até ser creditado.

Fontes, premissas e evidência autenticada estão em `research/2026-08-28-custo-aws-fase5.md`.

## Implementation slices

1. Consolidar o runtime local e o replay.
2. Criar os scripts AWS e o verificador da entrega.
3. Criar o orçamento e a função IAM limitada.
4. Implantar RDS, habilitar `pgvector` e executar migrations.
5. Rodar a aplicação com o RDS e validar os fluxos do MVP.
6. Atualizar documento, slides, custos e roteiro.
7. Gerar PDFs, evidências visuais, checksum e ZIP.

## Acceptance checks

- A automação recusa conta, região ou CIDR divergentes do arquivo local de estado.
- O banco exige TLS e não aceita tráfego fora do CIDR autorizado.
- `SELECT version()` e `SELECT extversion FROM pg_extension WHERE extname='vector'` funcionam.
- Alembic chega ao `head` no RDS.
- `/healthz` responde HTTP 200 e `/readyz` confirma banco e modelo.
- O primeiro cadastro, login e consulta autenticada funcionam.
- Um replay autorizado inicia e o painel mostra o estado da câmera.
- Alertas e metadados persistem após reinicialização da API.
- A evidência abre pelo fluxo autenticado.
- O ledger separa gasto pago, crédito, estimativa e rateio.
- Documento e slides descrevem apenas o que foi comprovado.
- O ZIP abre em uma pasta limpa e contém documentação PDF, apresentação PDF, links, checklist e referência do código no GitHub.
- O vídeo e o cadastro do grupo permanecem como os únicos passos externos.
- `scripts/verify-fase5.sh` termina com código zero.

## Visual scope

- Visual-Scope: diálogo de adição de câmera | replay vazio e preenchido | desktop e mobile | fluxo usado na demonstração.
- Visual-Scope: lista de câmeras | replay offline e online | desktop e mobile | estado exibido no pitch.
- Visual-Scope: documento acadêmico | todas as páginas | PDF A4 | artefato entregue ao professor.
- Visual-Scope: apresentação | todos os slides | PDF 16:9 | suporte visual do pitch.

## Escalation triggers

- A conta AWS perde acesso, crédito ou permissão para Amazon RDS.
- O IP público muda durante a validação e bloqueia a conexão.
- O RDS não inicia com PostgreSQL 16, 20 GiB gp3 ou `db.t4g.micro`.
- A estimativa ultrapassa US$ 10,00 para a janela de entrega.
- O modelo não carrega ou o replay não abre no runtime local.
- O conteúdo aprovado exige hospedar a aplicação inteira na internet.

## Reduction triggers

- Se a interface existente já cobrir o replay e passar na validação visual, não redesenhar páginas.
- Se os documentos atuais já contiverem uma seção correta, editar apenas os fatos de nuvem e evidência.
- Se o ZIP atual tiver a estrutura exigida, substituir os artefatos e acrescentar checksum, sem criar outro formato de pacote.

## Check and stop condition

- Check: `scripts/verify-fase5.sh`
- Stop: o verificador passa, a evidência AWS está registrada e nenhum item executável permanece pendente.

## External handoff

O grupo ainda precisa gravar e publicar o vídeo não listado, inserir a URL no arquivo de links, conferir nomes e RMs e fazer uma única entrega na FIAP ON. Esses atos não serão marcados como concluídos sem evidência.
