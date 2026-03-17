"""Zip agent: generates business logic, PRD, and build prompts then bundles them into a zip."""
from pathlib import Path

from google.adk.agents import LlmAgent

from ... import config
from ...tools import (
    create_document_tool,
    create_zip_artifact_tool,
    get_document_tool,
    get_project_tool,
    list_documents_tool,
)


def _load_instruction() -> str:
    path = getattr(config, "ZIP_AGENT_PROMPT_PATH", None) or (
        config.REPO_ROOT / "docs" / "prompts" / "zip-agent.md"
    )
    if not path.exists():
        return (
            "You generate business logic, PRD, and build prompts for the project, then call create_zip_artifact_tool "
            "with the markdown contents. Project: {projectId?}. User: {userId?}. App description: {appDescription?}."
        )
    text = path.read_text(encoding="utf-8")
    for k in ("projectId", "userId", "appDescription"):
        text = text.replace("{" + k + "}", "{" + k + "?}")
    return text


zip_agent = LlmAgent(
    name="zip_agent",
    model=config.get_agent_model(),
    description="Generates business logic, PRD, and build prompts then bundles them into a zip for download.",
    instruction=_load_instruction(),
    tools=[
        create_document_tool,
        create_zip_artifact_tool,
        get_document_tool,
        get_project_tool,
        list_documents_tool,
    ],
    sub_agents=[],
)
