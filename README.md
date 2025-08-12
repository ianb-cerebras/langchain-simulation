Simulation Web App
===================

A platform for simulating user interviews and synthesizing insights, powered by Cerebras. The app generates personas, conducts LLM‑driven interviews, and summarizes key themes, observations, and takeaways with an interactive dashboard.

Overview
--------

- Frontend: Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui
- Backend: Flask (Python) microservice
- LLM Workflow: LangGraph + Cerebras (via `langchain-cerebras`)
- Deployment: Vercel (frontend + Next API routes); Flask can be hosted separately (Render/Fly/EC2)

Features
--------

- Run simulated UX research: personas, interviews, synthesis
- Dashboard with:
  - Key Insights, Points of Observation, Big Takeaways
  - Interactive area chart of simulation progress
  - Draggable participants table with interview drill‑down
- Result caching for quick refresh (`/api/uxr-result` backed by `uxr-result.json`)

Prerequisites
-------------

- Node.js 20+
- Python 3.10+
- A Cerebras API key (sk_cerebras_...)

Quick Start (Local)
-------------------

1) Install frontend deps and run the app

```bash
npm ci
npm run dev
```

Visit http://localhost:3000 and open the Config page.

2) Start the Flask backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PORT=5000
python app.py
```

3) Configure the frontend to call Flask

Set `FLASK_URL` at build/runtime for Next.js API route `POST /api/run-uxr`:

```bash
# Example local
export FLASK_URL=http://localhost:5000
```

You can put this in your Vercel project env vars as well.

Running a Simulation
--------------------

- Go to Config
- Enter your research question, target audience, select number of interviews
- Paste your Cerebras API key (stored in localStorage on‑device)
- Click Run Simulation
- You’ll be redirected to the Dashboard when complete

Data Flow
--------

- Frontend POSTs to `/api/run-uxr` → forwards to Flask `/api/run-uxr`
- Flask runs the LangGraph workflow and returns a normalized payload including:
  - `participants` (table)
  - `timeline` events (`answer`, `interview_completed`)
  - `keyInsights`, `observations`, `takeaways`
- Frontend saves results to `uxr-result.json` (project root in dev; `/tmp` in Vercel) for `/api/uxr-result`

Important Behaviors
-------------------

- Interview/Question counts: values from the Config slider are respected end‑to‑end. Defaults apply only if missing.
- Insights parsing: backend extracts content from synthesis, supporting inline headings like `KEY THEMES: ...` and avoids duplicating “Pain Points” vs “Takeaways”.
- Charting: uses timeline buckets when timestamps are valid; falls back to sequence‑based data so charts reflect real progress even without reliable timestamps.

Environment Variables
---------------------

Frontend (Next.js):

- `FLASK_URL`: Base URL of the Flask service (e.g., `http://localhost:5000` or your deploy)
- `VERCEL` (provided by Vercel): toggles using `/tmp/uxr-result.json`

Backend (Flask):

- `CEREBRAS_API_KEY`: Cerebras key for LLM (also passed per‑request from frontend)
- `UXR_DEBUG=1`: enable extra debug logs

Production Notes
----------------

- Secrets: The Cerebras key is entered client‑side and stored in localStorage on the device. For production, consider a secure server‑side secret storage flow.
- Persistence: Results are saved to JSON for demo use. For production durability and collaboration, add a database (e.g., Postgres) and user auth.
- Observability: Add structured logging, metrics, and tracing as you scale.

Scripts
-------

```bash
# Frontend
npm run dev         # Next dev server
npm run build       # Production build
npm run start       # Start production server

# Backend
python backend/app.py  # Flask server (after venv + pip install)
```

License
-------

MIT


