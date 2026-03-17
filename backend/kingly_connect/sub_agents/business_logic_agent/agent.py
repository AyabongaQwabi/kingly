"""Business logic agent: generates structured business logic from app description or PRD."""
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
    path = getattr(config, "BUSINESS_LOGIC_AGENT_PROMPT_PATH", None) or (
        config.REPO_ROOT / "docs" / "prompts" / "business-logic-agent.md"
    )
    if not path.exists():
        return (
            "You generate business logic (markdown) from an app description or PRD. "
            "Use create_document_tool to save with type='business_logic'. "
            "Project: {projectId?}. User: {userId?}. App description: {appDescription?}. RAG context: {ragContext?}."
        )
    text = path.read_text(encoding="utf-8")
    for k in ("projectId", "userId", "appDescription", "ragContext"):
        text = text.replace("{" + k + "}", "{" + k + "?}")
    return text


business_logic_agent = LlmAgent(
    name="business_logic_agent",
    model=config.get_agent_model(),
    description="Generates structured business logic from an app description or PRD; saves as markdown document.",
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
