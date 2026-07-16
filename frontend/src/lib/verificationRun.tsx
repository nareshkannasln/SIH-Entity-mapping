/* Keeps one verification run alive across navigation and page reloads.
 *
 * Two different problems, two different fixes:
 *
 *  - Navigating away used to unmount <Verify/>, taking `busy`/`result` with it.
 *    The request kept running but its result landed on a dead component, so
 *    coming back showed an empty form. This provider sits above the router, so
 *    it never unmounts and the result is still here when you return.
 *
 *  - Reloading kills the in-flight fetch outright; no client-side state can
 *    survive that. But the server always finishes the job and writes it to
 *    `verifications` (documents.py) *before* responding — so the result is never
 *    really lost. On reload we replay it from history instead of re-running the
 *    extraction (which would cost another ~30s of OCR, or another API call).
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, type VerificationResult } from "../api";

const RESULT_KEY = "docverify_last_result";
const PENDING_KEY = "docverify_pending";

// Tolerate clock skew between browser and server when matching history rows.
const CLOCK_SKEW_MS = 60_000;
const POLL_MS = 3_000;
const POLL_TIMEOUT_MS = 5 * 60_000;

interface Pending {
  startedAt: number;
  filename: string;
  docType: string;
}

interface RunState {
  busy: boolean;
  result: VerificationResult | null;
  pending: Pending | null;
  /** True when we are re-attaching to a run that survived a reload. */
  recovering: boolean;
  run: (docType: string, file: File, reference: Record<string, unknown>) => Promise<VerificationResult>;
  clear: () => void;
}

const Ctx = createContext<RunState | null>(null);

/* True once the page is going away.
 *
 * A reload aborts the in-flight fetch, so `run()`'s error path executes while
 * the document is being torn down. Without this flag it cleared PENDING_KEY on
 * the way out and the next load had nothing to recover from — the exact case
 * the marker exists for. An abort during unload says nothing about the server,
 * which carries on and still writes the row. */
let pageUnloading = false;
if (typeof window !== "undefined") {
  window.addEventListener("pagehide", () => {
    pageUnloading = true;
  });
}

function readJSON<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function writeJSON(key: string, value: unknown | null) {
  try {
    if (value === null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* private mode / quota — persistence is a bonus, never required */
  }
}

/** Epoch ms for a server timestamp.
 *
 * The API serialises `created_at` from Mongo without an offset
 * ("2026-07-16T20:56:29.919000"), but the value is UTC. `Date.parse` reads a
 * naive string as *local* time, which in IST would shift it 5.5h into the past
 * and stop every row from ever matching. Force UTC when no offset is present.
 */
function serverTimeMs(iso: string): number {
  const hasZone = /(?:[zZ]|[+-]\d{2}:?\d{2})$/.test(iso);
  return Date.parse(hasZone ? iso : `${iso}Z`);
}

/** The history row this run produced, if it has landed yet. */
function findMatch(rows: VerificationResult[], p: Pending): VerificationResult | undefined {
  return rows.find(
    (r) =>
      r.filename === p.filename &&
      r.doc_type === p.docType &&
      r.created_at != null &&
      serverTimeMs(r.created_at) >= p.startedAt - CLOCK_SKEW_MS,
  );
}

export function VerificationRunProvider({ children }: { children: ReactNode }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);
  const [recovering, setRecovering] = useState(false);

  // Restore whatever the previous page-load left behind.
  //
  // `active` is scoped to this invocation on purpose. StrictMode runs effects
  // twice in dev; with a shared ref, the discarded first pass would sail past
  // its guard (the remount having reset the ref) and run its cleanup tail —
  // wiping PENDING_KEY and setting busy=false, which silently killed the very
  // recovery the second pass had just started.
  useEffect(() => {
    let active = true;

    const saved = readJSON<VerificationResult>(RESULT_KEY);
    if (saved) setResult(saved);

    const p = readJSON<Pending>(PENDING_KEY);
    if (!p) return;

    // A run was in flight when the page went away. Its fetch is gone, but the
    // server kept going — poll history for the row it wrote.
    if (Date.now() - p.startedAt > POLL_TIMEOUT_MS) {
      writeJSON(PENDING_KEY, null);
      return;
    }

    setPending(p);
    setBusy(true);
    setRecovering(true);

    const deadline = p.startedAt + POLL_TIMEOUT_MS;

    (async () => {
      while (active && Date.now() < deadline) {
        try {
          const hit = findMatch(await api.listVerifications(), p);
          if (!active) return;
          if (hit) {
            setResult(hit);
            writeJSON(RESULT_KEY, hit);
            break;
          }
        } catch {
          /* transient — keep polling until the deadline */
        }
        await new Promise((r) => setTimeout(r, POLL_MS));
      }
      if (!active) return; // superseded: leave state for the live pass
      writeJSON(PENDING_KEY, null);
      setPending(null);
      setBusy(false);
      setRecovering(false);
    })();

    return () => {
      active = false;
    };
  }, []);

  const run = useCallback(
    async (docType: string, file: File, reference: Record<string, unknown>) => {
      const p: Pending = { startedAt: Date.now(), filename: file.name, docType };
      setPending(p);
      setBusy(true);
      setResult(null);
      setRecovering(false);
      writeJSON(PENDING_KEY, p);
      writeJSON(RESULT_KEY, null);

      try {
        const res = await api.verify(docType, file, reference);
        setResult(res);
        writeJSON(RESULT_KEY, res);
        writeJSON(PENDING_KEY, null);
        setPending(null);
        setBusy(false);
        return res;
      } catch (e) {
        // Only retire the marker if we are still here to act on the failure.
        // Mid-unload the abort tells us nothing — keep it so the next load can
        // pick the result up from history.
        if (!pageUnloading) {
          writeJSON(PENDING_KEY, null);
          setPending(null);
          setBusy(false);
        }
        throw e;
      }
    },
    [],
  );

  const clear = useCallback(() => {
    setResult(null);
    writeJSON(RESULT_KEY, null);
  }, []);

  return (
    <Ctx.Provider value={{ busy, result, pending, recovering, run, clear }}>{children}</Ctx.Provider>
  );
}

export function useVerificationRun() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useVerificationRun must be used within VerificationRunProvider");
  return ctx;
}
