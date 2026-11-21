# FarmSight

FarmSight is a crop-health and produce-quality application. It combines a
React/Vite frontend with a FastAPI image-analysis service and a preserved
Streamlit interface. Images are analyzed by local PyTorch models.

## Features

- **Leaf diagnosis:** identifies supported crops and leaf-condition classes;
  unsupported known-crop examples map to a reject label.
- **Tomato pest recognition:** classifies eight source-coded categories or a
  non-target class. The source does not provide verified pest species names.
- **Produce grading:** identifies one of 14 fruit or vegetable types and
  classifies its condition as Fresh or Rotten.
- **Input checking:** an image gate checks whether an upload resembles a leaf,
  produce, or another image type.
- **Explanations:** analysis results can include a Grad-CAM heatmap.

The React interface is currently English-only. The language switch has been
removed.

## Run the application

Use two PowerShell terminals from the project root.

Terminal 1 — start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Terminal 2 — start the frontend:

```powershell
Set-Location frontend
pnpm install --frozen-lockfile
pnpm dev -- --host 127.0.0.1 --port 5173
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). The Vite server proxies
API requests to `http://127.0.0.1:8000`. Set `FARMSIGHT_API_TARGET` to use a
different API origin.

Check API and model availability at
[http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health). The
response includes an `ok` flag and availability for each model file.

### Single-server mode

Build the frontend once, then serve it through FastAPI:

```powershell
Set-Location frontend
pnpm install --frozen-lockfile
pnpm run build
Set-Location ..
.\.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

### Run the Streamlit interface

The original Streamlit UI is preserved:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app\app.py
```

