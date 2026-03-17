"""Tech stack agent: decides stack and generates Cursor rules."""
from google.adk.agents import LlmAgent

from ... import config
from ...tools import (
    create_document_tool,
    get_document_tool,
    list_documents_tool,
)


def _load_instruction() -> str:
    path = getattr(config, "TECH_STACK_AGENT_PROMPT_PATH", None) or (
        config.REPO_ROOT / "docs" / "prompts" / "tech-stack-agent.md"
    )
    if not path.exists():
        return (
            "You decide a tech stack and generate Cursor rules. "
            "Use list_documents_tool/get_document_tool to fetch PRD and business logic if missing. "
            "Then create two documents: type='tech_stack' and type='cursor_rules'."
        )
    text = path.read_text(encoding="utf-8")
    for k in ("projectId", "userId", "prdContent", "businessLogic"):
        text = text.replace("{" + k + "}", "{" + k + "?}")
    return text


tech_stack_agent = LlmAgent(
    name="tech_stack_agent",
    model=config.get_agent_model(),
    description="Decides the tech stack and generates a Cursor rules file; saves both as markdown documents.",
    instruction=_load_instruction(),
    tools=[
        create_document_tool,
        get_document_tool,
        list_documents_tool,
    ],
    sub_agents=[],
)

