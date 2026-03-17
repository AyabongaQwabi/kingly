"""
Kingly – FastAPI backend. Supabase auth, projects/documents CRUD, agent run, file upload, zip download.
"""
import io
import json
import logging
import time
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from kingly_connect import config as kc_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Import after env is loaded
try:
    from backend.agent_runner import init_runner, run_agent_async
    from backend.kingly_connect.tools.supabase_tools import (
        create_project,
        create_document,
        delete_project,
        get_document,
        get_project,
        list_documents,
        list_projects,
        update_document,
        update_project,
        _get_client,
    )
except ImportError:
    from agent_runner import init_runner, run_agent_async
    from kingly_connect.tools.supabase_tools import (
        create_project,
        create_document,
        delete_project,
        get_document,
        get_project,
        list_documents,
        list_projects,
        update_document,
        update_project,
        _get_client,
    )


# ---------- Auth ----------

security = HTTPBearer(auto_error=False)

# Cache for JWKS (new Supabase JWT signing keys). Key: url, value: (payload, expiry_ts)
_jwks_cache: dict[str, tuple[dict, float]] = {}
_JWKS_CACHE_TTL = 300  # 5 minutes


def _fetch_jwks() -> dict:
    url = (kc_config.SUPABASE_URL or "").rstrip("/") + "/auth/v1/.well-known/jwks.json"
    now = time.time()
    if url in _jwks_cache:
        payload, expiry = _jwks_cache[url]
        if now < expiry:
            return payload
    try:
        import httpx
        r = httpx.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        _jwks_cache[url] = (data, now + _JWKS_CACHE_TTL)
        return data
    except Exception as e:
        logger.warning("JWKS fetch failed: %s", e)
        return {"keys": []}


def _verify_jwt_with_jwks(token: str) -> dict | None:
    """Verify JWT using Supabase JWKS (asymmetric keys). Returns payload or None."""
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        alg = header.get("alg", "RS256")
        if not kid:
            return None
        jwks = _fetch_jwks()
        keys = jwks.get("keys") or []
        for key_dict in keys:
            if key_dict.get("kid") != kid:
                continue
            try:
                from jwcrypto import jwk
                k = jwk.JWK.from_json(json.dumps(key_dict))
                pem = k.export_to_pem()
                if isinstance(pem, bytes):
                    pem = pem.decode("utf-8")
                decoded = jwt.decode(
                    token,
                    pem,
                    algorithms=[alg],
                    audience="authenticated",
                    options={"verify_aud": True, "verify_exp": True},
                )
                return decoded
            except Exception as e:
                logger.debug("JWKS key verify failed for kid %s: %s", kid, e)
                continue
        return None
    except Exception as e:
        logger.debug("JWKS verify failed: %s", e)
        return None


def get_current_user_id(
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str:
    if cred is None:
        raise HTTPException(status_code=401, detail="Bearer token required")
    token = cred.credentials
    # Reject obvious non-JWT (e.g. publishable key sent by mistake)
    if token.startswith("sb_publishable_") or token.startswith("sb_secret_"):
        raise HTTPException(status_code=401, detail="Use your session token, not the API key")
    payload = None
    # 1) Try JWKS (new Supabase asymmetric JWT signing keys)
    if kc_config.SUPABASE_URL:
        payload = _verify_jwt_with_jwks(token)
    # 2) Fall back to legacy JWT secret (HS256)
    if payload is None and kc_config.SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                kc_config.SUPABASE_JWT_SECRET,
                audience="authenticated",
                algorithms=["HS256"],
            )
        except Exception as e:
            logger.warning("JWT decode (legacy) failed: %s", e)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload["sub"]


# ---------- Request/Response models ----------

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class RunAgentInput(BaseModel):
    app_description: str = ""


class RunAgentRequest(BaseModel):
    agent: str = Field(..., pattern="^(business_logic|prd|prompts|zip|tech_stack)$")
    input: RunAgentInput = Field(default_factory=RunAgentInput)


class DocumentCreate(BaseModel):
    type: str = Field(
        ...,
        pattern="^(app_description|business_logic|prd|prompts|upload|tech_stack|cursor_rules|cursor_master_prompt|cursor_execution_plan)$",
    )
    title: str = Field(..., min_length=1)
    content: str = ""


