# Explorer

The explorer consists of a FastAPI backend and a React frontend.

## Backend

```bash
cd explorer/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

uvicorn main:app --reload --port 8000
```

Environment variables:

- `DATABASE_URL` (default: `postgresql://xai:xai@localhost/xai_explorer`)
- `XAI_NODE_URL` (default: `http://localhost:12001`)
- `CORS_ORIGINS` (comma-separated)
- `EXPLORER_REQUIRE_API_KEY` (`true`/`false`)
- `EXPLORER_API_KEY_SECRET_PATH`
- `HOST`, `PORT`

API docs are served at `http://localhost:8000/docs`.

## Frontend

```bash
cd explorer/frontend
npm install
npm run dev
```

By default the frontend expects the backend at `http://localhost:8000`.
