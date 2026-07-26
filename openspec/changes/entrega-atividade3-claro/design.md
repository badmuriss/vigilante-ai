# Design — Entrega da Atividade 3 (Claro)

## Vocabulário do domínio

| Termo | Significado neste projeto |
|---|---|
| **Operador** | Pessoa (telefone) que age em nome de uma empresa pelo WhatsApp. Recebe alerta e conversa com o agente. Tabela `whatsapp_operators`. |
| **Canal** | Superfície conversacional: `ui` (painel) ou `whatsapp`. |
| **Ponto de convergência** | `ChatService.handle_message`, onde os dois canais se encontram. |
| **Camada de identidade** | Resolução de empresa a partir do telefone de quem falou, na entrada do WhatsApp. |
| **Artefato de revisão** | Imagem destinada a humano: frame anotado e thumbnail. |
| **Artefato de treino** | Frame raw, sem anotação, usado para retreinar o modelo. |

## Decisão 1 — Blur num único choke point, e o raw fica limpo

`AlertService.add_alert` (`backend/app/services/alert_service.py`) já é o ponto por onde todo alerta passa. Recebe `frame` (anotado) e `raw_frame` (limpo) e produz três JPEGs: `thumb`, `frame`, `raw`. O notificador de WhatsApp consome os caminhos persistidos, não o frame em memória.

Logo: **borrar dentro de `add_alert`, antes de encodar `thumb_jpeg` e `full_jpeg`, cobre painel e WhatsApp de uma vez.** Nenhum chamador precisa saber que existe blur, e nenhum caminho futuro escapa por esquecimento. É a definição de módulo profundo: interface pequena, complexidade escondida.

**O raw não é borrado.** Motivo técnico, não preguiça: capacete fica na cabeça, colado na região do rosto. Borrar ali degrada exatamente o sinal que o YOLO precisa aprender para `hardhat` e `no_hardhat`. A mitigação de privacidade do raw é de acesso e retenção, não de pixel, e é o que o próprio roadmap já dizia ("acesso raw restrito a admin/supervisor, retenção curta").

**Teste de deleção aplicado:** se apagar a função de blur e distribuir a chamada nos chamadores, a complexidade não desaparece, ela se multiplica por chamador e cria a chance de um caminho novo enviar imagem sem borrão. Fica no choke point.

**Fonte das caixas de rosto:** `Detector` já detecta face (`_detect_faces`, `FACE_CLASS_KEY`) e `stream.py` já tem `visible_faces` em escopo no ponto da chamada (`stream.py:540`). Passar as caixas como parâmetro novo e opcional de `add_alert` é mais honesto que redetectar dentro do serviço, porque evita rodar cascade duas vezes no mesmo frame.

## Decisão 2 — Identidade por MSISDN é a tese do pitch, com tradeoff explícito

Já está implementado no working tree. O que esta mudança faz é **documentar como decisão** e transformar em slide, porque contradiz o que foi apresentado na Atividade 2.

- **Antes:** credencial Meta por cliente em `whatsapp_configs` (`phone_number_id`, `access_token`, `app_secret` e `verify_token` cifrados com Fernet). Tenant resolvido pelo `phone_number_id` de destino. HMAC validado com o segredo daquele cliente.
- **Agora:** um número de plataforma, credenciais em `settings.WHATSAPP_*`. Tenant resolvido pelo **telefone do remetente** via `whatsapp_operators` (`phone` UNIQUE global). HMAC validado contra o segredo global. `whatsapp_configs` sobrevive magra, só com `enabled` e `include_image`.

**Tradeoff registrado:** trocou isolamento de credencial por onboarding sem fricção. O isolamento de **dados** por empresa continua intacto. Limitação conhecida e aceita: um telefone pertence a uma empresa, então encarregado terceirizado que atende duas construtoras não cabe hoje.

**Consequência de pitch:** a frase do slide 7 da Atividade 2 ("credenciais do WhatsApp de cada cliente cifradas") **não vale mais**. Vai um slide próprio assumindo a evolução, porque mentor de mercado respeita decisão explicada e desconfia de mudança silenciosa.

## Decisão 3 — k3s entra, mediamtx dentro do cluster

Segue `docs/kubernetes-k3s.md`, com dois desvios do que aquele doc propôs:

- **mediamtx vira Deployment + Service ClusterIP**, e o backend consome `rtsp://mediamtx:8554/<stream>` por DNS interno, RTSP sobre TCP. O doc tratava RTSP como parte difícil por causa de UDP, mas o tráfego é interno ao cluster e não precisa de NodePort nem de exposição UDP.
- **Sem GPU.** Uma câmera RTSP em CPU basta, porque o protagonista da demo é o hub.

`replicas: 1` no backend é decisão, não limitação: `StreamSource` por câmera vive na memória do processo, então duas réplicas duplicam trabalho e alerta. Frontend fica em 2 réplicas porque é stateless.

`/healthz` e `/readyz` são pré-requisito de tudo. O `/api/status` atual não serve como probe porque chama `_ensure_legacy_camera()`, ou seja, tem efeito colateral e depende de câmera.

## Decisão 4 — Valor qualitativo neste ciclo

O slide de valor não cita número medido. Consequência aceita: a meta de 60 a 70% de resolução sem humano, publicada na Atividade 1 e na mentoria, fica sem resposta numérica. Mitigação no roteiro: se um mentor perguntar o número, a resposta é que ainda não foi medido e o que existe hoje é o mecanismo, não a série histórica. Melhor isso que número inventado no ar.

## Alternativas rejeitadas

| Alternativa | Por que não |
|---|---|
| Coluna `feedback_source` no `Alert` para medir resolução no canal | Slide de valor é qualitativo por decisão do autor. Sem número na tela, a migração não se paga neste ciclo. Fica como candidata natural para a banca de outubro. |
| Capturar `usage` do LLM para custo por conversa | Mesma razão. Se voltar, o caminho barato é script offline lendo as conversas em JSONB com tiktoken, sem tocar no hot path. |
| Borrar também o frame raw | Degrada o sinal de treino de capacete, que fica adjacente ao rosto. Privacidade do raw se resolve por acesso e retenção. |
| Blur nos chamadores em vez de em `add_alert` | Multiplica a chance de um caminho futuro enviar imagem sem borrão. |
| Redetectar faces dentro do `AlertService` | Rodaria o cascade duas vezes no mesmo frame. As caixas já existem no chamador. |
| Manter credencial Meta por cliente | Já rejeitado no código. Exigia o cliente criar WABA e app na Meta antes de ver valor. |
| mediamtx com NodePort/UDP no k3s | Tráfego é interno ao cluster. RTSP sobre TCP por ClusterIP resolve sem exceção de rede. |
| Retreino como bloco do vídeo | Plateia Claro liga para canal. Os 30s valem mais no bloco de identidade multi-empresa. |
| Escalar backend acima de 1 réplica | Estado de câmera vive no processo. Exige sharding ou fila antes. |
