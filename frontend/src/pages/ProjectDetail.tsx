import { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import {
  FileText,
  FolderOpen,
  Download,
  Pencil,
  Loader2,
  ArrowLeft,
  LogOut,
  FileArchive,
  Sparkles,
} from "lucide-react";
import { supabase } from "../lib/supabase";
import {
  projects,
  documents,
  runAgent,
  refineDescription,
  generateCursorPackage,
  downloadZip,
  type Project,
  type Document,
} from "../lib/api";

function downloadDocumentAsMarkdown(doc: Document) {
  const content = doc.content || "";
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${(doc.title || "document").replace(/[^a-z0-9.-]+/gi, "-")}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState<string | null>(null);
  const [runReply, setRunReply] = useState("");
  const [appDescription, setAppDescription] = useState("");
  const [savingDescription, setSavingDescription] = useState(false);
  const [refiningDescription, setRefiningDescription] = useState(false);
  const [generatingCursorPackage, setGeneratingCursorPackage] = useState(false);
  const [editDoc, setEditDoc] = useState<Document | null>(null);
  const [editPrompt, setEditPrompt] = useState("");
  const [updatingDoc, setUpdatingDoc] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    projects
      .get(projectId)
      .then(setProject)
      .catch(() => navigate("/dashboard", { replace: true }))
      .finally(() => setLoading(false));
  }, [projectId, navigate]);

  useEffect(() => {
    if (!projectId) return;
    documents.list(projectId).then(setDocs).catch(() => setDocs([]));
  }, [projectId]);

  const appDescriptionDoc = docs.find((d) => d.type === "app_description");
  useEffect(() => {
    if (appDescriptionDoc?.content && appDescription === "") {
      setAppDescription(appDescriptionDoc.content);
    }
  }, [appDescriptionDoc?.id]); // eslint-disable-line react-hooks/exhaustive-deps -- sync textarea from doc once when doc loads

  const hasAppDescriptionDoc = docs.some((d) => d.type === "app_description");
  const hasPrd = docs.some((d) => d.type === "prd");
  const hasBusinessLogic = docs.some((d) => d.type === "business_logic");
  const hasPrompts = docs.some((d) => d.type === "prompts");

  const canSaveDescription = appDescription.trim().length > 0 && !savingDescription;
  const canRefineDescription = appDescription.trim().length > 0 && !refiningDescription && !running && !savingDescription;
  const enablePrd = hasAppDescriptionDoc && !running;
  const enableBusinessLogic = hasAppDescriptionDoc && hasPrd && !running;
  const enablePrompts = hasBusinessLogic && !running;
  const enableZip = hasPrompts && !running;
  const enableCursorPackage = hasPrd && hasBusinessLogic && !running && !generatingCursorPackage;

  async function handleGenerateCursorPackage() {
    if (!projectId) return;
    setGeneratingCursorPackage(true);
    setRunReply("");
    try {
      const res = await generateCursorPackage(projectId);
      setDocs(res.documents || []);
      setRunReply("Cursor package generated. Download the zip to get .cursor rules + master prompt + plan.");
    } catch (e) {
      setRunReply(e instanceof Error ? e.message : "Cursor package failed");
    } finally {
      setGeneratingCursorPackage(false);
    }
  }

  async function handleRefineDescription() {
    if (!projectId || !appDescription.trim()) return;
    setRefiningDescription(true);
    setRunReply("");
    try {
      const res = await refineDescription(projectId, appDescription.trim());
      setAppDescription(res.refined);
      // Backend saves by default as app_description; refresh docs so the rest of the UI unlocks.
      const list = await documents.list(projectId);
      setDocs(list);
      setRunReply("Description improved and saved.");
    } catch (e) {
      setRunReply(e instanceof Error ? e.message : "Refine failed");
    } finally {
      setRefiningDescription(false);
    }
  }

  async function handleSaveAppDescription() {
    if (!projectId || !appDescription.trim()) return;
    setSavingDescription(true);
    setRunReply("");
    try {
      await documents.create(
        projectId,
        "app_description",
        "App Description",
        appDescription.trim()
      );
      const list = await documents.list(projectId);
      setDocs(list);
      setRunReply("App description saved.");
    } catch (e) {
      setRunReply(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSavingDescription(false);
    }
  }

  async function handleRunAgent(agent: "business_logic" | "prd" | "prompts" | "zip") {
    if (!projectId) return;
    setRunning(agent);
    setRunReply("");
    try {
      const res = await runAgent(projectId, agent, appDescription);
      setRunReply(res.reply);
      const list = await documents.list(projectId);
      setDocs(list);
    } catch (e) {
      setRunReply(e instanceof Error ? e.message : "Request failed");
    } finally {
      setRunning(null);
    }
  }

  async function handleDownloadZip() {
    if (!projectId) return;
    try {
      await downloadZip(projectId);
    } catch {
      setRunReply("Download failed");
    }
  }

  async function handleUpdateDocument() {
    if (!editDoc || !editPrompt.trim()) return;
    setUpdatingDoc(true);
    try {
      await documents.updateWithPrompt(editDoc.id, editPrompt.trim());
      setEditDoc(null);
      setEditPrompt("");
      const list = await documents.list(projectId!);
      setDocs(list);
    } catch (e) {
      setRunReply(e instanceof Error ? e.message : "Update failed");
    } finally {
      setUpdatingDoc(false);
    }
  }

  async function handleSignOut() {
    await supabase.auth.signOut();
    navigate("/login", { replace: true });
  }

  if (loading || !project) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex justify-between items-center">
        <div className="flex items-center gap-4">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Link>
          <h1 className="text-lg font-semibold flex items-center gap-2">
            <FolderOpen className="h-5 w-5 text-slate-500" />
            {project.name}
          </h1>
        </div>
        <button
          type="button"
          onClick={handleSignOut}
          className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-6 lg:py-8">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Left panel: inputs/actions */}
          <section className="lg:col-span-1">
            <div className="bg-white rounded-xl border border-gray-200 p-4 lg:sticky lg:top-6">
              {project.description && (
                <p className="text-gray-600 mb-4">{project.description}</p>
              )}

              <div className="mb-5">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  App description (used for generation)
                </label>
                <textarea
                  value={appDescription}
                  onChange={(e) => setAppDescription(e.target.value)}
                  placeholder="e.g. A task app where users can create projects and add markdown documents"
                  className="w-full rounded-xl bg-gray-50 px-4 py-3 text-sm leading-6 shadow-sm focus:outline-none focus:ring-2 focus:ring-slate-200"
                  rows={10}
                />
                <div className="mt-2 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={handleRefineDescription}
                    disabled={!canRefineDescription}
                    className="btn-secondary inline-flex items-center gap-2 disabled:opacity-50 disabled:pointer-events-none"
                  >
                    {refiningDescription ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Sparkles className="h-4 w-4" />
                    )}
                    {refiningDescription ? "Improving..." : "Improve with AI"}
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveAppDescription}
                    disabled={!canSaveDescription}
                    className="btn-primary inline-flex items-center gap-2"
                  >
                    {savingDescription ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <FileText className="h-4 w-4" />
                    )}
                    {savingDescription ? "Saving..." : "Save as app description"}
                  </button>
                </div>
              </div>

              <div className="flex flex-wrap gap-2 mb-5">
                <button
                  type="button"
                  onClick={handleGenerateCursorPackage}
                  disabled={!enableCursorPackage}
                  className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-slate-800 disabled:opacity-50 disabled:pointer-events-none"
                >
                  {generatingCursorPackage ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  {generatingCursorPackage ? "Generating..." : "Generate Cursor Package"}
                </button>
                <button
                  type="button"
                  onClick={() => handleRunAgent("prd")}
                  disabled={!enablePrd}
                  className="btn-primary inline-flex items-center gap-2 disabled:opacity-50 disabled:pointer-events-none"
                >
                  {running === "prd" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  {running === "prd" ? "Generating..." : "Generate PRD"}
                </button>
                <button
                  type="button"
                  onClick={() => handleRunAgent("business_logic")}
                  disabled={!enableBusinessLogic}
                  className="btn-primary inline-flex items-center gap-2 disabled:opacity-50 disabled:pointer-events-none"
                >
                  {running === "business_logic" ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
                  {running === "business_logic" ? "Generating..." : "Generate business logic"}
                </button>
                <button
                  type="button"
                  onClick={() => handleRunAgent("prompts")}
                  disabled={!enablePrompts}
                  className="btn-primary inline-flex items-center gap-2 disabled:opacity-50 disabled:pointer-events-none"
                >
                  {running === "prompts" ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
                  {running === "prompts" ? "Generating..." : "Generate prompts"}
                </button>
                <button
                  type="button"
                  onClick={() => handleRunAgent("zip")}
                  disabled={!enableZip}
                  className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-green-700 disabled:opacity-50 disabled:pointer-events-none"
                >
                  {running === "zip" ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileArchive className="h-4 w-4" />}
                  {running === "zip" ? "Generating..." : "Generate all (zip)"}
                </button>
                <button
                  type="button"
                  onClick={handleDownloadZip}
                  className="inline-flex items-center gap-2 rounded-lg bg-gray-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-gray-700"
                >
                  <Download className="h-4 w-4" />
                  Download zip
                </button>
              </div>

              {runReply && (
                <div className="mb-5 p-4 bg-white rounded-lg border border-gray-200 text-sm text-gray-700 flex items-start gap-2">
                  <FileText className="h-4 w-4 mt-0.5 shrink-0" />
                  {runReply}
                </div>
              )}

              {/* Upload section hidden for now */}
            </div>
          </section>

          {/* Right panel: documents */}
          <section className="lg:col-span-2">
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <h3 className="text-lg font-medium text-gray-900 mb-3 flex items-center gap-2">
                <FolderOpen className="h-5 w-5 text-slate-500" />
                Documents
              </h3>
              {docs.length === 0 ? (
                <p className="text-gray-500">No documents yet. Save an app description or generate above.</p>
              ) : (
                <ul className="space-y-2">
                  {docs.map((d) => (
                    <li
                      key={d.id}
                      className="flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-200 hover:border-gray-300"
                    >
                      <Link
                        to={`/projects/${projectId}/documents/${d.id}`}
                        className="flex-1 min-w-0 flex items-center gap-2"
                      >
                        <FileText className="h-4 w-4 text-slate-500 shrink-0" />
                        <span className="font-medium text-gray-900 truncate">{d.title}</span>
                        <span className="text-xs text-gray-500 shrink-0">({d.type})</span>
                      </Link>
                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          type="button"
                          onClick={() => downloadDocumentAsMarkdown(d)}
                          className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                          title="Download"
                        >
                          <Download className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setEditDoc(d);
                            setEditPrompt("");
                          }}
                          className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                          title="Edit with prompt"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        </div>
      </main>

      {editDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6">
            <h3 className="font-semibold text-gray-900 mb-2">Edit document with a prompt</h3>
            <p className="text-sm text-gray-500 mb-3">
              Describe how you want to change &quot;{editDoc.title}&quot;. The AI will apply your changes.
            </p>
            <textarea
              value={editPrompt}
              onChange={(e) => setEditPrompt(e.target.value)}
              placeholder="e.g. Add a section on error handling and add two more user stories"
              className="input mb-4"
              rows={4}
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setEditDoc(null);
                  setEditPrompt("");
                }}
                className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleUpdateDocument}
                disabled={!editPrompt.trim() || updatingDoc}
                className="btn-primary inline-flex items-center gap-2"
              >
                {updatingDoc ? <Loader2 className="h-4 w-4 animate-spin" /> : <Pencil className="h-4 w-4" />}
                {updatingDoc ? "Updating..." : "Update"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
