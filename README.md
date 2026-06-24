# ComplianceCrew

**Six AI agents that read an RBI circular, turn it into auditable bank controls, and prove every claim with a verbatim citation and a tamper-evident hash chain.**

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white) ![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=flat&logo=langchain&logoColor=white) ![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=flat&logo=pydantic&logoColor=white) ![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-F55036?style=flat&logo=meta&logoColor=white) ![Next.js](https://img.shields.io/badge/Next.js_14-000000?style=flat&logo=nextdotjs&logoColor=white) ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white) ![pytest](https://img.shields.io/badge/pytest-50_tests-0A9EDC?style=flat&logo=pytest&logoColor=white)

## Overview

The Reserve Bank of India publishes a steady stream of circulars, and every regulated bank has to translate each one into concrete controls, assign an owner, set a deadline, and then prove compliance against live data. Done by hand it's slow and easy to get wrong. Done with a naive LLM it's worse — the model invents requirements and fabricates citations that look authoritative but don't exist in the source.

ComplianceCrew takes a regulatory circular (PDF or text) and runs it through six specialist agents wired together as a LangGraph state machine. They read the document, derive control requirements, adversarially check each other's interpretations against the source text, route the work to bank departments, test sample bank data for actual violations, and assemble an audit-ready report. Two things make it usable in a compliance setting rather than just a demo: every claim is tied to a verbatim quote from the regulation, and every model call is folded into a SHA-256 hash chain so the audit trail is provably untampered.

It was built for the **SuRaksha Cyber Hackathon 2.0** (Canara Bank track) and runs entirely on a free-tier model — Groq's Llama 3.3 70B — with no paid LLM APIs anywhere in the stack. The whole thing ships as a web console where a compliance officer uploads a circular and watches the agents reason in real time.

## Key Features

- **Six-agent pipeline on LangGraph** — Ingestor → Mapper → Validator → Assigner → Evidence Checker → Auditor, sharing one Pydantic-typed state object so no untyped dicts cross node boundaries.
- **Verbatim citation guardrail** — every control must quote the regulation word-for-word; a quote that isn't a substring of the source is auto-rejected *before* an LLM call is spent.
- **Adversarial retry loop** — the Validator reviews each control and, on rejection, sends it back to the Mapper with a quoted span as feedback. Retries are capped at 2 attempts per paragraph.
- **Tamper-evident SHA-256 audit chain** — one hash-chained row per agent invocation, verifiable end-to-end; editing any historical row breaks every hash that follows it.
- **LLM-proposes / Python-executes evidence checks** — the Evidence Checker emits a structured query plan; Python deterministically runs it against the bank data. The model never executes code.
- **Department routing and CCO escalation** — approved controls are routed to one of six departments with a priority and deadline; high/critical-risk findings are escalated to the Chief Compliance Officer for human sign-off.
- **Honest "Not evaluated" state** — a control that genuinely couldn't be tested is recorded as un-evaluated, never silently marked compliant.
- **Live streaming console** — a Next.js 14 workspace with five views; the Pipeline view streams agent reasoning over Server-Sent Events.
- **Grounded Q&A assistant** — a chatbot that answers compliance questions from the run, cites the regulation, and admits when the answer isn't in the analysis.
- **Typed REST + SSE API** — FastAPI backend with Swagger docs and an endpoint to re-verify the audit chain on demand.
- **50 pytest tests** covering the agents, the audit chain, the citation check, the graph wiring, and the DB layer.

## How It Works

### The shared state

Everything hangs off a single `ComplianceState` Pydantic model (`src/state.py`). Each node reads from it and writes back to it — paragraphs, MAPs (Mapped Action Policies), validations, assignments, escalations, evidence checks, the final report, and the routing flags that drive the conditional edge. Citation is a required field on every MAP and every evidence check, so a control physically cannot exist in the state without a `paragraph_id`, a verbatim quote, a confidence score, and a source document id.

### The pipeline

```
PDF/TXT → Ingestor → Mapper → Validator → Assigner → Evidence Checker → Auditor → Report
            (classify)  ▲          │        (route +      (query bank        (cited
                        └─ retry ──┘         escalate)      data)             memo)
                       conditional edge on rejection (cap = 2)
```

The Validator's conditional edge back to the Mapper is the spine of the design (`src/graph.py`). After validation, `route_after_validation()` checks `rejected_map_ids`: if every rejected MAP has already hit the retry cap, it proceeds to the Assigner; otherwise it loops back to the Mapper to try again with the feedback.

### The agents

- **Ingestor** (no LLM) — parses the circular into cite-able paragraphs with section titles and page numbers, classifies the document, and scores its urgency. Deterministic, so the cheap structural work doesn't burn tokens.
- **Mapper** (LLM) — translates each paragraph into a MAP: a control title and description, an evidence type, a risk category, and a mandatory citation. This is where regulation becomes an actionable control.
- **Validator** (LLM + pre-LLM hash check) — adversarially reviews each MAP. Before the model is even called, a substring check (`src/utils/citation_check.py`) rejects any quote that isn't found verbatim in the source paragraph, tagged `wrong_paragraph`. Surviving MAPs are then reasoned over and either approved or rejected with a quoted span and a rejection category.
- **Assigner** (LLM) — routes approved controls to one of six departments (IT/Digital, Retail Banking, Risk/AML, HR/Training, Legal/Compliance, Operations) with a priority, a deadline in days, and any cross-control dependencies. High and critical findings produce an Escalation to the CCO.
- **Evidence Checker** (LLM for the plan only) — for each approved MAP it asks the model for a `QueryPlan` (which dataset, which filter expression, which columns). Python then loads the right CSV and runs `DataFrame.query()` on it (`src/agents/evidence_checker.py`). A malformed query is caught and recorded as an un-evaluated check rather than a false pass — the LLM proposes, Python decides.
- **Auditor** (single LLM call) — assembles the final cited Markdown report from everything in the state.

### The audit chain

`src/utils/audit_chain.py` is a real, working hash-chained ledger, not a stub. Every LLM call is logged through one wrapper (`src/llm.py`), which means the audit trail is built for free as a side effect of normal operation. Each row stores `prev_hash` and `entry_hash = sha256(prev_hash ‖ canonical_payload)`, the genesis hash is 64 zeros, and the canonical payload is a fixed-order, unit-separator (`\x1f`) delimited string so the same logical row always hashes identically. `verify_chain()` walks the rows, recomputes the chain, and reports the 1-based index of the first row whose stored hash disagrees with the recomputed value. A regulator can call the verify endpoint and confirm nothing was edited after the fact.

### The LLM wrapper

All six agents go through `llm_call()` (`src/llm.py`), which targets Groq's `llama-3.3-70b-versatile`. It enforces structured output via a compact JSON-schema hint plus `response_format=json_object`, strips stray code fences, validates the response against the agent's Pydantic schema, logs the audit entry, and retries with exponential backoff — failing fast on permanent errors like a bad API key so a misconfiguration doesn't waste the free-tier token budget.

### The console

The Next.js 14 frontend ("Ledger" — a light, editorial design system using Fraunces, Archivo, and IBM Plex Mono) has five views:

- **Overview** — compliance posture: control counts, approvals, rejections, violations, escalations, department workload, compliance rate, and live audit-chain integrity.
- **Pipeline** — upload or pick a circular and watch the six agents reason in real time over an animated agent-flow visualiser, fed by an `EventSource` SSE stream.
- **Circulars** — document intelligence (classification, urgency, reference number) with a drag-and-drop uploader for your own RBI PDFs.
- **Controls** — every MAP with its citation, validation verdict, routing, and evidence, plus the final report and the raw hash-chained audit trail.
- **Assistant** — the grounded compliance Q&A chatbot.

## Results / Highlights

- **Six-agent pipeline** with a working adversarial retry loop (cap = 2) and a fully verifiable SHA-256 audit chain — `verify_chain()` pinpoints the first tampered row.
- **~4,900 lines of Python** (agents, API, scripts, tests) and **~2,100 lines of TypeScript/TSX** for the console.
- **50 pytest test functions** across the agents, audit chain, citation check, graph, DB, and LLM wrapper.
- **Synthetic bank dataset generated in-house**: 10,000 customers and 50,000 transactions, with deliberately seeded violations (e.g. 200 unflagged large transactions over ₹10 lakh) so the Evidence Checker has real anomalies to find.
- **Zero paid LLM spend** — runs entirely on free-tier Groq Llama 3.3 70B (~300 tok/s), and the JSON-schema hints are minified specifically to stretch the free daily token budget.

## Tech Stack

- **Language(s):** Python 3.11+, TypeScript
- **Backend / orchestration:** FastAPI, Uvicorn, LangGraph, Pydantic v2
- **LLM:** Groq Llama 3.3 70B (`llama-3.3-70b-versatile`, free tier)
- **Data / ML:** pandas, pypdf, pdfplumber, SQLite (SHA-256 hash-chained audit trail)
- **Frontend:** Next.js 14 (App Router), React, Tailwind CSS, Server-Sent Events
- **Testing / tooling:** pytest, pytest-asyncio, PowerShell launch scripts

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- A free Groq API key from https://console.groq.com/keys

### Installation

```bash
git clone https://github.com/DCode-v05/Compliance-Crew.git
cd Compliance-Crew

# Backend (Python 3.11+)
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env               # then add GROQ_API_KEY
python scripts/seed_db.py --reset  # initialise a clean, hash-chained database

# Frontend (Node 18+)
cd frontend
npm install
cp .env.local.example .env.local   # defaults to http://localhost:8000
cd ..
```

The synthetic bank data is included; regenerate it any time with `python scripts/generate_synthetic_data.py`.

### Running

```powershell
# Windows, from the repo root — opens API + console in two windows
.\start.ps1
```

Or run each side manually:

```bash
# Terminal 1 — API (http://localhost:8000, Swagger at /docs)
uvicorn api.main:app --reload --port 8000

# Terminal 2 — Console (http://localhost:3000)
cd frontend && npm run dev
```

Then open http://localhost:3000.

## Usage

1. Open the console, go to **Circulars**, and drag in an RBI circular (PDF/TXT/MD) — or use the bundled sample KYC paragraphs.
2. On **Pipeline**, pick the circular and click **Run pipeline**; watch the six agents stream their reasoning live.
3. Inspect results on **Controls**: each control's citation, validation verdict, department routing, and evidence, plus the **Report** and **Audit trail** tabs.
4. Ask questions on the **Assistant** — answers are grounded in the run and cited to the regulation.

CLI-only (no frontend):

```bash
python -m src.graph data/circulars/sample_kyc_paragraphs.txt
```

Key API endpoints (interactive docs at `http://localhost:8000/docs`):

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/pipeline/run` | Run the pipeline to completion → summary |
| GET  | `/api/v1/pipeline/stream` | Live SSE stream of agent reasoning |
| GET  | `/api/v1/dashboard/stats` | Compliance posture for the Overview |
| GET  | `/api/v1/circulars` · POST `/upload` | List circulars / upload a PDF |
| GET  | `/api/v1/maps` | Controls with citation, verdict, routing |
| POST | `/api/v1/chat` | Grounded compliance Q&A |
| GET  | `/api/v1/audit/chain` | Re-verify the SHA-256 audit chain |

## Project Structure

```
Compliance-Crew/
├── src/
│   ├── graph.py                  # LangGraph wiring + the conditional retry edge
│   ├── state.py                  # ComplianceState — the typed shared state
│   ├── llm.py                    # single Groq entry point, audit logging, retries
│   ├── db.py                     # SQLite persistence for the hash chain
│   ├── agents/                   # ingestor, mapper, validator, assigner,
│   │                             #   evidence_checker, auditor
│   ├── prompts/                  # one prompt module per agent + chatbot
│   └── utils/
│       ├── audit_chain.py        # SHA-256 hash chain + verify_chain()
│       ├── citation_check.py     # verbatim substring guardrail
│       └── pdf_parser.py         # PDF/TXT → cite-able paragraphs
├── api/
│   ├── main.py                   # FastAPI app, CORS, router wiring
│   ├── routes/                   # pipeline, dashboard, circulars, maps, chat, audit, health
│   ├── services/                 # pipeline / circular / dashboard / chat services
│   └── schemas.py                # API request/response models
├── frontend/                     # Next.js 14 console ("Ledger" design system)
│   └── src/app/(console)/        # dashboard, pipeline, circulars, maps, chat views
├── scripts/
│   ├── generate_synthetic_data.py# 10k customers / 50k transactions with seeded violations
│   ├── seed_db.py                # initialise the hash-chained DB
│   └── run_api.ps1 / run_web.ps1 # launch helpers
├── data/
│   ├── circulars/                # sample KYC paragraphs
│   └── synthetic_bank/           # customers.csv, transactions.csv
├── tests/                        # 50 pytest functions
├── .claude/skills/regulation-citation/SKILL.md  # citation contract as a Claude skill
├── start.ps1                     # one-shot Windows launcher
├── pyproject.toml / requirements.txt
└── README.md
```

---

## Contact

<table>
  <tr><td><b>Portfolio:</b> <a href="https://www.denistan.me">Denistan</a></td><td><b>LinkedIn:</b> <a href="https://www.linkedin.com/in/denistanb">denistanb</a></td></tr>
  <tr><td><b>GitHub:</b> <a href="https://github.com/DCode-v05">DCode-v05</a></td><td><b>LeetCode:</b> <a href="https://leetcode.com/u/Denistan_B">Denistan_B</a></td></tr>
  <tr><td colspan="2" align="center"><b>Email:</b> <a href="mailto:denistanb05@gmail.com">denistanb05@gmail.com</a></td></tr>
</table>

Made with ❤️ by **Denistan B**
