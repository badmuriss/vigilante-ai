# Guia — Criar o template WhatsApp (alerta de EPI com botões)

Guia para criar o template no Meta que o Vigilante.AI usa para mandar o alerta
de EPI pelo WhatsApp **com botões de revisão** (Confirmar / Falso positivo).
O conteúdo aqui bate exatamente com o que o backend envia.

> **Causa mais provável do erro que você teve:** o botão **"Marcar como Falso
> Positivo" tem 26 caracteres** e o limite do Meta para botão quick-reply é
> **25**. Use um rótulo mais curto (ex: **"Falso Positivo"**). O texto do botão
> é só cosmético — o backend identifica pela **ordem** (posição), não pelo
> texto.

---

## 1. Contrato que o backend espera (tem que bater)

| Item | Valor exigido |
|---|---|
| Categoria | **Utility** |
| Idioma | **Português (Brasil) = `pt_BR`** (underscore, BR maiúsculo) |
| Nome | minúsculas + underscore, sem espaços/maiúsculas. Vai em `VIGILANTE_WHATSAPP_TEMPLATE_NAME` |
| Corpo | **exatamente 3 variáveis**, nesta ordem: `{{1}}` câmera, `{{2}}` EPI ausente, `{{3}}` data/hora |
| Botões | **2 "Resposta rápida" (quick reply)**, nesta ordem: **índice 0 = Confirmar**, **índice 1 = Falso positivo** |
| Header | **opcional** — ver a decisão na seção 4 |

Pontos críticos:
- **Ordem dos botões importa.** Índice 0 = confirmar (vira feedback `correct`),
  índice 1 = falso positivo (`false_positive`). Se inverter, inverte o efeito.
- O **payload** do botão (que leva o `alert_id`) é definido **no envio**, pelo
  backend — você **não** configura payload na criação. Só o texto do botão.
- Nome + idioma do template criado **têm que ser idênticos** ao que está no env
  (`VIGILANTE_WHATSAPP_TEMPLATE_NAME` / `VIGILANTE_WHATSAPP_TEMPLATE_LANGUAGE`).

---

## 2. Passo a passo no Meta

1. **business.facebook.com → WhatsApp Manager → Modelos de mensagem → Criar
   modelo.**
2. **Categoria: Utility.** (Não use Marketing. Nada de texto promocional, senão
   o Meta reclassifica/rejeita.)
3. **Nome:** minúsculas + `_`, ex `vigilante_epi_review`. Não dá pra editar
   depois; não pode repetir nome na mesma conta.
4. **Idioma:** Português (Brasil) → `pt_BR`.
5. **Header:** ver seção 4. Para protótipo rápido, escolha **Nenhum** (texto).
6. **Corpo (Body):** cole o texto da seção 3. Variáveis `{{1}} {{2}} {{3}}`
   sequenciais, **sem** começar nem terminar com variável, **sem** duas
   variáveis coladas.
7. **Amostras (Samples):** preencha exemplo de cada variável (obrigatório):
   `{{1}}` = `Portão Norte`, `{{2}}` = `Capacete`, `{{3}}` = `28/05/2026 14:30`.
8. **Botões → Resposta rápida (Quick reply):** adicione **2**, nesta ordem:
   1. `Confirmar Infração`
   2. `Falso Positivo`   ← curto (≤ 25 chars!)
9. **Enviar.** Aprovação costuma sair em minutos (pode ir a revisão manual até
   24–48h). Status em Modelos de mensagem (Pendente → Aprovado).

---

## 3. Texto pronto pra colar (corpo)

```
🦺 Possível violação de EPI detectada.

Câmera: {{1}}
EPI ausente: {{2}}
Data/hora: {{3}}

Revise e responda abaixo: confirme a infração ou marque como falso positivo.
```

Amostras:
- `{{1}}` → `Portão Norte`
- `{{2}}` → `Capacete`
- `{{3}}` → `28/05/2026 14:30`

