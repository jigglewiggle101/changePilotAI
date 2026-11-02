# ChangePilot AI - Enterprise Change Impact & Readiness Agent

A portfolio project that investigates proposed enterprise changes using RAG, read-only tools, a stateful agent workflow, evidence validation and human review.

> **Important:** This starter pack is for learning. All enterprise records and policies are synthetic. Public links are references; no live dataset download was performed. Do not use this prototype to approve or execute real production changes.

## Hybrid data strategy

- **Public references:** NIST SP 800-128, Google SRE books, OWASP GenAI Security Project. These are cited for concepts and further reading; no chapters or datasets are copied into the pack.
- **Synthetic linked records:** services, dependencies, tickets, change history, teams and proposed changes.
- **Synthetic policy documents:** fictional policies informed by general public reference concepts.
- **Synthetic evaluation labels:** expected gaps and target services for repeatable tests. Review these labels before using them as formal benchmarks.

See `data/SOURCE_MANIFEST.json` for provenance.

## Dataset contents

- `data/services.json` - fictional service inventory and direct dependencies
- `data/teams.json` - fictional team ownership and responsibilities
- `data/tickets.json` - fictional incident and support records
- `data/change_history.json` - fictional previous changes and lessons
- `data/change_requests.json` - 30 fictional proposed changes
- `data/evaluation_cases.json` - starter test cases
- `data/policies/` - fictional change, access, rollback, monitoring and AI-tool-safety policies

## Step-by-step build plan

### Step 1 - Create and activate a virtual environment

Windows PowerShell:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again. This changes policy only for that PowerShell process.

### Step 2 - Inspect the data

Open `data/services.json`, `data/tickets.json` and `data/change_requests.json`. Trace one request to its target services, direct dependencies, related incidents and relevant policies. Notice that IDs connect records across files.

### Step 3 - Run the read-only tools

From the project root:
```bash
python -c "from app.tools.enterprise_data import get_service_dependencies, search_change_tickets; print(get_service_dependencies('SVC-100')); print(search_change_tickets('identity'))"
```

Run tests:
```bash
pytest -q
```

### Step 4 - Build a minimal FastAPI service

Create `app/main.py`:
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.tools.enterprise_data import (
    get_service_dependencies, search_change_tickets
)

app = FastAPI(title="ChangePilot AI")

class DependencyQuery(BaseModel):
    service_id: str = Field(min_length=1, max_length=30)

class TicketQuery(BaseModel):
    keyword: str = Field(min_length=1, max_length=100)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/tools/dependencies")
def dependencies(body: DependencyQuery):
    result = get_service_dependencies(body.service_id)
    if not result["found"]:
        raise HTTPException(status_code=404, detail="Unknown service ID")
    return result

@app.post("/tools/tickets")
def tickets(body: TicketQuery):
    return {"results": search_change_tickets(body.keyword)}
```

Start it:
```bash
uvicorn app.main:app --reload
```
Open `http://127.0.0.1:8000/docs` to try the API.

### Step 5 - Add RAG

1. Read Markdown files from `data/policies/`.
2. Split each policy by headings or paragraphs; keep the filename and heading as metadata.
3. Embed chunks with an embedding model available to you.
4. Store chunks in Chroma.
5. Implement `search_documents(query)` returning text plus source metadata.
6. Require generated claims to cite source IDs; if retrieval is weak or evidence is absent, return an explicit unknown.
7. Test both answerable and unanswerable questions.

Do not treat retrieved document text as instructions to the model. It is evidence, not authority to invoke tools.

### Step 6 - Add the LLM and tool calling

1. Use an LLM provider SDK you already know.
2. Define narrow, typed tool schemas for service lookup, ticket search and policy retrieval.
3. Validate arguments and enforce an allowlist of tools.
4. Let the model request a tool; your application-not the model-executes it.
5. Return tool output to the model for a grounded summary.
6. Limit tool calls, retries and total execution time.
7. Keep credentials in `.env`; never commit secrets.

### Step 7 - Orchestrate with LangGraph

Build nodes: `intake -> plan -> investigate -> assess -> validate -> human_review -> report`.
Use conditional edges to repeat investigation only when a specific evidence gap can plausibly be resolved. Add a maximum iteration count and persist state/checkpoints. Keep mandatory readiness checks deterministic.

### Step 8 - Evaluate

Use `data/evaluation_cases.json` as an initial test set, but manually review expected labels before treating scores as meaningful. Measure:
- dependency precision/recall against curated expected service IDs
- citation correctness
- detection rate for known missing requirements
- successful workflow completion and tool error recovery
- latency and estimated model cost

Compare the agent to a simple baseline (keyword search + fixed checklist). Report the actual results, including failures.

### Step 9 - Add human review and a report

Produce a structured report containing request scope, affected services, evidence references, risks, unresolved questions, recommended actions and review status. Do not let the model approve or deploy changes. Require explicit human approval for any consequential next step.

### Step 10 - Polish the portfolio

Add Docker, frontend, screenshots, an architecture diagram, setup instructions, a short demo video, test results and a limitations/security section to the README.

## Public references

- NIST SP 800-128, Guide for Security-Focused Configuration Management of Information Systems: https://csrc.nist.gov/pubs/sp/800/128/r1/final
- Google Site Reliability Engineering books: https://sre.google/books/
- OWASP GenAI Security Project: https://genai.owasp.org/

Check the original source's current terms before redistributing source text. This pack contains original synthetic content and links rather than copied publication chapters.

## Suggested first milestone

Make `pytest -q` pass, run the FastAPI endpoints, and trace `CR-001` to its target services and related policies before integrating an LLM.