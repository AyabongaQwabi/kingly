"""Cursor execution plan agent: generates ExecutionPlan.md content and saves it."""
from google.adk.agents import LlmAgent

from ... import config
from ...tools import create_document_tool, get_document_tool, list_documents_tool


def _load_instruction() -> str:
    path = getattr(config, "CURSOR_EXECUTION_PLAN_AGENT_PROMPT_PATH", None) or (
        config.REPO_ROOT / "docs" / "prompts" / "cursor-execution-plan-agent.md"
    )
    if not path.exists():
        return (
            "You create a Cursor execution plan and save it as type='cursor_execution_plan'. "
            "Use tools to fetch stack, rules, master prompt, PRD, and business logic."
        )
    text = path.read_text(encoding="utf-8")
    for k in ("projectId", "userId"):
        text = text.replace("{" + k + "}", "{" + k + "?}")
    return text


cursor_execution_plan_agent = LlmAgent(
    name="cursor_execution_plan_agent",
    model=config.get_agent_model(),
    description="Generates a Cursor execution plan runbook; saves as markdown document.",
    instruction=_load_instruction(),
    tools=[list_documents_tool, get_document_tool, create_document_tool],
    sub_agents=[],
)