It normally runs at [http://localhost:8501](http://localhost:8501).

## API

- `GET /api/health` — reports model-file availability.
- `POST /api/analyse` — multipart fields: `task` (`leaf`, `produce`, or `pest`)
  and `file` (JPEG, PNG, or WebP). Leaf crop is identified automatically; do
  not send a `crop` field.
- Uploads are limited to 10 MB. Image dimensions are also limited.

The API reuses the inference implementation in `app/app.py`, so the React and
Streamlit interfaces use the same model paths and image-processing behavior.

## Models and evaluation

Active model checkpoints:

| Task | Checkpoint |
| --- | --- |
| Leaf diagnosis | `runs/leaf_expansion_candidate/model.pt` |
| Potato/Tomato leaf specialist | `app/models/leaf.pt` |
| Produce grading | `app/models/fruit.pt` |
| Leaf/produce/other input gate | `runs/input_gate/model.pt` |
| Tomato pest recognition | `runs/tomato_pest_candidate/model.pt` |

Recorded test results are dataset measurements, not guarantees for field
photos:

- The 68-class leaf model scored 96.6% accuracy and 92.0% macro F1 on its
  9,447-image test split. Its Potato/Tomato field holdout score was 51.4% on
  243 images; this conditions on the known crop and does not measure crop
  identification.
- The nine-class tomato-pest model scored 89.0% accuracy and 84.9% macro F1 on
  its 182-image test split.
- Produce grading scored 92.9% accuracy on 2,930 held-out dataset images.
  Performance on real phone photos has not been measured.
- The image gate scored 99.7% accuracy on 1,008 test images. Only eight
  non-target images were in that test split, so this does not establish broad
  out-of-domain rejection.

Leaf predictions are suggestions, not confirmed diagnoses. Treatment guidance
is withheld unless confidence thresholds are met. Confirm important decisions
with a qualified agricultural expert.

## Training and data preparation

Python utilities are grouped by purpose and run as modules from the project
root. For example, train the MobileNet model on prepared FruitVeg data:

```powershell
.\.venv\Scripts\python.exe -m scripts.training.train --data data\fruitveg --out runs\fruitveg_mobilenet --model mobilenet --augment --class_weights --epochs 5 --batch 64 --img 128
```

Prepare the expanded leaf dataset and fine-tune a candidate without replacing
the current model:

```powershell
.\.venv\Scripts\python.exe -m scripts.data_preparation.prepare_leaf_extension
.\.venv\Scripts\python.exe -m scripts.training.train --data data\leaf_all_crops_v6 --out runs\leaf_extension_candidate --model mobilenet --init_checkpoint runs\leaf_7crop_candidate_v7\model.pt --augment --class_weights --epochs 20 --early_stopping_patience 5 --batch 32 --img 128 --workers 0 --lr 0.0001 --compare_checkpoint runs\leaf_7crop_candidate_v7\model.pt --compare_data data\leaf_all_crops_v5
```

Training refuses to overwrite an existing `model.pt` unless `--overwrite` is
explicitly supplied. Review the candidate's test metrics, per-class results,
confusion matrix, and field-image results before changing the deployed model.

Useful scripts:

- `scripts/training/train.py` — train CNN or MobileNet classifiers.
- `scripts/training/train_input_gate.py` — train the leaf/produce/other image
  gate; provide representative negative images with `--negative-images`.
- `scripts/training/baseline_cnn.py` — shared CNN, dataset, and evaluation
  utilities.
- `scripts/data_preparation/prepare_fruitveg.py` — prepare FruitVeg splits.
- `scripts/data_preparation/prepare_leaf_all_crops.py` and
  `scripts/data_preparation/prepare_leaf_extension.py` — prepare leaf datasets.
- `scripts/data_preparation/prepare_additional_datasets.py` and
  `scripts/data_preparation/prepare_tomato_pest_rejection.py` — audit and
  prepare additional crop and pest data.
- `scripts/data_preparation/prepare_plantdoc.py`,
  `scripts/data_preparation/make_mixed.py`, and
  `scripts/data_preparation/merge_class_folders.py` — additional dataset
  preparation workflows.
- `scripts/evaluation/eval_holdout.py` — evaluate a checkpoint on a labelled
  holdout folder.
- `scripts/evaluation/gradcam_check.py` — generate a sampled Grad-CAM grid.
- `scripts/evaluation/evaluate_images.py` — check the labelled image manifest
  in `evaluation/`.

Run the external-image spot check from the project root:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluation.evaluate_images
```

The script reads `evaluation/web_image_manifest.json` and writes
`evaluation/web_image_results.json`. The bundled images are a small qualitative
check, not a statistically meaningful accuracy estimate. The manifest also
references optional workspace examples under `new images/`; that folder is not
currently present, so restore those images or remove their manifest entries
before running the full manifest evaluation.

Dataset source files, prepared dataset folders, and archives are retained as
provided. Do not move, relabel, unpack, or regenerate dataset contents unless
intentionally running a preparation workflow.

## Tests and checks

Run Python tests from the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Run frontend type checking and production build:

```powershell
Set-Location frontend
pnpm exec tsc --noEmit
pnpm run build
```

Run browser tests:

```powershell
pnpm exec playwright test
```

If Playwright reports that Chromium is missing, install its browser once with
`pnpm exec playwright install chromium` from `frontend/`. Browser tests that
exercise API inference require the API server to be running.

## Project layout

```text
app/                         Streamlit UI, shared inference, and legacy models
archives/                    Original Dataset.zip and UI.zip archives
data/                        Prepared datasets and raw dataset sources
evaluation/                  Image manifest, spot-check results, and images
frontend/                    React/Vite application and browser tests
logs/training/               Historical training logs
runs/                        Model checkpoints, metrics, and run outputs
scripts/data_preparation/    Dataset preparation utilities
scripts/evaluation/          Model and image evaluation utilities
scripts/training/            Model training utilities
tests/                       Python test suite
server.py                    FastAPI application
README.md                    Project setup, usage, and development guide
```

The root `.gitignore` excludes the local Python environment, Python caches,
pytest cache, frontend dependencies, and generated frontend build/test output.
