# Frontend

React + Vite frontend for the SQLi/XSS lab.

## Run

```powershell
cd frontend
npm install
npm run dev
```

Vite proxies `/api/*` to `http://127.0.0.1:8000`, so run the Python backend first.

## Docker

From the repo root:

```powershell
docker compose up --build
```

The frontend runs on `http://127.0.0.1:5173` and proxies API traffic to the backend container.
