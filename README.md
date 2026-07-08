# DocVerify

AI-powered **document verification & entity extraction**. Upload a PDF or image,
pick a document type, and Claude reads it — extracting structured fields and
checking them against reference values you supply. Document types and their fields
are fully configurable, so it works for any document, not just one domain.

Originally an SIH 2024 recruitment-verification prototype (Surya OCR + local Ollama
+ poppler across GPU servers), rebuilt as a clean product around a **single Claude
vision call**.

## How it works

```
Upload (PDF/image)  ──►  Claude vision + structured outputs  ──►  {structured JSON}
                                                                       │
                                              compare vs reference ────┘
                                                                       ▼
                                             per-field match / mismatch report
```

- **One Claude call** does OCR *and* extraction — no OCR service, no Ollama, no
  poppler, no GPU. Claude reads PDFs and images natively.
- **Structured outputs** (`output_config.format`) guarantee validated JSON built at
  runtime from each document type's field schema — no `eval`, no positional arrays.
- **Verification** compares extracted fields against reference values and flags
  document-type mismatches.

## Architecture

| Part | Stack |
|------|-------|
| Backend | FastAPI (single service), MongoDB (async via Motor), JWT auth (bcrypt), Anthropic SDK |
| Frontend | React + Vite + TypeScript + Tailwind |
| Infra | `docker-compose` (mongo + backend + frontend) |

```
backend/app/
  config.py        all secrets/URLs from env (pydantic-settings)
  security.py      bcrypt password hashing + JWT
  extraction.py    Claude vision + runtime JSON schema  ← the core
  verification.py  compare extracted vs reference
  seed.py          default doc-type schemas
  routers/         auth · doc-types · verify+history
frontend/src/      auth · dashboard · verify flow · schema admin
```

## Quick start (Docker)

```bash
cp .env.example .env       # then set JWT_SECRET and ANTHROPIC_API_KEY
docker compose up --build
```

- App: <http://localhost:8080>
- API docs: <http://localhost:8000/docs>

Register an account, go to **Verify**, pick a doc type (e.g. *Marksheet*), upload a
file, optionally fill in expected values, and hit **Extract & verify**.

## Local development

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # set ANTHROPIC_API_KEY (and a JWT_SECRET)
# needs a MongoDB running locally, or point MONGO_URI at one
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173 (proxies /api to :8000)
```

## Configuration

All via environment (see `backend/.env.example`):

| Var | Purpose | Default |
|-----|---------|---------|
| `MONGO_URI` / `MONGO_DB` | database | `mongodb://localhost:27017` / `docverify` |
| `JWT_SECRET` | token signing — **must** override in prod | `change-me-in-production` |
| `ANTHROPIC_API_KEY` | Claude access (read by the SDK) | — |
| `ANTHROPIC_MODEL` | extraction model | `claude-opus-4-8` |
| `CORS_ORIGINS` | allowed SPA origins (comma-sep) | `http://localhost:5173` |

Swap `ANTHROPIC_MODEL` to `claude-sonnet-5` or `claude-haiku-4-5` to trade quality
for cost on high volume.

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` · `/api/auth/login` | returns a JWT |
| GET | `/api/auth/me` | current user |
| GET/POST | `/api/doc-types` | list / create doc types |
| GET/PUT | `/api/doc-types/{key}` | get / update a doc type |
| POST | `/api/verify` | multipart: `file`, `doc_type`, optional `reference` (JSON) |
| GET | `/api/verifications` · `/api/verifications/{id}` | history |

## Tests

```bash
cd backend && source .venv/bin/activate
pip install pytest
pytest                      # extraction schema builder, verification logic, auth/JWT
```

The Anthropic client is never called in tests.

## Security notes

- Secrets, DB URIs, and model choice are read from the environment — nothing is
  committed. Never commit `.env` (it's git-ignored).
- Passwords are bcrypt-hashed; JWTs are signed with `JWT_SECRET`.
- ⚠️ **The original repo committed live MongoDB credentials** (`sih:sih@…`) — those
  are in git history and should be treated as compromised. **Rotate the MongoDB
  password / Atlas access** before deploying; moving them to `.env` does not undo
  the historical exposure.
