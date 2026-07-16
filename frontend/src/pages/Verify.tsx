import { useEffect, useMemo, useRef, useState } from "react";
import { api, type DocType } from "../api";
import { parseReferenceFile } from "../lib/importFields";
import { useVerificationRun } from "../lib/verificationRun";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, EmptyState, Field, Input, Select } from "../components/ui";
import { IconCheck, IconFile, IconScan, IconUpload, IconX } from "../components/icons";

const fieldTone = {
  match: "green",
  mismatch: "red",
  missing: "amber",
  no_reference: "slate",
} as const;

const overallTone = { matched: "green", mismatched: "red", extracted: "slate" } as const;

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

// Stages of the real backend pipeline (upload -> rasterize -> OCR -> map -> compare).
// The server sends no progress events, so these advance on elapsed time: they show
// what the request is doing, never a percentage we cannot actually know. Local CPU
// OCR runs ~30s/page, so the later copy reassures rather than implying a stall.
const STAGES: { at: number; label: string; hint: string }[] = [
  { at: 0, label: "Uploading document", hint: "Sending the file to the server" },
  { at: 2, label: "Rendering pages", hint: "Converting the document to page images" },
  { at: 5, label: "Reading the document", hint: "Recognising text on each page" },
  { at: 20, label: "Still reading", hint: "Local CPU OCR takes roughly 30s per page" },
  { at: 45, label: "Extracting fields", hint: "Mapping the text onto this document type" },
  { at: 60, label: "Almost there", hint: "Comparing values against your reference" },
];

function elapsedLabel(s: number) {
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function ProcessingStatus({ startedAt, recovering }: { startedAt: number; recovering: boolean }) {
  // Derived from the run's real start time, not from mount, so the timer stays
  // truthful after navigating away and back — or after a reload.
  const [elapsed, setElapsed] = useState(() => Math.max(0, Math.round((Date.now() - startedAt) / 1000)));

  useEffect(() => {
    const tick = () => setElapsed(Math.max(0, Math.round((Date.now() - startedAt) / 1000)));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [startedAt]);

  const stage = useMemo(
    () =>
      recovering
        ? {
            label: "Picking up where you left off",
            hint: "This document was already being processed — waiting for the result",
          }
        : [...STAGES].reverse().find((s) => elapsed >= s.at) ?? STAGES[0],
    [elapsed, recovering],
  );

  return (
    <div
      className="mb-5 rounded-lg border border-slate-200/60 bg-slate-50/60 p-4
                 dark:border-slate-700/60 dark:bg-slate-800/40"
      aria-live="polite"
    >
      <div className="flex items-center gap-3">
        <span className="relative flex h-2.5 w-2.5 shrink-0">
          <span
            className="absolute inline-flex h-full w-full animate-ping rounded-full
                       bg-indigo-400 opacity-75"
          />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-indigo-500" />
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-2">
            <p className="truncate text-sm font-medium">
              {stage.label}
              <span className="ml-0.5 inline-flex">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="animate-bounce"
                    style={{ animationDelay: `${i * 150}ms` }}
                  >
                    .
                  </span>
                ))}
              </span>
            </p>
            <span className="shrink-0 font-mono text-xs tabular-nums text-slate-500">
              {elapsedLabel(elapsed)}
            </span>
          </div>
          <p className="mt-0.5 truncate text-xs text-slate-500">{stage.hint}</p>
        </div>
      </div>

      {/* Indeterminate bar — the server reports no percentage, so we never fake one. */}
      <div className="mt-3 h-1 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
        <div className="progress-indeterminate" />
      </div>
    </div>
  );
}

