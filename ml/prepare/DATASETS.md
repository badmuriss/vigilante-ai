# Datasets — guia de seleção

Schema: **4 classes** (`helmet`, `vest`, `head`, `no_vest`). `head` é cabeça sem
capacete e `no_vest` é torso sem colete, ou seja a violação como classe própria.
Tudo fora desse escopo é descartado pelo `merge_datasets.py`.

> **As fontes Roboflow já baixadas em `ml/datasets/` cobrem as 4 classes.**
> Nada do Tier 1 abaixo é necessário para ter `head`. Contagem medida nas fontes
> locais: `head` 16.346 (hard-hat-universe), `NO-Hardhat` 12.946 (hard-hats-fhbh5)
> + 12.966 (combined-model), `No-Helmet` 398 (vest-pbrbu). Até 2026-07-27 o
> `merge_datasets.py` descartava todas essas caixas por design.
>
> **Aviso sobre o Tier 1:** os repositórios GitHub abaixo contêm **código, não
> imagens** (o SHWD tem 3,5 MB no git). `git clone` seguido de `voc_to_yolo` não
> traz dataset nenhum. As imagens ficam em Drive/Baidu, linkados no README de
> cada repo. Para o SHWD: Google Drive id `1qWm7rrwvjAWs1slymbrLaCf7Q-wnGLEX`
> (7.581 imagens, VOC, MIT). Baixe com `gdown` antes de converter.

**Princípio**: só usar fontes **estáveis** (GitHub maduro com >100 stars, Roboflow Public benchmark). Datasets de Roboflow Universe upload-by-user são voláteis (deletados/movidos sem aviso) — evitar citar slug fixo.

## Verificação atual (curl HEAD)

URLs abaixo confirmadas no commit deste arquivo. Se algo voltar 404 no futuro, busca alternativa (não invento link).

## Tier 1 — confirmados via curl, pegar todos

### SHWD (Safety Helmet Wearing Dataset) — GitHub
- URL: https://github.com/njvisionpower/Safety-Helmet-Wearing-Dataset
- ~7.500 imagens, classes `helmet`, `head`/`person` (VOC format)
- Dataset mais citado em papers de detecção de capacete
- Download:
  ```bash
  git clone https://github.com/njvisionpower/Safety-Helmet-Wearing-Dataset \
    ml/datasets/shwd_raw
  python -m ml.prepare.voc_to_yolo \
    --voc-root ml/datasets/shwd_raw \
    --out-root ml/datasets/shwd \
    --images-subdir VOC2028/JPEGImages \
    --annotations-subdir VOC2028/Annotations
  ```

### GDUT-HWD — GitHub
- URL: https://github.com/wujixiu/helmet-detection
- ~3.000 imagens canteiro chinês, capacete por cor (VOC)
- Download:
  ```bash
  git clone https://github.com/wujixiu/helmet-detection ml/datasets/gdut_raw
  python -m ml.prepare.voc_to_yolo \
    --voc-root ml/datasets/gdut_raw \
    --out-root ml/datasets/gdut
  ```

### Pictor-PPE — GitHub
- URL: https://github.com/ciber-lab/pictor-ppe
- ~1.500 imagens canteiro real, formato YOLO direto
- Download:
  ```bash
  git clone https://github.com/ciber-lab/pictor-ppe ml/datasets/pictor_ppe
  ```

### Hard Hat Workers — Roboflow Public
- URL: https://public.roboflow.com/object-detection/hard-hat-workers
- ~7.000 imagens, classes `helmet`, `head`, `person`
- Sem API key necessário
- Download manual: abre URL → "Download Dataset" → format YOLOv8 → descomprime em `ml/datasets/hardhat/`

### Smart_Construction — GitHub (bonus, pequeno)
- URL: https://github.com/PeterH0323/Smart_Construction
- ~500 imagens
- Útil só pra incremento marginal — pode pular sem perda

## Outros caminhos pra achar (estável, sem URL-by-URL)

Se quiser mais dados depois:

