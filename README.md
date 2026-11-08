# ComplianceCrew

Six agents that read an RBI circular, turn it into bank controls, check them against sample bank data, and write an audit report. Every control has to quote the regulation word for word, and every LLM call is logged in a SHA-256 hash chain so the audit trail can be verified afterwards.

Banks have to turn each circular into concrete controls, give each an owner and a deadline, and then show they comply. A plain LLM tends to invent requirements and cite text that is not in the source, so the pipeline checks every citation against the document and keeps the model away from anything it could get wrong silently. I built it for the SuRaksha Cyber Hackathon 2.0 (Canara Bank track). It runs on Groq's free-tier Llama 3.3 70B.

## How it works

The agents are a LangGraph graph (`src/graph.py`) sharing one Pydantic `ComplianceState` (`src/state.py`). Every control in the state has a paragraph id, a verbatim quote, a confidence and a source document id.

```
PDF/TXT -> Ingestor -> Mapper -> Validator -> Assigner -> Evidence Checker -> Auditor -> report
                         ^          |
                         +- retry --+   (on rejection, at most 2 retries)
```

- **Ingestor** (no LLM): splits the circular into citable paragraphs with section titles and page numbers, classifies it and scores urgency.
- **Mapper** (LLM): turns each paragraph into a control with a title, description, evidence type, risk category and citation.
- **Validator** (LLM): first a substring check (`src/utils/citation_check.py`) rejects any quote that is not in the source paragraph, before any model call is spent. The rest are reviewed by the model and approved or rejected with a quoted span. Rejected controls go back to the Mapper with that feedback.
- **Assigner** (LLM): routes each approved control to one of six departments with a priority and a deadline in days. High and critical items are escalated to the Chief Compliance Officer.
- **Evidence Checker** (LLM plans, Python runs): the model proposes a query plan (dataset, filter, columns) and Python runs it with `DataFrame.query()` on the bank CSVs. A malformed query is recorded as not evaluated instead of a pass.
- **Auditor** (one LLM call): assembles the cited Markdown report.

All model calls go through `llm_call()` in `src/llm.py`, which asks Groq for JSON, validates it against the agent's schema, retries with backoff, and writes an audit row. Each row stores `prev_hash` and `entry_hash = sha256(prev_hash || canonical payload)` (`src/utils/audit_chain.py`, SQLite via `src/db.py`), and `verify_chain()` reports the first row whose hash no longer matches.

The web console is a Next.js 14 app with Overview, Pipeline (live agent output over Server-Sent Events), Circulars (upload), Controls (citations, verdicts, routing, report, audit trail) and Assistant (a Q&A chatbot grounded in the run).

## Data

`data/synthetic_bank/` has 10,000 customers and 50,000 transactions made by `scripts/generate_synthetic_data.py`, with violations seeded on purpose, for example 200 transactions above INR 10 lakh that are not flagged. `data/circulars/sample_kyc_paragraphs.txt` is a short sample circular. The real RBI KYC Master Direction PDF is not in the repo; `data/circulars/README.md` says where to put it.

## Tech stack

- Python 3.11+, FastAPI, Uvicorn, LangGraph, Pydantic v2
- Groq (`llama-3.3-70b-versatile`), pandas, pypdf, pdfplumber, SQLite
- Next.js 14 (App Router), React, Tailwind CSS
- pytest, pytest-asyncio

## Setup

You need Python 3.11+, Node.js 18+ and a free Groq API key from https://console.groq.com/keys.

```bash
git clone https://github.com/DCode-v05/Compliance-Crew.git
cd Compliance-Crew

python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env               # add GROQ_API_KEY
python scripts/seed_db.py --reset  # create an empty hash-chained database

cd frontend
npm install
cp .env.local.example .env.local   # API base URL, defaults to http://localhost:8000
```

## Running

On Windows, `.\start.ps1` opens the API and the console in two windows. Or by hand:

```bash
uvicorn api.main:app --reload --port 8000     # API, Swagger at /docs
cd frontend && npm run dev                    # console on http://localhost:3000
```

Without the frontend:

```bash
python -m src.graph data/circulars/sample_kyc_paragraphs.txt
```

Tests: `pytest`.

Main API routes, all under `/api/v1`:

- `POST /pipeline/run` runs the pipeline and returns a summary
- `GET /pipeline/stream` streams agent output over SSE
- `GET /dashboard/stats`
- `GET /circulars`, `POST /circulars/upload`
- `GET /maps` lists controls with citation, verdict and routing
- `POST /chat`
- `GET /audit/chain` re-verifies the hash chain

## Project structure

```
src/
  graph.py, state.py, llm.py, db.py
  agents/       ingestor, mapper, validator, assigner, evidence_checker, auditor
  prompts/      one prompt module per agent, plus the chatbot
  utils/        audit_chain, citation_check, pdf_parser
api/            FastAPI app: routes, services, schemas
frontend/       Next.js console
scripts/        synthetic data generator, DB seeding, launch scripts
data/           sample circular, synthetic bank CSVs
tests/          pytest suite
.claude/skills/regulation-citation/   the citation rules as a Claude skill
```

## Limitations

The LLM stages depend on a free-tier Groq quota, and the evidence checks only run against the synthetic data, not real bank records.

## Contact

Denistan B: [portfolio](https://www.denistan.me), [LinkedIn](https://www.linkedin.com/in/denistanb), [GitHub](https://github.com/DCode-v05)
