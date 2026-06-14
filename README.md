# ComplianceCrew

## Project Description
ComplianceCrew is an AI-powered system that automates **RBI (Reserve Bank of India) circular compliance**. A team of six specialist agents reads a regulatory circular, derives concrete control requirements, validates each other's interpretations against the source text, routes the work to bank departments, tests sample bank data for violations, and assembles an audit-ready report — with **every claim cited to a verbatim paragraph** of the regulation and **every model call chained with SHA-256** so the audit trail is provably untampered. The solution is deployed as an interactive web console, letting a compliance officer upload a circular and watch the agents reason in real time. Built for **SuRaksha Cyber Hackathon 2.0 · Canara Bank**, and powered entirely by a **free-tier model** (Groq Llama 3.3 70B) — no Azure OpenAI, no paid APIs.

---

## Project Details

### Problem Statement
RBI issues a continuous stream of circulars, and every regulated bank must translate each one into auditable controls, assign ownership, set deadlines, and prove compliance against live data. Done manually the process is slow and error-prone; done with a naive LLM it hallucinates requirements and fabricates citations. ComplianceCrew makes interpretation **automated and auditable at once** — cited, peer-validated, department-routed, and tamper-evident.

### The Agent Pipeline
The system is a six-node [LangGraph](https://github.com/langchain-ai/langgraph) state machine with a single Pydantic-typed state. The Validator's conditional edge back to the Mapper is the spine of the design.

```
PDF/TXT → Ingestor → Mapper → Validator → Assigner → Evidence Checker → Auditor → Report
            (classify)  ▲          │        (route +    (query bank      (cited
                        └─ retry ──┘         escalate)    data)            memo)
                       conditional edge on rejection (cap = 2)
```

| Agent | LLM | Role |
|-------|-----|------|
| **Ingestor** | No | Parses the circular into cite-able paragraphs; classifies it and scores urgency. |
| **Mapper** | Yes | Translates each paragraph into a **MAP** (Mapped Action Policy) with a mandatory verbatim citation. |
| **Validator** | Yes + hash check | Adversarially reviews each MAP; auto-rejects fabricated citations *before* the LLM via a substring hash check. |
| **Assigner** | Yes | Routes approved controls to departments with priority, deadline, and dependencies; escalates high/critical risk to the CCO. |
| **Evidence Checker** | Yes (plan only) | Emits a pandas query plan; Python deterministically runs it against synthetic bank data to count violations. The LLM never executes code. |
| **Auditor** | Yes (1 call) | Assembles the final cited Markdown report. |

### Reliability Mechanisms
- **Verbatim citation check** — every MAP must quote the regulation word-for-word; quotes that aren't a substring of the source are auto-rejected (`wrong_paragraph`) with no LLM call burned.
- **Adversarial retry loop** — the Validator rejects flawed controls with a quoted span; the Mapper retries with that feedback until the interpretation holds or the retry cap is reached.
- **Tamper-proof audit chain** — `entry_hash = sha256(prev_hash ‖ payload)`; editing any historical row breaks every subsequent hash, and the chain is verifiable end-to-end.
- **CCO escalation** — high/critical-risk controls are flagged for human sign-off ("agents propose, humans approve").
- **Honest evidence** — a control that can't actually be tested (e.g. rate-limited) is recorded as **Not evaluated**, never silently "compliant".

### The Console
The Next.js workspace ("Ledger" — a light, editorial design system) provides five views:
- **Overview** — compliance posture: controls, approvals, rejections, violations, escalations, department workload, compliance rate, and live audit-chain integrity.
- **Pipeline** — upload or select a circular and watch the six agents reason in real time (Server-Sent Events) over an animated agent-flow visualiser.
- **Circulars** — document intelligence: classification, urgency score, reference number, and a drag-and-drop uploader for your own RBI PDFs.
- **Controls** — every MAP with its citation, validation verdict, department routing, and evidence — plus the final report and the raw hash-chained audit trail.
- **Assistant** — a grounded compliance Q&A chatbot; every regulatory claim is cited, and if the answer isn't in the analysis it says so.

---

## Tech Stack
- **Backend:** Python 3.11+, FastAPI, Uvicorn
- **Orchestration:** LangGraph, Pydantic v2
- **LLM:** Groq Llama 3.3 70B (free tier)
- **Data & storage:** SQLite (SHA-256 hash-chained audit trail), pandas, pypdf / pdfplumber
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Type:** Fraunces (display) · Archivo (body) · IBM Plex Mono (data)
- **Testing:** pytest

---

## Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/DCode-v05/Compliance-Crew.git
cd Compliance-Crew
```

### 2. Backend setup (Python 3.11+)
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1            # Windows PowerShell  (or: source .venv/bin/activate)
pip install -r requirements.txt

cp .env.example .env                     # then add your free Groq key:
#   GROQ_API_KEY  ->  https://console.groq.com/keys

python scripts/seed_db.py --reset        # initialise a clean, hash-chained database
```
The synthetic bank data is included; regenerate it any time with
`python scripts/generate_synthetic_data.py`.

### 3. Frontend setup (Node 18+)
```bash
cd frontend
npm install
cp .env.local.example .env.local         # defaults to http://localhost:8000
cd ..
```

### 4. Run
The easiest way on Windows — from the repo root:
```powershell
.\start.ps1        # opens the API and the console in two windows
```
Or run each side manually:
```powershell
# Terminal 1 — API  (http://localhost:8000, Swagger at /docs)
uvicorn api.main:app --reload --port 8000

# Terminal 2 — Console  (http://localhost:3000)
cd frontend; npm run dev
```
Then open **http://localhost:3000**.

---

## Usage
- Open the console, go to **Circulars**, and drag in an RBI circular (PDF/TXT/MD) — or use the bundled sample KYC circular.
- On **Pipeline**, pick the circular and click **Run pipeline**; watch the six agents stream their reasoning live.
- Inspect the results on **Controls**: each control's citation, validation verdict, department routing, and evidence, plus the **Report** and **Audit trail** tabs.
- Ask questions on the **Assistant** — answers are grounded in the run and cited to the regulation.

**CLI-only** (no frontend): `python -m src.graph data/circulars/sample_kyc_paragraphs.txt`

Key API endpoints (interactive docs at `http://localhost:8000/docs`):

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/pipeline/run` | Run the pipeline (blocking) → summary |
| GET  | `/api/v1/pipeline/stream` | Live SSE stream of agent reasoning |
| GET  | `/api/v1/dashboard/stats` | Cumulative compliance metrics |
| GET  | `/api/v1/circulars` · `POST /circulars/upload` | List / upload circulars |
| GET  | `/api/v1/maps?run_id=` | Controls joined with validation, routing, evidence |
| POST | `/api/v1/chat` | Grounded compliance Q&A |
| GET  | `/api/v1/audit/chain` | Verify the SHA-256 audit chain |

---

## Project Structure
```
Compliance-Crew/
│
├── src/                     # LangGraph pipeline
│   ├── agents/              # ingestor, mapper, validator, assigner, evidence_checker, auditor
│   ├── prompts/             # system + user prompt templates
│   ├── utils/               # citation_check, audit_chain (SHA-256), pdf_parser
│   ├── state.py             # Pydantic shared state
│   ├── graph.py             # LangGraph wiring with the conditional retry edge
│   ├── db.py                # SQLite + hash-chained audit trail
│   └── llm.py               # llm_call() — Groq Llama 3.3 70B
│
├── api/                     # FastAPI backend
│   ├── main.py              # app + CORS + routers
│   ├── schemas.py           # typed request/response models
│   ├── services/            # pipeline, chat, dashboard, circular
│   └── routes/              # pipeline, circulars, maps, dashboard, chat, audit, health
│
├── frontend/                # Next.js 14 console ("Ledger" design system)
│   └── src/
│       ├── app/             # splash + console pages: dashboard, pipeline, circulars, maps, chat
│       ├── components/      # TopNav, AgentFlow, EventStream, CircularUpload, ui primitives
│       └── lib/             # typed API client + types
│
├── data/                    # sample circular + synthetic bank data
├── scripts/                 # generate_synthetic_data.py, seed_db.py, run_api.ps1, run_web.ps1
├── tests/                   # pytest suite (50 tests)
├── start.ps1                # one-shot launcher (API + console)
├── requirements.txt
└── README.md
```

---

## Contributing

Contributions are welcome! To contribute:
1. Fork the repository
2. Create a new branch:
   ```bash
   git checkout -b feature/your-feature
   ```
3. Commit your changes:
   ```bash
   git commit -m "Add your feature"
   ```
4. Push to your branch:
   ```bash
   git push origin feature/your-feature
   ```
5. Open a pull request describing your changes.

---

## Contact
- **GitHub:** [DCode-v05](https://github.com/DCode-v05)
- **Email:** denistanb05@gmail.com
