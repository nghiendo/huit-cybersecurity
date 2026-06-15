# Python Backend

FastAPI backend for a local SQLi/XSS training lab.

## Run

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Docker

From the repo root:

```powershell
docker compose up --build
```

SQLite is persisted to `backend/data/lab.sqlite` on the host via bind mount.

## Seeder

The backend seeds demo rows for `users`, `comments`, and `lab_logs` automatically when each table is empty.

To run the seeder manually:

```powershell
cd backend
python -m app.seed
```

## Endpoint

Only one API endpoint is exposed:

```txt
POST /api/lab
```

Example:

```json
{
  "input": "' OR 1=1--"
}
```

## Modes

Default mode is `vulnerable`. In this mode the lab accepts payloads, classifies likely SQLi/XSS patterns, stores recent inputs, and returns simulated analysis for teaching and detector evaluation.

The backend does not execute raw SQL built from user input and does not return unescaped HTML for browser execution. Frontend demos should render `escapedPreview` as text or explicitly isolate any client-side exercises.

To use the detector as a blocking layer:

```powershell
$env:LAB_MODE = "protected"
$env:BLOCK_THRESHOLD = "0.85"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Model Hooks

`app/detectors.py` currently contains lightweight placeholder functions:

- `run_ml_detector`
- `run_dl_detector`
- `classify_payload`

These can be replaced with scikit-learn, PyTorch, TensorFlow, ONNX Runtime, or a separate model server call without changing the endpoint contract.
