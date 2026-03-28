# SRE Auto-Auditor

An AI-powered multi-agent system that automatically audits GitHub repositories for **Site Reliability Engineering (SRE) best practices**, security vulnerabilities, and reliability anti-patterns.

Built with **Google Agent Development Kit (ADK)**, **Gemini 2.5 Flash** on **Vertex AI**, and deployed on **Google Cloud Run**.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Local Setup](#local-setup)
- [Project Structure](#project-structure)
- [Deployment to Cloud Run](#deployment-to-cloud-run)
- [API Reference](#api-reference)
- [Agent Pipeline](#agent-pipeline)
- [Contributing](#contributing)

---

## Overview

SRE Auto-Auditor takes a GitHub repository URL and returns a detailed Markdown report highlighting:

- Hardcoded secrets and API keys
- Missing timeouts and retry logic
- Missing health checks and resource limits (Kubernetes)
- Poor error handling and missing observability
- What the repo is already doing well

It uses a **sequential multi-agent pipeline** — one agent fetches and audits the code, another formats the findings into a clean, professional report.

---

## Architecture

```
User Request (repo URL)
        │
        ▼
┌─────────────────────┐
│   api_receiver      │  ← Root orchestrator agent
│   (FastAPI Entry)   │    Saves repo URL to shared state
└────────┬────────────┘
         │ delegates to
         ▼
┌─────────────────────┐
│   audit_workflow    │  ← SequentialAgent
│                     │
│  1. reliability_    │  ← Fetches code via GitHub MCP
│     auditor         │    Scans for SRE anti-patterns
│                     │    
│  2. report_         │  ← Formats raw findings into
│     formatter       │    clean Markdown report
└─────────────────────┘
         │
         ▼
   Markdown Report
```

**Key technologies:**

| Component | Technology |
|---|---|
| Agent Framework | Google ADK |
| LLM | Gemini 2.5 Flash (Vertex AI) |
| GitHub Integration | GitHub MCP Server (remote HTTP) |
| API Server | FastAPI + Uvicorn |
| Deployment | Google Cloud Run |
| Secrets | Google Secret Manager |

---

## Features

- **Multi-agent pipeline** — specialised agents for auditing and formatting
- **GitHub MCP integration** — reads real repository contents via the official GitHub MCP server
- **Supports multiple languages** — Python, Go, Java, Kubernetes YAML, Terraform, and more
- **Clean Markdown reports** — structured findings with severity levels and fix recommendations
- **Built-in web UI** — simple HTML frontend to submit repos and view reports
- **Cloud-native** — fully serverless on Cloud Run with Vertex AI auth via ADC

---

## Prerequisites

- Python 3.11+
- A Google Cloud project with billing enabled
- A GitHub Personal Access Token (PAT) with `repo` and `read:org` scopes
- `gcloud` CLI installed and authenticated

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/sre-auto-auditor.git
cd sre-auto-auditor
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
PROJECT_ID=$(gcloud config get-value project)

cat <<EOF > .env
PROJECT_ID=$PROJECT_ID
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GOOGLE_CLOUD_LOCATION=us-central1
MODEL=gemini-2.5-flash
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_pat_here
EOF
```

### 4. Authenticate with Google Cloud

```bash
gcloud auth application-default login
```

### 5. Run the server

```bash
uvicorn main:app --reload --port 8000
```

The API is now available at `http://localhost:8000`.

---

## Project Structure

```
sre-auto-auditor/
├── main.py                  # FastAPI app entry point
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── .env                     # Local config (never commit this)
├── ui/
│   └── index.html           # Web UI frontend
├── agents/
│   ├── orchestrator.py      # Root agent + workflow assembly
│   └── reliability_agent.py # Auditor + formatter agents
└── tools/
    └── github_mcp.py        # GitHub MCP server connection
```

---

## Deployment to Cloud Run

### 1. Enable required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com
```

### 2. Create a service account

```bash
gcloud iam service-accounts create sre-auditor-sa \
  --display-name="SRE Auditor Service Account"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:sre-auditor-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

### 3. Store your GitHub token in Secret Manager

```bash
echo -n "your_github_pat_here" | \
  gcloud secrets create GITHUB_PERSONAL_ACCESS_TOKEN --data-file=-

gcloud secrets add-iam-policy-binding GITHUB_PERSONAL_ACCESS_TOKEN \
  --member="serviceAccount:sre-auditor-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 4. Deploy

```bash
gcloud run deploy sre-auto-auditor \
  --source . \
  --project=$PROJECT_ID \
  --region=us-central1 \
  --service-account=sre-auditor-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=us-central1,MODEL=gemini-2.5-flash" \
  --set-secrets="GITHUB_PERSONAL_ACCESS_TOKEN=GITHUB_PERSONAL_ACCESS_TOKEN:latest" \
  --allow-unauthenticated \
  --memory=1Gi \
  --timeout=300 \
  --port=8080
```

---

## API Reference

### `POST /audit`

Audits a GitHub repository and returns a Markdown report.

**Request:**
```json
{
  "repo_url": "https://github.com/owner/repository"
}
```

**Response:**
```json
{
  "status": "success",
  "target": "https://github.com/owner/repository",
  "report": "# Reliability Audit Report\n\n..."
}
```

**Example:**
```bash
curl -X POST https://your-service-url/audit \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/GoogleCloudPlatform/microservices-demo"}'
```

### `GET /health`

Health check endpoint for Cloud Run readiness probes.

**Response:**
```json
{
  "status": "healthy",
  "service": "sre-auto-auditor"
}
```

### `GET /`

Serves the web UI for submitting audit requests interactively.

---

## Agent Pipeline

The system uses a **three-agent sequential pipeline**:

### 1. `api_receiver` (Orchestrator)
- Receives the repository URL from the API request
- Saves it to shared ADK state using `add_target_to_state`
- Delegates to the `audit_workflow` sequential agent

### 2. `reliability_auditor`
- Connects to the GitHub repository via the **GitHub MCP Server**
- Detects the language/framework (Python, Go, K8s, Terraform, etc.)
- Scans for SRE anti-patterns across these categories:
  - Hardcoded credentials
  - Missing network timeouts and retries
  - Missing Kubernetes health checks and resource limits
  - Poor error handling and insufficient logging
  - Missing observability (metrics, tracing)
- Outputs raw findings to shared state as `audit_raw_data`

### 3. `report_formatter`
- Reads `audit_raw_data` from shared state
- Produces a professional, structured Markdown report with:
  - Clear severity levels (Critical / High / Medium / Low)
  - Explanation of each issue and its impact
  - Concrete fix recommendations

---

## Troubleshooting

**`429 RESOURCE_EXHAUSTED`** — You've hit Vertex AI's rate limit. Wait 1-2 minutes and retry, or switch to `gemini-2.0-flash`:
```bash
gcloud run services update sre-auto-auditor \
  --region=us-central1 \
  --update-env-vars="MODEL=gemini-2.0-flash"
```

**`Failed to create MCP session`** — Check that your `GITHUB_PERSONAL_ACCESS_TOKEN` is valid and has `repo` scope.

**`No API key was provided`** — Run `gcloud auth application-default login` locally, or ensure the Cloud Run service account has the `roles/aiplatform.user` role.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
