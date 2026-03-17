"""
Kingly Connect – Supabase CRUD and vector search as ADK FunctionTools.
Uses SUPABASE_SERVICE_ROLE_KEY for server-side access.
"""
import io
import json
import logging
import tempfile
import zipfile
from typing import Any
from uuid import UUID

from google.adk.tools import FunctionTool

from .. import config

logger = logging.getLogger(__name__)

# Lazy Supabase client
_client = None


def _get_client():
    global _client
    if _client is None:
        from supabase import create_client
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY)
    return _client


def _embedding_for_text(text: str) -> list[float]:
    """Generate embedding vector for text using Gemini."""
    if not text or not text.strip():
        return [0.0] * 768
    try:
        import google.generativeai as genai
        genai.configure(api_key=config.GOOGLE_API_KEY)
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text.strip(),
            task_type="retrieval_document",
        )
        return result["embedding"]
    except Exception as e:
        logger.warning("Embedding generation failed: %s", e)
        return [0.0] * 768


# ---------- Project CRUD ----------

def create_project(user_id: str, name: str, description: str = "") -> dict[str, Any]:
    """Create a new project for the user. Returns the created project with id."""
    try:
        sb = _get_client()
        r = sb.table("projects").insert({
            "user_id": user_id,
            "name": name,
            "description": description or "",
        }).execute()
        data = r.data
        if data and len(data) > 0:
            return {"status": "ok", "project": data[0]}
        return {"status": "error", "message": "Insert returned no data"}
    except Exception as e:
        logger.exception("create_project_tool failed: %s", e)
        return {"status": "error", "message": str(e)}


def get_project(project_id: str) -> dict[str, Any]:
    """Get a project by id."""
    try:
        sb = _get_client()
        r = sb.table("projects").select("*").eq("id", project_id).execute()
        data = r.data
        if data and len(data) > 0:
            return {"status": "ok", "project": data[0]}
        return {"status": "not_found"}
    except Exception as e:
        logger.exception("get_project_tool failed: %s", e)
        return {"status": "error", "message": str(e)}


def list_projects(user_id: str) -> dict[str, Any]:
    """List all projects for the user."""
    try:
        sb = _get_client()
        r = sb.table("projects").select("*").eq("user_id", user_id).order("updated_at", desc=True).execute()
        return {"status": "ok", "projects": r.data or []}
    except Exception as e:
        logger.exception("list_projects_tool failed: %s", e)
        return {"status": "error", "message": str(e)}


def update_project(project_id: str, name: str | None = None, description: str | None = None) -> dict[str, Any]:
    """Update a project's name and/or description."""
    try:
        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if not payload:
            return {"status": "ok", "message": "Nothing to update"}
        sb = _get_client()
        r = sb.table("projects").update(payload).eq("id", project_id).execute()
        data = r.data
        if data and len(data) > 0:
            return {"status": "ok", "project": data[0]}
        return {"status": "ok", "message": "Updated"}
    except Exception as e:
        logger.exception("update_project_tool failed: %s", e)
        return {"status": "error", "message": str(e)}


def delete_project(project_id: str) -> dict[str, Any]:
    """Delete a project and all its documents and embeddings."""
    try:
        sb = _get_client()
        sb.table("projects").delete().eq("id", project_id).execute()
        return {"status": "ok"}
    except Exception as e:
        logger.exception("delete_project_tool failed: %s", e)
        return {"status": "error", "message": str(e)}


# ---------- Document CRUD ----------

def create_document(project_id: str, type: str, title: str, content: str = "") -> dict[str, Any]:
    """Create a document (business_logic, prd, prompts, or upload). Returns the created document with id."""
    try:
        if type not in (
            "app_description",
            "business_logic",
            "prd",
            "prompts",
            "upload",
            "tech_stack",
            "cursor_rules",
            "cursor_master_prompt",
            "cursor_execution_plan",
        ):
            return {"status": "error", "message": "Invalid type"}
        sb = _get_client()
        r = sb.table("documents").insert({
            "project_id": project_id,
            "type": type,
            "title": title,
            "content": content or "",
        }).execute()
        data = r.data
        if data and len(data) > 0:
            return {"status": "ok", "document": data[0]}
        return {"status": "error", "message": "Insert returned no data"}
    except Exception as e:
        logger.exception("create_document_tool failed: %s", e)
        return {"status": "error", "message": str(e)}


