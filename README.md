# BookMySlot AI Service

Python FastAPI microservice providing AI-powered dental X-ray analysis for the BookMySlot healthcare platform.

## Run & Operate

### bookmyslot-ai-service (Python / FastAPI)
```bash
cd bookmyslot-ai-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- Required: place `best.pt` in `bookmyslot-ai-service/models/` (not committed to git)
- Required env: `MODEL_PATH=models/best.pt`, `CONFIDENCE_THRESHOLD=0.25`

### Node.js workspace (existing pnpm monorepo)
- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string

## Stack

### AI Service
- Python 3.11, FastAPI, Uvicorn
- YOLOv8 (Ultralytics), PyTorch
- Pydantic v2
- Deploy target: Render Web Service

### Node.js Monorepo
- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `bookmyslot-ai-service/` — standalone Python AI microservice (independent of pnpm workspace)
- `bookmyslot-ai-service/app/main.py` — FastAPI routes
- `bookmyslot-ai-service/app/model.py` — YOLOv8 inference logic + class mapping
- `bookmyslot-ai-service/app/schemas.py` — Pydantic response models
- `bookmyslot-ai-service/models/` — model weights directory (`best.pt` not committed)
- `artifacts/api-server/` — Node.js Express API

## Architecture decisions

- AI service is **fully independent** of the Node.js backend — Node calls it via HTTP, no shared code
- `best.pt` model file is **never committed to git** — downloaded from Google Drive/Colab and placed in `models/`
- Class labels use DENTEX `category_id_1` mapping (0–3 → "Finding Type 1–4") — no assumed dental meanings until taxonomy is validated
- Confidence threshold is env-configurable (`CONFIDENCE_THRESHOLD`, default 0.25)
- Temporary upload files are deleted immediately after inference

## Product

Dental X-ray analysis API: accepts an X-ray image, runs YOLOv8 inference, returns structured JSON findings with class label, confidence score, and bounding box location.

## User preferences

- Do not commit model files (`*.pt`) to git
- Deploy AI service to Render (separate from Node backend)
- Use DENTEX category_id_1 class labels — do not hardcode assumed dental meanings

## Gotchas

- `best.pt` must be placed manually in `bookmyslot-ai-service/models/` before the service can run
- On Render, the model should be downloaded at startup or stored on a persistent disk — not bundled in the Docker image if it exceeds ~50 MB
- The `bookmyslot-ai-service/` directory is **not** a pnpm workspace package — do not add it to `pnpm-workspace.yaml`

## Pointers

- See `bookmyslot-ai-service/README.md` for full API docs and Render deployment steps
