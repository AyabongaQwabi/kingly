import { supabase } from "./supabase";

const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "") || "";

async function getAuthHeaders(): Promise<HeadersInit> {
  const { data: { session } } = await supabase.auth.getSession();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }
  return headers;
}

export async function api<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const headers = await getAuthHeaders();
  const res = await fetch(url, {
    ...options,
    headers: { ...headers, ...(options.headers as Record<string, string>) },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail?: string }).detail || res.statusText);
  }
  if (res.headers.get("content-type")?.includes("application/json")) {
    return res.json() as Promise<T>;
  }
  return res.text() as Promise<T>;
}

export async function apiUpload(
  path: string,
  file: File
): Promise<{ document: { id: string; title: string; type: string }; extracted_length: number }> {
  const { data: { session } } = await supabase.auth.getSession();
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(url, {
    method: "POST",
    headers: session?.access_token
      ? { Authorization: `Bearer ${session.access_token}` }
      : {},
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail?: string }).detail || res.statusText);
  }
  return res.json();
}

export type Project = {
  id: string;
  user_id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
};

export type Document = {
  id: string;
  project_id: string;
  type: string;
  title: string;
  content: string | null;
  created_at: string;
  updated_at: string;
};

/** Call after signup to auto-confirm the new user's email so they can use the app without clicking a verification link. */
export async function confirmEmail(): Promise<void> {
  await api("/auth/confirm-email", { method: "POST" });
}

export const projects = {
  list: () => api<{ projects: Project[] }>("/projects").then((r) => r.projects),
  create: (name: string, description: string) =>
    api<Project>("/projects", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    }),
  get: (id: string) => api<Project>(`/projects/${id}`),
  update: (id: string, data: { name?: string; description?: string }) =>
    api<Project>(`/projects/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    api<{ status: string }>(`/projects/${id}`, { method: "DELETE" }),
};

export const documents = {
  list: (projectId: string) =>
    api<{ documents: Document[] }>(`/projects/${projectId}/documents`).then(
      (r) => r.documents
    ),
  get: (id: string) => api<Document>(`/documents/${id}`),
  create: (projectId: string, type: string, title: string, content: string) =>
    api<Document>(`/projects/${projectId}/documents`, {
      method: "POST",
      body: JSON.stringify({ type, title, content }),
    }),
  updateWithPrompt: (documentId: string, prompt: string) =>
    api<Document>(`/documents/${documentId}/update`, {
      method: "POST",
      body: JSON.stringify({ prompt }),
    }),
};

export const runAgent = (
  projectId: string,
  agent: "business_logic" | "prd" | "prompts" | "zip",
  appDescription: string = ""
) =>
  api<{ reply: string; agent: string }>(`/projects/${projectId}/run`, {
    method: "POST",
    body: JSON.stringify({ agent, input: { app_description: appDescription } }),
  });

export const refineDescription = (projectId: string, draft: string) =>
  api<{ refined: string; document: Document }>(`/projects/${projectId}/refine-description`, {
    method: "POST",
    body: JSON.stringify({ draft }),
  });

export const uploadFile = (projectId: string, file: File) =>
  apiUpload(`/projects/${projectId}/upload`, file);

export async function downloadZip(projectId: string): Promise<void> {
  const { data: { session } } = await supabase.auth.getSession();
  const base = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "") || "";
  const url = `${base}/projects/${projectId}/artifacts/zip`;
  const res = await fetch(url, {
    headers: session?.access_token
      ? { Authorization: `Bearer ${session.access_token}` }
      : {},
  });
  if (!res.ok) throw new Error("Download failed");
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "kingly-artifacts.zip";
  a.click();
  URL.revokeObjectURL(a.href);
}
