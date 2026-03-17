"""
Kingly Connect – config (env-based). Used by agents and tools.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

KC_DIR = Path(__file__).resolve().parent
load_dotenv(KC_DIR / ".env")
load_dotenv(KC_DIR.parent / ".env")
load_dotenv(KC_DIR.parent.parent / ".env")

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("MODEL", "gemini-2.5-flash")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "").strip()

YOCO_SECRET_KEY = os.environ.get("YOCO_SECRET_KEY", "").strip()

REPO_ROOT = Path(__file__).resolve().parent

# Prompt paths for agents
BUSINESS_LOGIC_AGENT_PROMPT_PATH = REPO_ROOT / "docs" / "prompts" / "business-logic-agent.md"
PRD_AGENT_PROMPT_PATH = REPO_ROOT / "docs" / "prompts" / "prd-agent.md"
PROMPTS_AGENT_PROMPT_PATH = REPO_ROOT / "docs" / "prompts" / "prompts-agent.md"
ZIP_AGENT_PROMPT_PATH = REPO_ROOT / "docs" / "prompts" / "zip-agent.md"
DESCRIPTION_REFINER_AGENT_PROMPT_PATH = REPO_ROOT / "docs" / "prompts" / "description-refiner-agent.md"
TECH_STACK_AGENT_PROMPT_PATH = REPO_ROOT / "docs" / "prompts" / "tech-stack-agent.md"
CURSOR_MASTER_PROMPT_AGENT_PROMPT_PATH = REPO_ROOT / "docs" / "prompts" / "cursor-master-prompt-agent.md"
CURSOR_EXECUTION_PLAN_AGENT_PROMPT_PATH = REPO_ROOT / "docs" / "prompts" / "cursor-execution-plan-agent.md"


def get_agent_model() -> str:
    return GEMINI_MODEL
