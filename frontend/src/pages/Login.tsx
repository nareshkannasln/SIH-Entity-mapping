import { useState, type FormEvent } from "react";
import { useAuth } from "../auth";
import { Button, Input } from "../components/ui";
import { IconAlert, IconLayers, IconScan, IconShield } from "../components/icons";

const features = [
  { icon: IconScan, title: "Read any document", body: "OCR + AI extraction for PDFs and images — no templates." },
  { icon: IconLayers, title: "Your own schemas", body: "Define document types and the exact fields you need." },
  { icon: IconShield, title: "Verify against references", body: "Per-field match / mismatch reports you can trust." },
];

export default function Login() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "login") await login(username, password);
      else await register(username, email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Brand / value panel */}
      <div className="relative hidden overflow-hidden bg-gradient-to-br from-indigo-600 via-indigo-700 to-violet-800 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-white/15">
            <IconShield width={20} height={20} />
          </span>
          <span className="text-lg font-bold tracking-tight">DocVerify</span>
        </div>
        <div>
          <h2 className="max-w-md text-3xl font-bold leading-tight">
            Turn documents into verified, structured data.
          </h2>
          <p className="mt-3 max-w-md text-indigo-100">
            Upload a certificate, marksheet, or ID — extract the fields and check them against your
            records in seconds.
          </p>
          <div className="mt-8 space-y-5">
            {features.map(({ icon: Icon, title, body }) => (
              <div key={title} className="flex gap-3">
                <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-white/10">
                  <Icon width={18} height={18} />
                </span>
                <div>
                  <p className="font-semibold">{title}</p>
                  <p className="text-sm text-indigo-100">{body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
        <p className="text-xs text-indigo-200">Works fully offline with the built-in OCR engine.</p>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <span className="text-2xl font-bold tracking-tight">
              Doc<span className="text-indigo-600 dark:text-indigo-400">Verify</span>
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">
            {mode === "login" ? "Welcome back" : "Create your account"}
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {mode === "login" ? "Sign in to continue to DocVerify." : "Get started in a few seconds."}
          </p>

          <form onSubmit={submit} className="mt-6 space-y-4">
            <Input
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
            {mode === "register" && (
              <Input
                placeholder="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            )}
            <Input
              placeholder="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            {error && (
              <p className="flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">
                <IconAlert width={16} height={16} />
                {error}
              </p>
            )}
            <Button type="submit" loading={busy} className="w-full">
              {mode === "login" ? "Sign in" : "Create account"}
            </Button>
          </form>

          <button
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError(null);
            }}
            className="mt-5 w-full text-center text-sm text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400"
          >
            {mode === "login" ? (
              <>Don't have an account? <span className="font-medium text-indigo-600 dark:text-indigo-400">Register</span></>
            ) : (
              <>Already have an account? <span className="font-medium text-indigo-600 dark:text-indigo-400">Sign in</span></>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