def get_document(document_id: str) -> dict[str, Any]:
    """Get a document by id."""
    try:
        sb = _get_client()
        r = sb.table("documents").select("*").eq("id", document_id).execute()
        data = r.data
        if data and len(data) > 0:
            return {"status": "ok", "document": data[0]}
        return {"status": "not_found"}
    except Exception as e:
        logger.exception("get_document_tool failed: %s", e)
        return {"status": "error", "message": str(e)}


def list_documents(project_id: str) -> dict[str, Any]:
    """List all documents for a project."""
    try:
        sb = _get_client()
        r = sb.table("documents").select("*").eq("project_id", project_id).order("created_at", desc=True).execute()
        return {"status": "ok", "documents": r.data or []}
    except Exception as e:
        logger.exception("list_documents_tool failed: %s", e)
        return {"status": "error", "message": str(e)}


def update_document(document_id: str, title: str | None = None, content: str | None = None) -> dict[str, Any]:
    """Update a document's title and/or content."""
    try:
        payload = {}
        if title is not None:
            payload["title"] = title
        if content is not None:
            payload["content"] = content
        if not payload:
            return {"status": "ok", "message": "Nothing to update"}
        sb = _get_client()
        r = sb.table("documents").update(payload).eq("id", document_id).execute()
        data = r.data
        if data and len(data) > 0:
            return {"status": "ok", "document": data[0]}
        return {"status": "ok", "message": "Updated"}
    except Exception as e:
        logger.exception("update_document_tool failed: %s", e)
        return {"status": "error", "message": str(e)}


# ---------- Vector search (pgvector) ----------

def vector_search(project_id: str, query: str, limit: int = 5) -> dict[str, Any]:
    """Search project documents by semantic similarity. Returns relevant chunks."""
    try:
        embedding = _embedding_for_text(query)
        sb = _get_client()
        r = sb.rpc("match_document_embeddings", {
            "query_embedding": embedding,
            "match_count": limit,
            "filter_project_id": project_id,
        }).execute()
        rows = r.data or []
        return {"status": "ok", "chunks": [{"content": row.get("content"), "similarity": row.get("similarity")} for row in rows]}
    except Exception as e:
        logger.exception("vector_search_tool failed: %s", e)
        return {"status": "error", "message": str(e), "chunks": []}


# ---------- Embedding upsert ----------

def upsert_embedding(document_id: str, chunk_index: int, content: str, embedding: list[float] | None = None) -> dict[str, Any]:
    """Insert or update one chunk embedding. If embedding is None, generate from content."""
    try:
        if embedding is None:
            embedding = _embedding_for_text(content)
        if len(embedding) != 768:
            return {"status": "error", "message": "Embedding must be 768 dimensions"}
        sb = _get_client()
        # Upsert: delete existing chunk_index for this document then insert
        sb.table("document_embeddings").delete().eq("document_id", document_id).eq("chunk_index", chunk_index).execute()
        sb.table("document_embeddings").insert({
            "document_id": document_id,
            "chunk_index": chunk_index,
            "content": content,
            "embedding": embedding,
            "metadata": {},
        }).execute()
        return {"status": "ok"}
    except Exception as e:
        logger.exception("upsert_embedding_tool failed: %s", e)
        return {"status": "error", "message": str(e)}


# ---------- Zip artifact ----------

def create_zip_artifact(
    project_id: str,
    business_logic_content: str,
    prd_content: str,
    prompts_content: str,
    file_names: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a zip with business logic, PRD, and prompts markdown files. Returns base64-encoded zip and suggested filename."""
    names = file_names or {}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(names.get("business_logic", "business-logic.md"), business_logic_content or "")
        zf.writestr(names.get("prd", "prd.md"), prd_content or "")
        zf.writestr(names.get("prompts", "build-prompts.md"), prompts_content or "")
    buf.seek(0)
    import base64
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return {
        "status": "ok",
        "zip_base64": b64,
        "filename": "kingly-artifacts.zip",
    }


# ---------- ADK FunctionTool wrappers ----------

create_project_tool = FunctionTool(create_project)
get_project_tool = FunctionTool(get_project)
list_projects_tool = FunctionTool(list_projects)
update_project_tool = FunctionTool(update_project)
delete_project_tool = FunctionTool(delete_project)
create_document_tool = FunctionTool(create_document)
get_document_tool = FunctionTool(get_document)
list_documents_tool = FunctionTool(list_documents)
update_document_tool = FunctionTool(update_document)
vector_search_tool = FunctionTool(vector_search)
upsert_embedding_tool = FunctionTool(upsert_embedding)
create_zip_artifact_tool = FunctionTool(create_zip_artifact)
