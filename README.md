# Agentic Financial Operations Intelligence Platform

Multi-agent AI system for financial fraud and complaint investigation using FastAPI, LangGraph-style orchestration, PostgreSQL, RAG, and human approval.

## What This Includes

- FastAPI service with investigation and approval endpoints
- Agent workflow for intake, evidence retrieval, fraud analysis, complaint analysis, decisioning, and human approval
- PostgreSQL-ready SQLAlchemy models
- RAG service abstraction with a deterministic local retriever for development
- Docker Compose for API and PostgreSQL
- Pytest starter coverage for the main workflow

## Quick Start

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

API docs will be available at `http://127.0.0.1:8000/docs`.

## Docker

```bash
docker compose up --build
```

## Core Flow

1. A case is submitted through `POST /cases`.
2. The workflow classifies the case and retrieves supporting policy or transaction evidence.
3. Specialist agents assess fraud signals and complaint obligations.
4. A decision agent recommends an action.
5. High-risk or customer-impacting cases pause for human approval.
6. An approver records a final decision through `POST /cases/{case_id}/approval`.

## API

### Create Case

```http
POST /cases
```

```json
{
  "customer_id": "cust_123",
  "case_type": "fraud",
  "summary": "Customer disputes three card transactions.",
  "amount": 984.23,
  "currency": "USD",
  "channel": "mobile",
  "metadata": {
    "merchant": "EXAMPLE STORE"
  }
}
```

### Get Case

```http
GET /cases/{case_id}
```

### Approve Case

```http
POST /cases/{case_id}/approval
```

```json
{
  "approved": true,
  "reviewer": "ops.lead@example.com",
  "notes": "Evidence supports temporary credit and escalation."
}
```

## Development Notes

The current implementation uses a deterministic local RAG retriever and rule-based agents so the system is runnable without external model credentials. The `app/services/llm.py` boundary is where hosted model providers can be added.
