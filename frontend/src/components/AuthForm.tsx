import { ArrowUpRight, CircleAlert, Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, getApiError } from "../api";
import { Logo } from "./Logo";

export function AuthForm({
  mode,
  onAuthenticated,
}: {
  mode: "login" | "register";
  onAuthenticated: (access: string, refresh: string, email: string) => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "register") await api.register(email, password);
      const session = await api.login(email, password);
      onAuthenticated(session.access_token, session.refresh_token, email);
    } catch (err) {
      setError(
        getApiError(
          err,
          mode === "login"
            ? "Check your email and password."
            : "Unable to create your account.",
        ),
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-5 bg-[#17233b] p-5 md:flex-row md:gap-6">
      <section className="w-full max-w-md rounded-2xl bg-[#fffefa] p-8 shadow-2xl sm:p-11">
        <Logo dark />
        <p className="mt-12 text-[10px] font-bold uppercase tracking-[.15em] text-[#e88d35]">
          PERSONAL DOCUMENT INTELLIGENCE
        </p>
        <h1 className="mt-3 font-serif text-4xl font-medium leading-tight tracking-tight">
          {mode === "login" ? (
            <>
              Your documents,
              <br />
              <em className="not-italic text-[#e88d35]">made answerable.</em>
            </>
          ) : (
            <>
              Start your document
              <br />
              <em className="not-italic text-[#e88d35]">workspace.</em>
            </>
          )}
        </h1>
        <p className="mt-4 text-sm leading-6 text-slate-500">
          Ask questions across your government PDFs and get answers grounded in
          the source.
        </p>
        <form onSubmit={submit} className="mt-7 space-y-4">
          <label className="block text-xs font-semibold text-slate-600">
            Email address
            <input
              required
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-sm outline-none focus:border-[#e88d35] focus:ring-2 focus:ring-orange-100"
            />
          </label>
          <label className="block text-xs font-semibold text-slate-600">
            Password
            <span className="relative mt-2 block">
              <input
                required
                minLength={8}
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 pr-10 text-sm outline-none focus:border-[#e88d35] focus:ring-2 focus:ring-orange-100"
              />
              <button
                type="button"
                onClick={() => setShowPassword((visible) => !visible)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                title={showPassword ? "Hide password" : "Show password"}
                className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-400 transition hover:text-slate-600"
              >
                {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </span>
          </label>
          {error && (
            <p className="flex items-center gap-2 text-xs text-red-600">
              <CircleAlert size={14} />
              {error}
            </p>
          )}
          <button
            disabled={busy}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#e88d35] px-4 py-3 text-sm font-bold text-white shadow-lg shadow-orange-200 transition hover:bg-[#d87b27] disabled:opacity-50"
          >
            {busy
              ? "Opening workspace…"
              : mode === "login"
                ? "Enter workspace"
                : "Create account"}
            <ArrowUpRight size={17} />
          </button>
        </form>
        <p className="mt-6 text-center text-xs text-slate-500">
          {mode === "login" ? "New to gujdoc?" : "Already have an account?"}{" "}
          <Link
            className="font-bold text-[#e88d35]"
            to={mode === "login" ? "/register" : "/login"}
          >
            {mode === "login" ? "Create an account" : "Sign in"}
          </Link>
        </p>
      </section>
      {mode === "login" && (
        <aside className="w-full max-w-md rounded-2xl border border-white/10 bg-white/10 p-6 text-white backdrop-blur-sm md:max-w-xs">
          <p className="text-xs font-bold uppercase tracking-[.15em] text-[#f3b36e]">
            Demo account
          </p>
          <p className="mt-2 text-sm text-slate-200">
            Use these credentials to explore the workspace.
          </p>
          <dl className="mt-5 space-y-3 text-sm">
            <div>
              <dt className="text-xs text-slate-300">Email</dt>
              <dd className="mt-1 font-semibold">admin@gmail.com</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-300">Password</dt>
              <dd className="mt-1 font-semibold">Admin@123</dd>
            </div>
          </dl>
        </aside>
      )}
    </main>
  );
}
