import { useEffect, useState } from "react";
import { Route, Routes, useNavigate } from "react-router-dom";
import { Session } from "@supabase/supabase-js";
import { supabase } from "./lib/supabase";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import ProjectDetail from "./pages/ProjectDetail";
import DocumentView from "./pages/DocumentView";

const isPublicPath = (path: string) =>
  path === "/" || path === "/login" || path === "/register";

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });
    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (loading) return;
    const path = window.location.pathname;
    const isAuthPage = path === "/login" || path === "/register";
    if (!session && !isPublicPath(path)) {
      navigate("/login", { replace: true });
    } else if (session && isAuthPage) {
      navigate("/dashboard", { replace: true });
    }
  }, [session, loading, navigate]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/projects/:projectId" element={<ProjectDetail />} />
      <Route path="/projects/:projectId/documents/:documentId" element={<DocumentView />} />
    </Routes>
  );
}
