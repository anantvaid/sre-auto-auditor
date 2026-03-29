import os
import uuid
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path, override=True)

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", os.getenv("PROJECT_ID", ""))
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))

if not os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN") and not os.getenv("GITHUB_TOKEN"):
    print(f"WARNING: No GitHub token found in {env_path}")

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from agents.orchestrator import get_root_auditor

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="SRE Auto-Auditor API",
    description="An AI multi-agent system that audits repositories for SRE best practices.",
    version="1.0.0"
)

class AuditRequest(BaseModel):
    repo_url: str

@app.post("/audit")
async def run_audit(request: AuditRequest):
    logging.info(f"Received audit request for: {request.repo_url}")

    try:
        root_agent = get_root_auditor()
        session_service = InMemorySessionService()
        runner = Runner(
            agent=root_agent,
            app_name="sre-auditor",
            session_service=session_service
        )

        session = await session_service.create_session(  # await here
            app_name="sre-auditor",
            user_id="api",
            session_id=str(uuid.uuid4())
        )

        prompt = f"Please audit this repository for reliability risks: {request.repo_url}"
        content = types.Content(role="user", parts=[types.Part(text=prompt)])

        report = ""
        async for event in runner.run_async(             # run_async + async for
            user_id="api",
            session_id=session.id,
            new_message=content
        ):
            if event.is_final_response() and event.content and event.content.parts:
                report = event.content.parts[0].text

        return {
            "status": "success",
            "target": request.repo_url,
            "report": report
        }

    except Exception as e:
        logging.error(f"Audit failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sre-auto-auditor"}