class DocumentUpdatePrompt(BaseModel):
    prompt: str = Field(..., min_length=1)

class RefineDescriptionRequest(BaseModel):
    draft: str = Field(..., min_length=1)

class CursorPackageRequest(BaseModel):
    # For v1, allow an optional override as free text.
    stack_override: str = ""


# ---------- App ----------

@asynccontextmanager
async def lifespan(app):
    yield


app = FastAPI(title="Kingly API", description="Projects, documents, and AI agents", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- Auto-confirm new user email ----------

@app.post("/auth/confirm-email")
def api_confirm_email(user_id: Annotated[str, Depends(get_current_user_id)]):
    """Mark the current user's email as confirmed (call after signup so they can use the app without email verification)."""
    try:
        sb = _get_client()
        r = sb.auth.admin.update_user_by_id(user_id, {"email_confirm": True})
        return {"status": "ok", "message": "Email confirmed"}
    except Exception as e:
        logger.warning("confirm-email failed: %s", e)
        raise HTTPException(status_code=500, detail="Could not confirm email")


# ---------- Projects ----------

@app.get("/projects")
def api_list_projects(user_id: Annotated[str, Depends(get_current_user_id)]):
    r = list_projects(user_id)
    if r.get("status") != "ok":
        raise HTTPException(status_code=500, detail=r.get("message", "Failed to list projects"))
    return {"projects": r["projects"]}


@app.post("/projects")
def api_create_project(
    body: ProjectCreate,
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    r = create_project(user_id, body.name, body.description)
    if r.get("status") != "ok":
        raise HTTPException(status_code=500, detail=r.get("message", "Failed to create project"))
    return r["project"]


@app.get("/projects/{project_id}")
def api_get_project(
    project_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    r = get_project(project_id)
    if r.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Project not found")
    if r.get("status") != "ok":
        raise HTTPException(status_code=500, detail=r.get("message", "Error"))
    proj = r["project"]
    if proj.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@app.put("/projects/{project_id}")
def api_update_project(
  project_id: str,
  body: ProjectUpdate,
  user_id: Annotated[str, Depends(get_current_user_id)],
):
    r = get_project(project_id)
    if r.get("status") != "ok" or r["project"].get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    r = update_project(
        project_id,
        name=body.name,
        description=body.description,
    )
    if r.get("status") != "ok":
        raise HTTPException(status_code=500, detail=r.get("message", "Update failed"))
    return r.get("project") or r


@app.delete("/projects/{project_id}")
def api_delete_project(
    project_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    r = get_project(project_id)
    if r.get("status") != "ok" or r["project"].get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    delete_project(project_id)
    return {"status": "ok"}


# ---------- Documents ----------

@app.get("/projects/{project_id}/documents")
def api_list_documents(
    project_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    r = get_project(project_id)
    if r.get("status") != "ok" or r["project"].get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    r = list_documents(project_id)
    if r.get("status") != "ok":
        raise HTTPException(status_code=500, detail=r.get("message", "Failed to list documents"))
    return {"documents": r["documents"]}


@app.get("/documents/{document_id}")
def api_get_document(
    document_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    r = get_document(document_id)
    if r.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Document not found")
    if r.get("status") != "ok":
        raise HTTPException(status_code=500, detail=r.get("message", "Error"))
    doc = r["document"]
    # Ensure user owns the project
    proj_r = get_project(doc["project_id"])
    if proj_r.get("status") != "ok" or proj_r["project"].get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.post("/projects/{project_id}/documents")
def api_create_document(
    project_id: str,
    body: DocumentCreate,
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    r = get_project(project_id)
    if r.get("status") != "ok" or r["project"].get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    r = create_document(project_id, body.type, body.title, body.content)
    if r.get("status") != "ok":
        raise HTTPException(status_code=500, detail=r.get("message", "Failed to create document"))
    return r["document"]


def _update_document_content_with_prompt(current_content: str, prompt: str) -> str:
    """Use Gemini to produce updated markdown content from current content + user prompt."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=kc_config.GOOGLE_API_KEY)
        model = genai.GenerativeModel(kc_config.get_agent_model())
        response = model.generate_content(
            "You are editing a markdown document. The user wants you to apply the following change.\n\n"
            "**User's update instruction:**\n" + prompt + "\n\n"
            "**Current document content:**\n" + (current_content or "(empty)") + "\n\n"
            "Output ONLY the full updated markdown document content, with the user's changes applied. Do not include any explanation or preamble."
        )
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        logger.warning("Gemini update-document failed: %s", e)
    return current_content


@app.post("/documents/{document_id}/update")
def api_update_document_with_prompt(
    document_id: str,
    body: DocumentUpdatePrompt,
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    r = get_document(document_id)
    if r.get("status") != "ok":
        raise HTTPException(status_code=404, detail="Document not found")
    doc = r["document"]
    proj_r = get_project(doc["project_id"])
    if proj_r.get("status") != "ok" or proj_r["project"].get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Document not found")
    new_content = _update_document_content_with_prompt(doc.get("content") or "", body.prompt)
    update_r = update_document(document_id, content=new_content)
    if update_r.get("status") != "ok":
        raise HTTPException(status_code=500, detail=update_r.get("message", "Update failed"))
    return update_r.get("document") or get_document(document_id)["document"]


# ---------- Run agent ----------

@app.post("/projects/{project_id}/refine-description")
async def api_refine_description(
    project_id: str,
    body: RefineDescriptionRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    r = get_project(project_id)
    if r.get("status") != "ok" or r["project"].get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Project not found")

    draft = (body.draft or "").strip()
    # Only show "provide draft" style messages when input is actually inadequate.
    if len(draft) < 20:
        raise HTTPException(status_code=400, detail="Description is too short. Please add more detail.")

    reply = await run_agent_async(
        user_id=user_id,
        message=(
            "Run refine_description agent\n\n"
            "Draft description:\n"
            f"{draft}\n"
        ),
        project_id=project_id,
        draft_description=draft,
    )

    refined = (reply or "").strip()
    if not refined:
        raise HTTPException(status_code=500, detail="Refinement failed")

    # Save by default as the project's app_description document (create or update).
    existing = list_documents(project_id).get("documents") or []
    existing_app = next((d for d in existing if d.get("type") == "app_description"), None)
    if existing_app and existing_app.get("id"):
        saved = update_document(existing_app["id"], content=refined)
        if saved.get("status") != "ok":
            raise HTTPException(status_code=500, detail=saved.get("message", "Save failed"))
        doc = saved.get("document") or get_document(existing_app["id"]).get("document")
    else:
        created = create_document(project_id, "app_description", "App Description", refined)
        if created.get("status") != "ok":
            raise HTTPException(status_code=500, detail=created.get("message", "Save failed"))
        doc = created.get("document")

    return {"refined": refined, "document": doc}


@app.post("/projects/{project_id}/run")
async def api_run_agent(
    project_id: str,
    body: RunAgentRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    r = get_project(project_id)
    if r.get("status") != "ok" or r["project"].get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    app_description = (body.input and body.input.app_description) or ""
    message = f"Run {body.agent} agent."
    reply = await run_agent_async(
        user_id=user_id,
        message=message,
        project_id=project_id,
        app_description=app_description,
    )
    return {"reply": reply, "agent": body.agent}


@app.post("/projects/{project_id}/cursor-package")
async def api_cursor_package(
    project_id: str,
    body: CursorPackageRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    r = get_project(project_id)
    if r.get("status") != "ok" or r["project"].get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Project not found")

    docs_r = list_documents(project_id)
    if docs_r.get("status") != "ok":
        raise HTTPException(status_code=500, detail="Failed to list documents")
    docs = docs_r.get("documents") or []
    has_prd = any(d.get("type") == "prd" for d in docs)
    has_bl = any(d.get("type") == "business_logic" for d in docs)
    if not (has_prd and has_bl):
        raise HTTPException(status_code=400, detail="PRD and Business Logic are required first")

    # 1) Decide stack + generate cursor rules (agent saves docs)
    stack_msg = "Run tech_stack agent"
    if (body.stack_override or "").strip():
        stack_msg += "\n\nUser stack override:\n" + body.stack_override.strip()
    await run_agent_async(
        user_id=user_id,
        message=stack_msg,
        project_id=project_id,
    )

    # 2) Generate Cursor-optimized prompts doc (prompt 1..4 inside)
    await run_agent_async(
        user_id=user_id,
        message="Run prompts agent",
        project_id=project_id,
    )

    # 3) Generate and save MasterPrompt.md content
    await run_agent_async(
        user_id=user_id,
        message="Run cursor_master_prompt agent",
        project_id=project_id,
    )

    # 4) Generate and save ExecutionPlan.md content
    await run_agent_async(
        user_id=user_id,
        message="Run cursor_execution_plan agent",
        project_id=project_id,
    )

    # Return latest docs snapshot for the UI
    docs_r2 = list_documents(project_id)
    if docs_r2.get("status") != "ok":
        raise HTTPException(status_code=500, detail="Failed to list documents")
    return {"status": "ok", "documents": docs_r2.get("documents") or []}


# ---------- Upload (PDF/DOCX/MD) ----------

def _extract_text_from_file(content: bytes, filename: str) -> str:
    ext = (Path(filename).suffix or "").lower()
    if ext == ".pdf":
        try:
            import PyPDF2
            buf = io.BytesIO(content)
            reader = PyPDF2.PdfReader(buf)
            parts = []
            for page in reader.pages:
                parts.append(page.extract_text() or "")
            return "\n\n".join(parts)
        except Exception as e:
            logger.warning("PDF extract failed: %s", e)
            return ""
    if ext in (".docx", ".doc"):
        try:
            from docx import Document
            buf = io.BytesIO(content)
            doc = Document(buf)
            return "\n\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            logger.warning("DOCX extract failed: %s", e)
            return ""
    if ext in (".md", ".markdown", ""):
        return content.decode("utf-8", errors="replace")
    return content.decode("utf-8", errors="replace")


@app.post("/projects/{project_id}/upload")
async def api_upload(
    project_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    file: UploadFile = File(...),
):
    r = get_project(project_id)
    if r.get("status") != "ok" or r["project"].get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    content = await file.read()
    filename = file.filename or "upload"
    text = _extract_text_from_file(content, filename)
    # Store in Supabase Storage
    sb = _get_client()
    path = f"project_uploads/{user_id}/{project_id}/{filename}"
    try:
        sb.storage.from_("project-uploads").upload(path, content, {"content-type": file.content_type or "application/octet-stream"})
    except Exception as e:
        logger.warning("Storage upload failed (bucket may not exist): %s", e)
    # Create document with extracted text
    doc_r = create_document(project_id, "upload", filename, text)
    if doc_r.get("status") != "ok":
        raise HTTPException(status_code=500, detail=doc_r.get("message", "Failed to create document"))
    return {"document": doc_r["document"], "extracted_length": len(text)}


# ---------- Download zip ----------

@app.get("/projects/{project_id}/artifacts/zip")
def api_download_zip(
    project_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
):
    r = get_project(project_id)
    if r.get("status") != "ok" or r["project"].get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    docs_r = list_documents(project_id)
    if docs_r.get("status") != "ok":
        raise HTTPException(status_code=500, detail="Failed to list documents")
    documents = docs_r["documents"]
    by_type = {}
    for d in documents:
        t = d.get("type")
        if t in (
            "app_description",
            "business_logic",
            "prd",
            "prompts",
            "tech_stack",
            "cursor_rules",
            "cursor_master_prompt",
            "cursor_execution_plan",
        ):
            by_type[t] = d
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("app-description.md", (by_type.get("app_description") or {}).get("content") or "")
        zf.writestr("business-logic.md", (by_type.get("business_logic") or {}).get("content") or "")
        zf.writestr("prd.md", (by_type.get("prd") or {}).get("content") or "")
        zf.writestr("build-prompts.md", (by_type.get("prompts") or {}).get("content") or "")
        zf.writestr("tech-stack.md", (by_type.get("tech_stack") or {}).get("content") or "")
        zf.writestr(".cursor/rules/kingly.md", (by_type.get("cursor_rules") or {}).get("content") or "")
        zf.writestr("MasterPrompt.md", (by_type.get("cursor_master_prompt") or {}).get("content") or "")
        zf.writestr("ExecutionPlan.md", (by_type.get("cursor_execution_plan") or {}).get("content") or "")
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=kingly-artifacts.zip"},
    )
