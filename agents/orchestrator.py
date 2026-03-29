import os
import logging
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools.tool_context import ToolContext
from agents.reliability_agent import get_reliability_agents

def add_target_to_state(tool_context: ToolContext, repo_url: str) -> dict[str, str]:
    """Saves the target repository URL to the shared ADK state."""
    tool_context.state["REPO_URL"] = repo_url
    logging.info(f"[State updated] Added to REPO_URL: {repo_url}")
    return {"status": "success"}

def get_root_auditor() -> Agent:
    model_name = os.getenv("MODEL", "gemini-2.5-flash")

    auditor, formatter = get_reliability_agents()  # unpack the two agents

    audit_workflow = SequentialAgent(
        name="audit_workflow",
        description="The main pipeline for fetching code and auditing it.",
        sub_agents=[auditor, formatter]  # flat list, not a tuple
    )

    return Agent(
        name="api_receiver",
        model=model_name,
        description="The main entry point for the SRE Auditor API.",
        instruction="""
        You are the API Orchestrator. 
        When you receive a repository URL, use the 'add_target_to_state' tool to save it.
        After saving, immediately transfer control to the 'audit_workflow' agent.
        """,
        tools=[add_target_to_state],
        sub_agents=[audit_workflow]
    )
