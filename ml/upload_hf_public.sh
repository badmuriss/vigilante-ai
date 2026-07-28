#!/usr/bin/env bash
# Upload trained YOLOv8 PPE model to a PUBLIC Hugging Face Hub repo.
# Standalone version — no Vigilante.AI branding, suitable for academic/portfolio submission.
#
# Prereqs:
#   - export HF_TOKEN=<your-write-token>
#   - Trained run exists under ml/runs/train/<name>/
#
# Usage:
#   bash ml/upload_hf_public.sh
#   bash ml/upload_hf_public.sh ppe-canteiro-v1-4
#   bash ml/upload_hf_public.sh ppe-canteiro-v1-4 myuser/ppe-detection-yolov8s

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ML_ROOT="$REPO_ROOT/ml"
RUNS_DIR="$ML_ROOT/runs/train"

log() { printf "\n\033[1;36m▶ %s\033[0m\n" "$*"; }
die() { printf "\033[1;31m✗ %s\033[0m\n" "$*" >&2; exit 1; }

RUN_NAME="${1:-ppe-canteiro-v1-4}"
REPO_ID="${2:-}"
RUN_DIR="$RUNS_DIR/$RUN_NAME"

[[ -d "$RUN_DIR" ]] || die "Run dir not found: $RUN_DIR"
WEIGHTS="$RUN_DIR/weights/best.pt"
[[ -f "$WEIGHTS" ]] || die "best.pt missing at $WEIGHTS"
[[ -n "${HF_TOKEN:-}" ]] || die "HF_TOKEN not set"

# Call the interpreter directly instead of sourcing activate: a venv records an
# absolute path at creation time, so moving the repo leaves activate pointing at
# a directory that no longer exists. It then silently does nothing, `python`
# resolves to the system interpreter, and pip fails on an externally-managed
# environment. The binary itself keeps working.
PY=python
for candidate in "${VIRTUAL_ENV:-}/bin/python" "$ML_ROOT/.venv/bin/python" \
                 "$REPO_ROOT/backend/.venv/bin/python"; do
  if [[ -x "$candidate" ]]; then PY="$candidate"; break; fi
done
"$PY" -c "import huggingface_hub" 2>/dev/null \
  || "$PY" -m pip install -q "huggingface_hub>=0.20" \
  || die "huggingface_hub missing and could not be installed with $PY"