export default function Verify() {
  const toast = useToast();
  const [docTypes, setDocTypes] = useState<DocType[]>([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [reference, setReference] = useState<Record<string, string>>({});
  // Lives above the router, so it survives navigating away and page reloads.
  const { busy, result, pending, recovering, run, clear } = useVerificationRun();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api
      .listDocTypes()
      .then((dts) => {
        setDocTypes(dts);
        if (dts.length) setSelectedKey(dts[0].key);
      })
      .catch((e) => toast.error(e instanceof Error ? e.message : "Could not load document types"));
  }, [toast]);

  const selected = useMemo(
    () => docTypes.find((d) => d.key === selectedKey),
    [docTypes, selectedKey]
  );

  const chooseFile = (f: File | null) => {
    clear();
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(f);
    setPreviewUrl(f && f.type.startsWith("image/") ? URL.createObjectURL(f) : null);
  };
  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);

  const handleImport = async (importFile: File | null) => {
    if (!importFile || !selected) return;
    try {
      const parsed = await parseReferenceFile(importFile);
      const canonical = new Map(selected.fields.map((f) => [f.name.toLowerCase(), f.name]));
      const next: Record<string, string> = {};
      let matched = 0;
      for (const [k, v] of Object.entries(parsed)) {
        const name = canonical.get(k.trim().toLowerCase());
        if (name) {
          next[name] = v;
          matched += 1;
        }
      }
      if (matched === 0) {
        toast.info("No fields in the file matched this document type.");
        return;
      }
      setReference((r) => ({ ...r, ...next }));
      toast.success(`Filled ${matched} of ${selected.fields.length} fields from the file.`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not read the file");
    }
  };

  const submit = async () => {
    if (!file || !selected) return;
    try {
      const ref = Object.fromEntries(
        Object.entries(reference).filter(([, v]) => v.trim() !== "")
      );
      const res = await run(selected.key, file, ref);
      if (res.overall_status === "matched") toast.success("All referenced fields matched.");
      else if (res.overall_status === "mismatched") toast.error("Some fields did not match.");
      else toast.success("Document extracted.");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Verification failed");
    }
  };

  const counts = useMemo(() => {
    const fr = result?.field_results ?? [];
    return {
      match: fr.filter((f) => f.status === "match").length,
      mismatch: fr.filter((f) => f.status === "mismatch").length,
      missing: fr.filter((f) => f.status === "missing").length,
    };
  }, [result]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight">Verify a document</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Upload a file, pick its type, and check the extracted fields against your records.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Input */}
        <Card className="space-y-5 p-6">
          <Field label="Document type">
            <Select
              value={selectedKey}
              onChange={(e) => {
                setSelectedKey(e.target.value);
                setReference({});
              }}
            >
              {docTypes.map((d) => (
                <option key={d.key} value={d.key}>
                  {d.label}
                </option>
              ))}
            </Select>
          </Field>

          {/* Drag & drop upload */}
          <div>
            <span className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
              File (PDF or image)
            </span>
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf,image/*"
              className="hidden"
              onChange={(e) => chooseFile(e.target.files?.[0] ?? null)}
            />
            {!file ? (
              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOver(false);
                  chooseFile(e.dataTransfer.files?.[0] ?? null);
                }}
                className={`flex w-full flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
                  dragOver
                    ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-500/10"
                    : "border-slate-300 hover:border-indigo-400 dark:border-slate-700"
                }`}
              >
                <IconUpload className="text-slate-400" width={26} height={26} />
                <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
                  Drop a file here, or <span className="text-indigo-600 dark:text-indigo-400">browse</span>
                </span>
                <span className="text-xs text-slate-400">PDF, PNG, JPEG, WEBP or GIF</span>
              </button>
            ) : (
              <div className="flex items-center gap-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                {previewUrl ? (
                  <img src={previewUrl} alt="" className="h-14 w-14 rounded-lg object-cover" />
                ) : (
                  <span className="grid h-14 w-14 place-items-center rounded-lg bg-slate-100 text-slate-400 dark:bg-slate-800">
                    <IconFile width={22} height={22} />
                  </span>
                )}
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{file.name}</p>
                  <p className="text-xs text-slate-400">{formatBytes(file.size)}</p>
                </div>
                <button
                  onClick={() => chooseFile(null)}
                  className="grid h-8 w-8 place-items-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-red-500 dark:hover:bg-slate-800"
                  aria-label="Remove file"
                >
                  <IconX width={18} height={18} />
                </button>
              </div>
            )}
          </div>

          {/* Reference values */}
          {selected && (
            <div>
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Reference values{" "}
                  <span className="font-normal text-slate-400">(optional)</span>
                </span>
                <label className="shrink-0 cursor-pointer text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400">
                  Import JSON / Excel
                  <input
                    type="file"
                    accept=".json,.xlsx,.xls,.csv"
                    className="hidden"
                    onChange={(e) => {
                      handleImport(e.target.files?.[0] ?? null);
                      e.target.value = "";
                    }}
                  />
                </label>
              </div>
              <div className="space-y-2">
                {selected.fields.map((f) => (
                  <div key={f.name} className="flex items-center gap-2">
                    <span
                      className="w-36 shrink-0 truncate text-xs text-slate-500 dark:text-slate-400"
                      title={f.description || f.name}
                    >
                      {f.name}
                    </span>
                    <Input
                      className="flex-1 py-1.5 text-sm"
                      placeholder="expected value"
                      value={reference[f.name] ?? ""}
                      onChange={(e) => setReference((r) => ({ ...r, [f.name]: e.target.value }))}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          <Button
            onClick={submit}
            disabled={!file}
            loading={busy}
            icon={<IconScan width={16} height={16} />}
            className="w-full"
          >
            {busy ? "Reading document…" : "Extract & verify"}
          </Button>
        </Card>

        {/* Result */}
        <Card className="p-6">
          <h2 className="mb-4 text-base font-semibold">Result</h2>

          {busy && (
            <>
              <ProcessingStatus
                startedAt={pending?.startedAt ?? Date.now()}
                recovering={recovering}
              />
              <div className="space-y-3">
                <div className="skeleton h-6 w-40 rounded-md" />
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="skeleton h-9 w-full rounded-md" />
                ))}
              </div>
            </>
          )}

          {!busy && !result && (
            <EmptyState
              icon={<IconScan width={22} height={22} />}
              title="No result yet"
              description="Extracted fields and their match status will appear here."
            />
          )}

          {!busy && result && (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={overallTone[result.overall_status]}>{result.overall_status}</Badge>
                {counts.match > 0 && <Badge tone="green">{counts.match} matched</Badge>}
                {counts.mismatch > 0 && <Badge tone="red">{counts.mismatch} mismatched</Badge>}
                {counts.missing > 0 && <Badge tone="amber">{counts.missing} missing</Badge>}
                {result.doc_type_mismatch && (
                  <Badge tone="amber">detected as “{result.document_type_detected}”</Badge>
                )}
                {result.engine && (
                  <span className="ml-auto text-xs text-slate-400">via {result.engine}</span>
                )}
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-wide text-slate-400">
                    <tr>
                      <th className="py-1.5 pr-2 font-medium">Field</th>
                      <th className="py-1.5 pr-2 font-medium">Extracted</th>
                      <th className="py-1.5 pr-2 font-medium">Expected</th>
                      <th className="py-1.5 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {result.field_results.map((fr) => (
                      <tr key={fr.field} className="align-top">
                        <td className="py-2 pr-2 font-medium text-slate-700 dark:text-slate-200">
                          {fr.field}
                        </td>
                        <td className="py-2 pr-2 break-words">{String(fr.extracted ?? "—")}</td>
                        <td className="py-2 pr-2 text-slate-500 dark:text-slate-400">
                          {fr.expected == null ? "—" : String(fr.expected)}
                        </td>
                        <td className="py-2">
                          <Badge tone={fieldTone[fr.status]}>
                            {fr.status === "match" && <IconCheck width={12} height={12} />}
                            {fr.status === "mismatch" && <IconX width={12} height={12} />}
                            {fr.status}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
