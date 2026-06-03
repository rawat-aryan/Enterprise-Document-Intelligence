# Enterprise Document Intelligence Platform

Production-grade AI-powered platform for enterprise document processing, invoice automation, and business intelligence.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│   Streamlit Frontend  │  REST API Clients  │  Airflow Scheduler  │
└──────────────────┬────────────────┬────────────────┬─────────────┘
                   │                │                │
┌──────────────────▼────────────────▼────────────────▼─────────────┐
│                      API GATEWAY LAYER                            │
│              FastAPI (Async) + JWT Auth + RBAC                   │
└──────────────────┬────────────────┬────────────────┬─────────────┘
                   │                │                │
┌──────────────────▼────┐  ┌────────▼────────┐  ┌───▼──────────────┐
│    AI/ML SERVICES     │  │  DATA SERVICES  │  │  STORAGE LAYER   │
│  • Gemini Extraction  │  │  • PostgreSQL   │  │  • Google Cloud  │
│  • OCR Pipeline       │  │  • BigQuery DWH │  │    Storage       │
│  • RAG (ChromaDB)     │  │  • Redis Cache  │  │  • ChromaDB      │
│  • Recommendations    │  │  • Alembic Mig. │  │  • Local Files   │
└───────────────────────┘  └─────────────────┘  └──────────────────┘
```

## Quick Start

```bash
# Clone
git clone https://github.com/rawat-aryan/Enterprise-Document-Intelligence
cd Enterprise-Document-Intelligence

# Setup environment
cp .env.example .env
# Edit .env with your GEMINI_API_KEY and GCP credentials

# Option A: Docker Compose (recommended)
docker-compose up -d
# API: http://localhost:8000/docs
# Frontend: http://localhost:8501
# Airflow: http://localhost:8080
# MLflow: http://localhost:5000

# Option B: Local dev
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
uvicorn backend.app.main:app --reload &
streamlit run frontend/app.py
```

## Features

| Feature | Description |
|---------|-------------|
| Document Processing | Invoice, Contract, Report extraction via Gemini 1.5 Pro |
| OCR Pipeline | Tesseract + pdf2image for scanned PDFs and images |
| Bulk Processing | ZIP upload → parallel processing of thousands of documents |
| Duplicate Detection | Multi-signal detection (invoice#, vendor+amount, date) with risk scoring |
| Excel Reports | 5-sheet automated reports with openpyxl styling |
| RAG Search | LangChain + ChromaDB semantic document search |
| NL Analytics | Natural language → SQL via Gemini → BigQuery |
| Recommendations | AI-powered vendor performance and cost optimization |
| Multi-tenant | Full tenant isolation with JWT RBAC |
| BigQuery DWH | Fact/dim schema with vendor performance views |
| Dashboards | Plotly executive dashboards (spend, vendors, risk, trends) |

## Tech Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI + async SQLAlchemy 2.0 + Pydantic v2 |
| AI | Google Gemini 1.5 Pro + LangChain |
| OCR | Tesseract + pdf2image |
| Vector DB | ChromaDB |
| Database | PostgreSQL (prod) / SQLite (dev) |
| DWH | Google BigQuery |
| Storage | Google Cloud Storage |
| Messaging | Google Pub/Sub |
| Frontend | Streamlit + Plotly |
| Pipelines | Apache Airflow |
| MLOps | MLflow |
| DevOps | Docker + GitHub Actions CI/CD |
| IaC | Terraform |

## Project Structure

```
Enterprise-Document-Intelligence/
├── backend/app/
│   ├── api/v1/endpoints/    # REST: auth, documents, invoices, contracts, analytics, reports, recommendations
│   ├── core/                # security, logging, exceptions
│   ├── models/              # SQLAlchemy: User, Tenant, Document, Invoice, Contract
│   ├── schemas/             # Pydantic v2: all request/response models
│   └── services/            # gemini, ocr, extraction, validation, duplicate, excel, rag, bigquery
├── frontend/
│   ├── app.py               # Streamlit multi-page app + auth
│   └── pages/               # 7 pages: dashboard, upload, invoices, analytics, search, reco, reports
├── airflow/dags/            # 2 DAGs: document processing, BigQuery sync
├── infrastructure/
│   ├── bigquery/            # schemas + SQL views
│   └── terraform/           # GCP resources IaC
├── migrations/              # Alembic migrations
├── tests/                   # unit, integration, e2e
│   ├── unit/                # validation, duplicate detection, excel generation
│   └── integration/         # API endpoint tests
├── docker/                  # Dockerfile.backend, .frontend, .airflow
├── .github/workflows/       # CI (lint+test+build) + CD (Cloud Run deploy)
└── docker-compose.yml       # Full local dev stack
```

## API Endpoints

```
POST /api/v1/auth/register        Register new user
POST /api/v1/auth/login           Login → JWT token
GET  /api/v1/auth/me              Current user profile

POST /api/v1/documents/upload     Upload single document
POST /api/v1/documents/bulk-upload Upload ZIP of documents
GET  /api/v1/documents/           List documents (paginated)
GET  /api/v1/documents/{id}       Get document details

GET  /api/v1/invoices/            List invoices (with filters)
GET  /api/v1/invoices/stats       Invoice statistics
GET  /api/v1/invoices/duplicates  List duplicate invoices
GET  /api/v1/invoices/{id}        Get invoice details

GET  /api/v1/contracts/           List contracts
GET  /api/v1/contracts/{id}       Get contract details

POST /api/v1/analytics/query      Natural language → SQL → results
GET  /api/v1/analytics/spend      Spend analytics

GET  /api/v1/reports/excel        Generate Excel report (download)

GET  /api/v1/recommendations/vendors          Vendor performance AI
GET  /api/v1/recommendations/cost-optimization Cost savings analysis
GET  /api/v1/recommendations/contracts         Expiring contract alerts
```

## Environment Variables

See `.env.example` for all required configuration.

**Minimum required for local dev:**
```bash
SECRET_KEY=any-random-string-32-chars-min
# Gemini optional - falls back to regex extraction
GEMINI_API_KEY=your-key-from-makersuite.google.com
```

## Testing

```bash
pytest tests/ -v --cov=backend --cov-report=term-missing
```

## Deployment (GCP)

1. Set GitHub Secrets: `GCP_PROJECT_ID`, `WIF_PROVIDER`, `WIF_SERVICE_ACCOUNT`
2. Push to `main` → GitHub Actions deploys to Cloud Run
3. Set `SECRET_KEY` and `GEMINI_API_KEY` in Secret Manager

## License

Proprietary — Enterprise Use Only