if [[ -z "$REPO_ID" ]]; then
  HF_USER=$("$PY" -c "
from huggingface_hub import HfApi
import os
print(HfApi().whoami(token=os.environ['HF_TOKEN'])['name'])
")
  REPO_ID="${HF_USER}/ppe-detection-yolov8s"
fi

log "Run dir : $RUN_DIR"
log "Repo id : $REPO_ID  (PUBLIC)"
log "Weights : $WEIGHTS"

# --- model card ---
log "Generating README.md model card..."
"$PY" - <<PY
import csv
from pathlib import Path

run_dir = Path(r"$RUN_DIR")
results_csv = run_dir / "results.csv"

precision = recall = mAP50 = mAP5095 = epochs = "n/a"
if results_csv.is_file():
    with results_csv.open() as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if rows:
        last = rows[-1]
        epochs = last.get("epoch", "n/a")
        precision = f"{float(last['metrics/precision(B)']):.4f}"
        recall = f"{float(last['metrics/recall(B)']):.4f}"
        mAP50 = f"{float(last['metrics/mAP50(B)']):.4f}"
        mAP5095 = f"{float(last['metrics/mAP50-95(B)']):.4f}"

card = f"""---
license: agpl-3.0
tags:
  - object-detection
  - yolov8
  - ppe-detection
  - safety
  - construction
  - workplace-safety
  - vigilante-ai
library_name: ultralytics
pipeline_tag: object-detection
---

# Vigilante.AI — PPE Detection (YOLOv8s)

Detector YOLOv8s **treinado especificamente para o [Vigilante.AI](https://github.com/badmuriss/vigilante-ai)**,
plataforma de monitoramento em tempo real de uso de Equipamentos de Proteção Individual (EPI)
em canteiros de obra e ambientes industriais.

Detecta o EPI **e a violação** em streams RTSP, webcams e imagens. Roda em produção como
parte do stack do Vigilante.AI alimentando um painel multi-tenant de compliance.

Architecture: **YOLOv8s-P2** (Ultralytics) fine-tuned from COCO weights. A cabeça extra de
stride 4 existe porque um capacete em câmera de obra ocupa 10-25 px: em stride 8 uma caixa
de 12 px cobre ~1.5x1.5 células e quase não recebe âncoras.

## Por que a violação é uma classe, e não uma inferência

A versão anterior deste modelo tinha 2 classes e derivava a violação da **ausência** de
detecção: nenhuma caixa de capacete sobre a cabeça implicava "capacete ausente". Medido em
2.808 frames de 10 obras reais onde **todos** os trabalhadores usavam EPI (portanto toda
acusação é erro por construção), esse esquema errava de 26% a 96% conforme o portão de
detecção abria. Cada falha de detecção virava acusação contra alguém em conformidade.

As classes 2 e 3 substituem esse palpite por evidência: uma cabeça descoberta precisa ser
**vista**. Na mesma footage, com os pesos deste card, a acusação por detecção direta errou
**0 de 641**.

## Classes

| id | name    | description                                    |
|----|---------|------------------------------------------------|
| 0  | helmet  | Capacete de segurança                          |
| 1  | vest    | Colete de alta visibilidade                    |
| 2  | head    | Cabeça SEM capacete, ou seja a violação        |
| 3  | no_vest | Torso SEM colete, ou seja a violação           |

## Validation metrics (final epoch)

| Metric            | Value      |
|-------------------|------------|
| Precision         | {precision} |
| Recall            | {recall}    |
| mAP@0.5           | {mAP50}     |
| mAP@0.5:0.95      | {mAP5095}   |
| Epochs trained    | {epochs}    |

### Per-class, held-out test split (1.828 imagens, 6.021 caixas)

| class   |   gt | P     | R     | mAP@0.5 | mAP@0.5:0.95 |
|---------|------|-------|-------|---------|--------------|
| helmet  | 4390 | 0.923 | 0.945 | 0.975   | 0.650        |
| vest    |  292 | 0.845 | 0.846 | 0.901   | 0.631        |
| head    | 1319 | 0.882 | 0.913 | 0.939   | 0.645        |
| no_vest |   20 | 0.807 | 0.650 | 0.650   | 0.377        |

`no_vest` tem apenas 20 caixas de ground truth no teste. Trate esse número como indicativo,
não como medida.

### Recall vs escala do objeto

Métrica in-domain é medida em imagens onde a cabeça ocupa ~1% da área. Numa câmera de obra
real ela ocupa 0,01% a 0,09%, duas ordens de grandeza a menos. O teste abaixo mantém os
rótulos e encolhe os pixels, colocando cada imagem de teste reduzida num canvas 960x720:

| escala | helmet | vest  | head  | no_vest |
|--------|--------|-------|-------|---------|
| 1.0    | 0.896  | 0.822 | 0.841 | 0.550   |
| 0.5    | 0.928  | 0.781 | 0.879 | 0.400   |
| 0.3    | 0.898  | 0.753 | 0.845 | 0.250   |
| 0.2    | 0.818  | 0.668 | 0.757 | 0.090   |

`head` sobrevive à redução de 5x. `no_vest` desmorona e por isso não deve dirigir alertas
sozinho.

## Limitações

- **Recall em domínio real não foi medido.** As tabelas acima usam imagens do dataset,
  encolhidas ou não. Footage pública de obra é 100% em conformidade, então serve para medir
  alarme falso mas não recall de violação. Fechar isso exige footage rotulada com violações
  reais em ângulo de CCTV.
- O split de validação sai das mesmas fontes do treino, então **mAP alto aqui não prova
  desempenho em campo**. A versão anterior marcou mAP@0.5 = 0.944 e falhava quase por
  completo em câmera real.
- `no_vest` é fraco. Em produção o Vigilante.AI o mantém fora das classes de violação
  confiáveis e continua inferindo colete por ausência.

## Training setup

| Param      | Value            |
|------------|------------------|
| Base model | yolov8s-p2.yaml  |
| Pretrained | yolov8s.pt (COCO) |
| Image size | 960              |
| Batch size | 12               |
| Optimizer  | SGD              |
| Initial LR | 0.01, cosine     |
| Epochs     | 117              |
| scale      | 0.9              |
| mosaic     | 1.0, close_mosaic 20 |

`scale: 0.9` é a escolha que mais importa. `RandomPerspective` sorteia em uniform(1-s, 1+s),
então 0.9 espalha um capacete frontal de 60 px entre 6 e 114 px e cobre a faixa de deploy.
O valor anterior, 0.5, parava em 30 px, o dobro do que a câmera entrega.

## Dataset

Merged from public PPE datasets on Roboflow Universe, mapped onto the 4-class schema:

- Personal Protective Equipment Combined Model
- Hard Hats
- Hard Hat Universe
- Safety Vests
- vest-qf3av
- vest-pbrbu

68.141 pares imagem+rótulo coletados, dos quais a deduplicação por average-hash removeu
31.567 (46%), sobrando 36.574 imagens: train 29.260, val 5.486, test 1.828.

Essas fontes já traziam as classes de violação (`head`, `NO-Hardhat`, `NO-Safety Vest`) e o
merge anterior as descartava. Recuperá-las adicionou ~42.700 caixas de cabeça descoberta sem
baixar um único dataset novo.

Distribuição no train: helmet 68.149, head 20.480, vest 4.631, no_vest 282. O desbalanceamento
não foi corrigido por oversampling: na versão anterior a classe minoritária teve desempenho
melhor que a majoritária, o que indica que o gargalo é resolução, não frequência.

### Augmentation

YOLO built-ins apenas: mosaic, HSV jitter, perspective, scale, translate, horizontal flip.
Sem Albumentations offline. `mixup`, `copy_paste` e `erasing` ficaram em zero de propósito:
os dois últimos são no-ops silenciosos em rótulos que só têm caixa.

## Quick start

```python
from ultralytics import YOLO

model = YOLO("best.pt")
results = model("frame.jpg")

for r in results:
    for box in r.boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        print(["helmet", "vest", "head", "no_vest"][cls], conf, (x1, y1, x2, y2))
```

## Download

```bash
huggingface-cli download {{repo_id}} best.pt --local-dir .
```

## Drop into the Vigilante.AI backend

```bash
huggingface-cli download {{repo_id}} best.pt --local-dir backend/
docker compose restart backend
```

## Intended use

Construído para **monitoramento de compliance de EPI em tempo real** no Vigilante.AI — canteiros
de obra, fábricas, galpões e ambientes industriais. Otimizado para streams RTSP / IP-cam, mas
funciona em qualquer fonte de imagem suportada pelo Ultralytics (vídeo, webcam, imagem).

Use cases cobertos pelo Vigilante.AI usando este modelo:
- Detecção em tempo real de trabalhadores sem capacete ou colete
- Geração de alertas com snapshot do frame para revisão por supervisor
- Active learning loop: feedback (correto / falso positivo) gera amostras YOLO para retreino
- Reporting multi-tenant de compliance por câmera / site / período

## Limitations

- Trained on 4 classes only (helmet, vest, head, no_vest). Does not detect gloves, boots,
  glasses, masks, etc.
- Performance degrades under extreme occlusion, very low resolution (< 320 px), or unusual
  viewpoints not represented in training data.
- May confuse high-vis clothing that is not a vest (e.g., jackets) with the vest class.
- No bias evaluation across demographics has been performed.

## Citation / créditos

Modelo treinado para o projeto **Vigilante.AI** — sistema completo de monitoramento de EPI
com backend FastAPI multi-tenant, frontend Next.js, simulador RTSP via mediamtx, observabilidade
com Prometheus + structlog, e pipeline de active learning integrado.

Repositório: https://github.com/badmuriss/vigilante-ai

## License

AGPL-3.0 (inherited from Ultralytics YOLOv8).
"""

card = card.replace("{{repo_id}}", "$REPO_ID")
(run_dir / "README_public.md").write_text(card)
print(f"Wrote {run_dir / 'README_public.md'}")
PY

# --- upload ---
log "Creating + uploading to $REPO_ID ..."
"$PY" - <<PY
import os
from pathlib import Path
from huggingface_hub import HfApi, create_repo

api = HfApi(token=os.environ["HF_TOKEN"])
repo_id = "$REPO_ID"
run_dir = Path(r"$RUN_DIR")

create_repo(repo_id, token=os.environ["HF_TOKEN"], private=False, exist_ok=True, repo_type="model")

# README_public.md is uploaded as README.md (HF requires README.md as the model card)
mappings = [
    (run_dir / "weights/best.pt", "best.pt"),
    (run_dir / "README_public.md", "README.md"),
    (run_dir / "args.yaml", "args.yaml"),
    (run_dir / "results.csv", "results.csv"),
    (run_dir / "results.png", "results.png"),
    (run_dir / "data.yaml", "data.yaml"),
]
for pat in ("confusion_matrix*.png", "BoxF1_curve.png", "BoxPR_curve.png",
            "BoxP_curve.png", "BoxR_curve.png", "labels.jpg", "val_batch0_pred.jpg"):
    for p in run_dir.glob(pat):
        mappings.append((p, p.name))

uploaded = 0
for path, dest in mappings:
    if not path.is_file():
        continue
    print(f"  uploading {dest} ({path.stat().st_size // 1024} KB)")
    api.upload_file(
        path_or_fileobj=str(path),
        path_in_repo=dest,
        repo_id=repo_id,
        repo_type="model",
        token=os.environ["HF_TOKEN"],
    )
    uploaded += 1

print(f"\nUploaded {uploaded} files")
print(f"Repo URL: https://huggingface.co/{repo_id}")
PY

log "Done — model live at https://huggingface.co/$REPO_ID"
