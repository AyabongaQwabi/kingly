import { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowLeft, Download, FileText, LogOut, Loader2 } from "lucide-react";
import { supabase } from "../lib/supabase";
import { documents, projects, type Document } from "../lib/api";

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

export default function DocumentView() {
  const { projectId, documentId } = useParams<{ projectId: string; documentId: string }>();
  const navigate = useNavigate();
  const [doc, setDoc] = useState<Document | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!documentId) return;
    documents
      .get(documentId)
      .then((d) => {
        setDoc(d);
        return projects.get(d.project_id);
      })
      .then(() => undefined)
      .catch(() => navigate("/dashboard", { replace: true }))
      .finally(() => setLoading(false));
  }, [documentId, navigate]);

  async function handleSignOut() {
    await supabase.auth.signOut();
    navigate("/login", { replace: true });
  }

  if (loading || !doc) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex justify-between items-center">
        <div className="flex items-center gap-4 min-w-0">
          <Link
            to={projectId ? `/projects/${projectId}` : "/dashboard"}
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 shrink-0"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Link>
          <h1 className="text-lg font-semibold truncate flex items-center gap-2 min-w-0">
            <FileText className="h-5 w-5 text-slate-500 shrink-0" />
            {doc.title}
          </h1>
          <span className="text-xs text-gray-500 shrink-0">({doc.type})</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={() => downloadDocumentAsMarkdown(doc)}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
            title="Download as .md"
          >
            <Download className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={handleSignOut}
            className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </header>
      <main className="max-w-3xl mx-auto px-4 py-8">
        <article className="prose prose-gray max-w-none card p-6">
          {doc.content ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{doc.content}</ReactMarkdown>
          ) : (
            <p className="text-gray-500">No content.</p>
          )}
        </article>
      </main>
    </div>
  );
}
