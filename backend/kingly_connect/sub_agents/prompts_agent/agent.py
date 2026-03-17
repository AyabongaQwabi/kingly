"""Prompts agent: generates 3–5 build prompts from business logic and PRD."""
from pathlib import Path

from google.adk.agents import LlmAgent

from ... import config
from ...tools import (
    create_document_tool,
    get_document_tool,
    get_project_tool,
    list_documents_tool,
)


def _load_instruction() -> str:
    path = getattr(config, "PROMPTS_AGENT_PROMPT_PATH", None) or (
        config.REPO_ROOT / "docs" / "prompts" / "prompts-agent.md"
    )
    if not path.exists():
        return (
            "You generate 3–5 build prompts (markdown) from business logic and PRD. "
            "Use list_documents_tool to get project docs, then create_document_tool with type='prompts'. "
            "Project: {projectId?}. User: {userId?}. Business logic: {businessLogic?}. PRD: {prdContent?}."
        )
    text = path.read_text(encoding="utf-8")
    for k in ("projectId", "userId", "businessLogic", "prdContent"):
        text = text.replace("{" + k + "}", "{" + k + "?}")
    return text


prompts_agent = LlmAgent(
    name="prompts_agent",
    model=config.get_agent_model(),
    description="Generates 3–5 build prompts from business logic and PRD; saves as markdown.",
    instruction=_load_instruction(),
    tools=[
        create_document_tool,
        get_document_tool,
        get_project_tool,
        list_documents_tool,
    ],
    sub_agents=[],
)
