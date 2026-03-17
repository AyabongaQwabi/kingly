"""Description refiner agent: improves a draft app/product description."""
from google.adk.agents import LlmAgent

from ... import config


def _load_instruction() -> str:
    path = getattr(config, "DESCRIPTION_REFINER_AGENT_PROMPT_PATH", None) or (
        config.REPO_ROOT / "docs" / "prompts" / "description-refiner-agent.md"
    )
    if not path.exists():
        return (
            "You improve a draft app/product description into a clear markdown document. "
            "Input: {draftDescription?}. Output markdown only."
        )
    text = path.read_text(encoding="utf-8")
    text = text.replace("{draftDescription}", "{draftDescription?}")
    return text


description_refiner_agent = LlmAgent(
    name="description_refiner_agent",
    model=config.get_agent_model(),
    description="Improves a draft app/product description into a clear markdown app description.",
    instruction=_load_instruction(),
    tools=[],
    sub_agents=[],
)

