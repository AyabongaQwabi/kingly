"""Cursor master prompt agent: generates MasterPrompt.md content and saves it."""
from google.adk.agents import LlmAgent

from ... import config
from ...tools import create_document_tool, get_document_tool, list_documents_tool


def _load_instruction() -> str:
    path = getattr(config, "CURSOR_MASTER_PROMPT_AGENT_PROMPT_PATH", None) or (
        config.REPO_ROOT / "docs" / "prompts" / "cursor-master-prompt-agent.md"
    )
    if not path.exists():
        return (
            "You create a master Cursor orchestrator prompt and save it as "
            "type='cursor_master_prompt'. Use tools to fetch PRD, business logic, tech stack, cursor rules, and prompts."
        )
    text = path.read_text(encoding="utf-8")
    for k in ("projectId", "userId", "prdContent", "businessLogic"):
        text = text.replace("{" + k + "}", "{" + k + "?}")
    return text


cursor_master_prompt_agent = LlmAgent(
    name="cursor_master_prompt_agent",
    model=config.get_agent_model(),
    description="Generates a single master Cursor orchestrator prompt; saves as markdown document.",
    instruction=_load_instruction(),
    tools=[list_documents_tool, get_document_tool, create_document_tool],
    sub_agents=[],
)

