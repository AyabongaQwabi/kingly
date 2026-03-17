"""PRD agent: generates a Product Requirements Document from an app description."""
from pathlib import Path

from google.adk.agents import LlmAgent

from ... import config
from ...tools import (
    create_document_tool,
    get_document_tool,
    get_project_tool,
    list_documents_tool,
    vector_search_tool,
)


def _load_instruction() -> str:
    path = getattr(config, "PRD_AGENT_PROMPT_PATH", None) or (
        config.REPO_ROOT / "docs" / "prompts" / "prd-agent.md"
    )
    if not path.exists():
        return (
            "You generate a PRD (markdown) from an app description. "
            "Use create_document_tool to save with type='prd'. "
            "Project: {projectId?}. User: {userId?}. App description: {appDescription?}. RAG context: {ragContext?}."
        )
    text = path.read_text(encoding="utf-8")
    for k in ("projectId", "userId", "appDescription", "ragContext"):
        text = text.replace("{" + k + "}", "{" + k + "?}")
    return text


prd_agent = LlmAgent(
    name="prd_agent",
    model=config.get_agent_model(),
    description="Generates a Product Requirements Document from an app description; saves as markdown.",
    instruction=_load_instruction(),
    tools=[
        create_document_tool,
        get_document_tool,
        get_project_tool,
        list_documents_tool,
        vector_search_tool,
    ],
    sub_agents=[],
)
