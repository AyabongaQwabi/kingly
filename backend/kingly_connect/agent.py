"""
Kingly Connect – Root agent. Routes to business_logic, prd, prompts, or zip agent.
"""
from pathlib import Path

from google.adk.agents import Agent

from . import config
from .sub_agents import (
    business_logic_agent,
    description_refiner_agent,
    prd_agent,
    prompts_agent,
    zip_agent,
)


def _load_root_instruction() -> str:
    path = config.REPO_ROOT / "docs" / "prompts" / "root-orchestrator.md"
    if not path.exists():
        return (
            "You route to business_logic_agent, prd_agent, prompts_agent, or zip_agent based on the user request. "
            "State: projectId={projectId?}, userId={userId?}, appDescription={appDescription?}."
        )
    text = path.read_text(encoding="utf-8")
    for k in ("projectId", "userId", "appDescription", "ragContext"):
        text = text.replace("{" + k + "}", "{" + k + "?}")
    return text


def get_root_agent() -> Agent:
    """Build the root orchestrator that delegates to the four agents."""
    return Agent(
        name="kingly_orchestrator",
        model=config.get_agent_model(),
        description="Routes to business_logic, prd, prompts, or zip agent based on request.",
        instruction=_load_root_instruction(),
        tools=[],
        sub_agents=[description_refiner_agent, business_logic_agent, prd_agent, prompts_agent, zip_agent],
    )