```bash
# Roboflow Universe — busca aberta, pega URL ATIVO no momento
xdg-open "https://universe.roboflow.com/search?q=ppe+helmet+vest"
xdg-open "https://universe.roboflow.com/search?q=construction+safety+yolo"

# Kaggle — busca aberta
xdg-open "https://www.kaggle.com/datasets?search=hard+hat+detection"
xdg-open "https://www.kaggle.com/datasets?search=construction+ppe"

# GitHub — filtro por stars
xdg-open "https://github.com/search?q=hard+hat+detection+yolo&type=repositories&s=stars"
```

Critérios pra **adotar** um dataset que achou:
0. Preferir fonte com a **violação anotada** (`head`, `NO-Hardhat`, `NO-Safety Vest`).
   Detectar cabeça descoberta exige evidência positiva; inferir por ausência de
   capacete transforma toda falha de detecção em acusação (ver `ml/eval_compliant.py`).
1. ≥ 1.000 imagens
2. helmet E vest separados (não agregado em "ppe")
3. Bbox-anotados (não só classification)
4. License compatível (Public Domain, CC-BY, MIT)
5. Última atualização nos últimos 2 anos OU ≥100 stars (estabilidade)

## NÃO pegar

- "PPE detection" genérico < 500 imagens — fork copiado
- Cor única ("yellow helmet only") — viés
- Selfie/frontal — pose errada vs CCTV
- Qualquer Roboflow Universe slug que **eu** tiver citado mas você verifica e dá 404 — significa foi deletado/renomeado, busca substituto via search

## Pipeline completo (Tier 1)

```bash
source ml/.venv/bin/activate

# Clones diretos (estáveis)
git clone https://github.com/njvisionpower/Safety-Helmet-Wearing-Dataset ml/datasets/shwd_raw
git clone https://github.com/wujixiu/helmet-detection ml/datasets/gdut_raw
git clone https://github.com/ciber-lab/pictor-ppe ml/datasets/pictor_ppe

# Hard Hat Workers: download manual no Roboflow Public → ml/datasets/hardhat/

# Conversões VOC → YOLO
python -m ml.prepare.voc_to_yolo \
  --voc-root ml/datasets/shwd_raw \
  --out-root ml/datasets/shwd \
  --images-subdir VOC2028/JPEGImages \
  --annotations-subdir VOC2028/Annotations

python -m ml.prepare.voc_to_yolo \
  --voc-root ml/datasets/gdut_raw \
  --out-root ml/datasets/gdut

# Merge + dedupe
python -m ml.prepare.merge_datasets \
  --sources \
    ml/datasets/shwd \
    ml/datasets/gdut \
    ml/datasets/pictor_ppe \
    ml/datasets/hardhat \
  --output ml/datasets/merged \
  --dedupe --dedupe-threshold 4 \
  --val-ratio 0.15 --test-ratio 0.05
```

## Resultado real do merge (só fontes Roboflow, 2026-07-27)

Medido, não estimado. `ml/datasets/merged4`, dedupe threshold 4:

```
68.141 pares coletados -> dedupe removeu 31.567 (46%) -> 36.574 imagens
train 29.260 | val 5.486 | test 1.828

caixas no train:
  0 helmet   68.149
  1 vest      4.631
  2 head     20.480
  3 no_vest      282   <- fino demais para treinar, medir o AP antes de confiar
```

**Não persiga mAP alto no val split.** O `ppe-canteiro-v1-4` marcou mAP@0.5 = 0.944
aqui e falhou quase por completo em CCTV real: 4% de cobertura e 100% de alarme
falso em capacete. O val sai das mesmas fontes frontais do train, então mede
memorização. A régua que vale é `ml/eval_compliant.py` sobre footage real.

Causa medida: só **2,31%** das caixas de capacete estão na escala de deploy
(10-25px, ou 0,01-0,09% da área do frame). O treino precisa fabricar objeto
pequeno via `scale: 0.9` + mosaico (ver `ml/TRAINING_PLAN.md`).
