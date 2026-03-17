import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FolderPlus, FolderOpen, LogOut, Loader2 } from "lucide-react";
import { supabase } from "../lib/supabase";
import { projects, type Project } from "../lib/api";

export default function Dashboard() {
  const [list, setList] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    projects
      .list()
      .then(setList)
      .catch(() => setList([]))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    try {
      const p = await projects.create(name.trim(), description.trim());
      navigate(`/projects/${p.id}`);
    } catch {
      setCreating(false);
    }
    setCreating(false);
  }

  async function handleSignOut() {
    await supabase.auth.signOut();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex justify-between items-center">
        <Link to="/" className="text-lg font-semibold text-slate-900 hover:text-slate-700">
          Kingly
        </Link>
        <button
          type="button"
          onClick={handleSignOut}
          className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </header>
      <main className="max-w-2xl mx-auto px-4 py-8">
        <h2 className="text-xl font-medium text-gray-900 mb-4 flex items-center gap-2">
          <FolderOpen className="h-5 w-5 text-slate-500" />
          Projects
        </h2>

        <form onSubmit={handleCreate} className="mb-8 card p-4 space-y-3">
          <input
            type="text"
            placeholder="Project name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input"
            required
          />
          <textarea
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="input"
            rows={2}
          />
          <button
            type="submit"
            disabled={creating}
            className="btn-primary inline-flex items-center gap-2"
          >
            {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <FolderPlus className="h-4 w-4" />}
            {creating ? "Creating..." : "New project"}
          </button>
        </form>

        {loading ? (
          <p className="text-gray-500 flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading projects...
          </p>
        ) : list.length === 0 ? (
          <p className="text-gray-500">No projects yet. Create one above.</p>
        ) : (
          <ul className="space-y-2">
            {list.map((p) => (
              <li key={p.id}>
                <Link
                  to={`/projects/${p.id}`}
                  className="flex items-center gap-3 block p-4 card hover:border-gray-300"
                >
                  <FolderOpen className="h-5 w-5 text-slate-500 shrink-0" />
                  <div className="min-w-0">
                    <span className="font-medium text-gray-900">{p.name}</span>
                    {p.description && (
                      <p className="text-sm text-gray-500 mt-1">{p.description}</p>
                    )}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