Botões (Resposta rápida), nesta ordem:
1. `Confirmar Infração`
2. `Falso Positivo`

---

## 4. Decisão do header (importante)

Header de mídia no WhatsApp **não é "opcional por envio"**: se o template TEM
header de imagem, **todo envio precisa mandar uma imagem**, senão o Meta
rejeita o envio.

### Opção A — SEM imagem (recomendado pra protótipo)
- Header = **Nenhum**.
- No card de WhatsApp da plataforma, deixe **"Anexar imagem" DESLIGADO**.
- Resultado: alerta vai como texto + botões. `Enviar teste` funciona. Simples,
  sem falha.

### Opção B — COM foto do frame
- Header = **Mídia → Imagem** (suba uma imagem de exemplo na criação — sample de
  imagem é obrigatório).
- No card, **"Anexar imagem" LIGADO**.
- Caveats:
  - **Todo** envio precisa de imagem válida. Se o frame do alerta não carregar,
    o envio falha.
  - O botão **"Enviar teste"** manda **sem** imagem → vai **falhar** com a
    Opção B (é teste sem frame). Normal; teste com um alerta real.

> Para colocar online rápido: **Opção A**. Migra pra B depois se quiser a foto.

---

## 5. Erros comuns na criação (e fix)

| Erro | Causa | Fix |
|---|---|---|
| Botão rejeitado / muito longo | quick-reply > 25 chars (ex "Marcar como Falso Positivo" = 26) | Encurta: `Falso Positivo` |
| Variáveis inválidas | não começa em `{{1}}`, pula número, repete | numere `{{1}} {{2}} {{3}}` em ordem, sem buracos |
| Variável no início/fim ou duas coladas | placeholder sem texto estático ao redor | embrulhe cada variável com texto; corpo começa e termina com texto |
| Faltam amostras | submeteu sem exemplo das variáveis | preencha sample de cada `{{n}}` |
| Header imagem sem sample | header de imagem exige imagem de exemplo | suba a imagem de exemplo na criação |
| Nome inválido/duplicado | espaço/maiúscula/símbolo ou nome repetido | minúsculas+underscore, nome único |
| Categoria errada | texto soa promocional → vira Marketing/rejeita | mantenha 100% transacional, sem oferta/CTA de venda |
| Idioma errado | usou `pt`/`pt-BR`/`br` | use **`pt_BR`** e escreva em PT-BR |
| Espaço/linha sobrando | espaços duplos, linhas em branco extras | limpe a formatação |

---

## 6. Depois de aprovado

1. No `.env`:
   ```
   VIGILANTE_WHATSAPP_TEMPLATE_NAME=vigilante_epi_review   # o nome EXATO que você criou
   VIGILANTE_WHATSAPP_TEMPLATE_LANGUAGE=pt_BR
   ```
   (e `VIGILANTE_WHATSAPP_APP_SECRET` + `VIGILANTE_WHATSAPP_VERIFY_TOKEN` pro
   inbound dos botões.)
2. `docker compose up -d backend` (reinicia, lê o env no boot).
3. No card de WhatsApp: deve mostrar **"Plataforma conectada"**; cadastre os
   **operadores** e ligue **Ativar**.
4. Crie um alerta → cai no WhatsApp do operador com os 2 botões → toque →
   feedback aplicado no alerta + resposta de confirmação.

---

## 7. Como o backend usa o template (referência)

- **Push de revisão** (alerta novo, pending): corpo com os 3 params + header de
  imagem (se Opção B) + **2 botões quick-reply** com payload
  `confirm:<alert_id>` (índice 0) e `false_positive:<alert_id>` (índice 1).
- **Toque no botão**: chega no webhook como mensagem `type:"button"`; o backend
  lê o payload, valida que o alerta é do tenant do operador, grava o feedback e
  responde por texto.
- **Enviar teste**: manda só o corpo (`Teste de configuração` / `Vigilante.AI` /
  data-hora), **sem** imagem e **sem** payload de botão.
