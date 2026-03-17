"""
Kingly – Persistent ADK runner for the backend.
One Runner + InMemorySessionService; sessions keyed by user_id (Supabase).
"""
import json
import logging
import sys
from pathlib import Path
from typing import Any

_backend_root = Path(__file__).resolve().parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

from dotenv import load_dotenv
load_dotenv(_backend_root / ".env")
load_dotenv(_backend_root / "kingly_connect" / ".env")
load_dotenv(_backend_root.parent / ".env")

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from kingly_connect.agent import get_root_agent

logger = logging.getLogger(__name__)

APP_NAME = "kingly"
FALLBACK_REPLY = "Something went wrong. Please try again."

_runner: Runner | None = None
_session_service: InMemorySessionService | None = None
_created_sessions: set[str] = set()


def init_runner() -> None:
    """Load root agent and create Runner + SessionService once."""
    global _runner, _session_service
    if _runner is not None:
        return
    logger.info("Loading Kingly root agent and runner...")
    root_agent = get_root_agent()
    _session_service = InMemorySessionService()
    _runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=_session_service,
    )
    logger.info("Kingly agent and runner ready.")


async def _ensure_session(user_id: str, session_state: dict[str, Any] | None = None) -> None:
    """Create or reuse session for user_id with given state."""
    if _session_service is None:
        raise RuntimeError("Session service not initialized")
    session_id = f"user_{user_id}"
    if session_id in _created_sessions:
        return
    state = session_state or {}
    initial = {
        "userId": user_id,
        "projectId": state.get("projectId", ""),
        "appDescription": state.get("app_description", state.get("appDescription", "")),
        "draftDescription": state.get("draftDescription", ""),
        "ragContext": state.get("ragContext", ""),
    }
    await _session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
        state=initial,
    )
    _created_sessions.add(session_id)


def _update_session_state(user_id: str, session_id: str, state_updates: dict[str, Any]) -> None:
    """Merge state_updates into the session state."""
    if _session_service is None:
        return
    try:
        by_app = getattr(_session_service, "sessions", None)
        by_user = by_app.get(APP_NAME, {}).get(user_id, {}) if by_app else {}
        storage_session = by_user.get(session_id) if by_user else None
    except (AttributeError, TypeError):
        storage_session = None
    if storage_session is None:
        return
    state = getattr(storage_session, "state", None)
    if state is None:
        return
    for k, v in state_updates.items():
        state[k] = v


async def run_agent_async(
    user_id: str,
    message: str,
    project_id: str = "",
    app_description: str = "",
    draft_description: str = "",
    rag_context: str = "",
) -> str:
    """
    Run one user message through the runner with session state set for the project.
    Returns the reply text.
    """
    if _runner is None or _session_service is None:
        init_runner()
    session_id = f"user_{user_id}"
    await _ensure_session(user_id, {
        "projectId": project_id,
        "userId": user_id,
        "app_description": app_description,
        "appDescription": app_description,
        "draftDescription": draft_description,
        "ragContext": rag_context,
    })
    _update_session_state(user_id, session_id, {
        "projectId": project_id,
        "appDescription": app_description,
        "draftDescription": draft_description,
        "ragContext": rag_context,
    })
    content = types.Content(role="user", parts=[types.Part(text=message)])
    reply_text = ""
    accumulated = ""
    async for event in _runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    ):
        content_ev = getattr(event, "content", None)
        parts = getattr(content_ev, "parts", None) if content_ev else None
        if not parts:
            if getattr(event, "is_final_response", lambda: False)() and accumulated:
                reply_text = accumulated.strip()
            continue
        for part in parts:
            text = getattr(part, "text", None)
            if not text:
                continue
            text = text or ""
            if getattr(event, "partial", False):
                accumulated += text
            else:
                if getattr(event, "is_final_response", lambda: False)():
                    reply_text = (accumulated + text).strip()
                accumulated += text
        if getattr(event, "is_final_response", lambda: False)() and not reply_text and accumulated:
            reply_text = accumulated.strip()
    return reply_text.strip() or accumulated.strip() or FALLBACK_REPLY
