import { Link, useNavigate } from "react-router-dom";
import { LayoutDashboard, LogOut, LogIn, UserPlus, Sparkles } from "lucide-react";
import { supabase } from "../lib/supabase";
import { useEffect, useState } from "react";
import { Session } from "@supabase/supabase-js";

export default function Home() {
  const [session, setSession] = useState<Session | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: s } }) => setSession(s));
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => subscription.unsubscribe();
  }, []);

  async function handleSignOut() {
    await supabase.auth.signOut();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <header className="border-b border-slate-200/80 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex justify-between items-center">
          <span className="text-xl font-semibold text-slate-800">Kingly</span>
          <nav className="flex items-center gap-4">
            {session ? (
              <>
                <Link to="/dashboard" className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900">
                  <LayoutDashboard className="h-4 w-4" />
                  Dashboard
                </Link>
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900"
                >
                  <LogOut className="h-4 w-4" />
                  Sign out
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900"
                >
                  <LogIn className="h-4 w-4" />
                  Sign in
                </Link>
                <Link to="/register" className="btn-primary text-sm inline-flex items-center gap-2">
                  <UserPlus className="h-4 w-4" />
                  Get started
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-16 md:py-24">
        <section className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-bold text-slate-900 tracking-tight mb-4">
            Turn app ideas into specs and build prompts
          </h1>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto mb-10">
            Kingly uses AI agents to generate business logic, product requirements, and implementation prompts from an app description—so you can ship faster.
          </p>
          {session ? (
            <Link to="/dashboard" className="btn-primary text-base px-6 py-3 inline-flex items-center gap-2">
              <LayoutDashboard className="h-5 w-5" />
              Go to Dashboard
            </Link>
          ) : (
          <Link to="/register" className="btn-primary text-base px-6 py-3 inline-flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            Create free account
          </Link>
          )}
        </section>

        <section className="border-t border-slate-200 pt-16">
          <h2 className="text-2xl font-semibold text-slate-900 mb-8 text-center">
            What you can do
          </h2>
          <ul className="grid gap-6 sm:grid-cols-2">
            <li className="card p-6">
              <h3 className="font-semibold text-slate-900 mb-2">Create projects</h3>
              <p className="text-sm text-slate-600">
                Organize work by project. Add a short description and optional uploads (PDF, DOCX, or Markdown) to give the AI context.
              </p>
            </li>
            <li className="card p-6">
              <h3 className="font-semibold text-slate-900 mb-2">Generate business logic</h3>
              <p className="text-sm text-slate-600">
                One agent turns your app description or PRD into structured business logic: entities, flows, rules, and integrations—all in markdown.
              </p>
            </li>
            <li className="card p-6">
              <h3 className="font-semibold text-slate-900 mb-2">Generate a PRD</h3>
              <p className="text-sm text-slate-600">
                Another agent writes a full Product Requirements Document: user stories, functional and non-functional requirements, and scope.
              </p>
            </li>
            <li className="card p-6">
              <h3 className="font-semibold text-slate-900 mb-2">Get build prompts</h3>
              <p className="text-sm text-slate-600">
                A third agent produces 3–5 implementation prompts you can use with AI coding tools or developers to build the app step by step.
              </p>
            </li>
            <li className="card p-6 sm:col-span-2">
              <h3 className="font-semibold text-slate-900 mb-2">Download everything as a zip</h3>
              <p className="text-sm text-slate-600">
                Generate business logic, PRD, and prompts in one go and download a zip with all markdown files ready to share or version.
              </p>
            </li>
          </ul>
        </section>

        {!session && (
          <section className="mt-16 text-center">
            <p className="text-slate-500 text-sm mb-4">
              Already have an account?
            </p>
            <Link to="/login" className="text-blue-600 font-medium hover:underline">
              Sign in
            </Link>
          </section>
        )}
      </main>
    </div>
  );
}
