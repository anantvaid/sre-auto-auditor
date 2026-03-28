import os
from google.adk.agents import Agent
from tools.github_mcp import get_github_tool

model_name = os.getenv("MODEL", "gemini-2.5-flash")

def get_reliability_agents():
    github_tool = get_github_tool()

    auditor = Agent(
        name="reliability_auditor",
        model=model_name,
        description="Fetches code from GitHub and scans it for SRE anti-patterns.",
        instruction="""
        You are an SRE code reviewer. Please look at the code provided from {REPO_URL}.

        First, figure out what language or tool it is (like Go, Python, Kubernetes, or Terraform).
        Then, review it for common reliability and security mistakes.

        Keep an eye out for everyday SRE issues like:
        - Hardcoded passwords or API keys
        - Missing timeouts or lack of retries for network calls
        - Missing health checks or resource limits (especially for K8s)
        - Bad error handling or missing logs

        Output a short, easy-to-read report listing the main issues, why they matter, and a quick fix.
        """,
        tools=[github_tool],
        output_key="audit_raw_data"
    )

    formatter = Agent(
        name="report_formatter",
        model=model_name,
        description="Formats the raw audit into a clean markdown report.",
        instruction="""
        You are a Technical Writer for the SRE team. Take the raw audit data
        and format it into a professional, easy-to-read Markdown report.
        Use clear headings, bullet points, and highlight critical risks.

        RAW AUDIT DATA:
        {audit_raw_data}
        """
    )

    return auditor, formatter