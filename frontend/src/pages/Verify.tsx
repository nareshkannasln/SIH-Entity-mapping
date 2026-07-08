import { useEffect, useMemo, useState } from "react";
import { api, type DocType, type VerificationResult } from "../api";

const fieldStatusBadge: Record<string, string> = {
  match: "bg-green-100 text-green-800",
  mismatch: "bg-red-100 text-red-800",
  missing: "bg-amber-100 text-amber-800",
  no_reference: "bg-slate-100 text-slate-600",
};

export default function Verify() {
  const [docTypes, setDocTypes] = useState<DocType[]>([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [reference, setReference] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VerificationResult | null>(null);

  useEffect(() => {
    api.listDocTypes().then((dts) => {
      setDocTypes(dts);
      if (dts.length) setSelectedKey(dts[0].key);
    });
  }, []);

  const selected = useMemo(
    () => docTypes.find((d) => d.key === selectedKey),
    [docTypes, selectedKey]
  );

  const submit = async () => {
    if (!file || !selected) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const ref = Object.fromEntries(
        Object.entries(reference).filter(([, v]) => v.trim() !== "")
      );
      const res = await api.verify(selected.key, file, ref);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Verification failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid gap-8 md:grid-cols-2">
      {/* Input panel */}
      <div className="space-y-5 rounded-lg border border-slate-200 bg-white p-6">
        <h1 className="text-lg font-semibold">Verify a document</h1>

        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">Document type</span>
          <select
            className="w-full rounded-md border border-slate-300 px-3 py-2"
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
          </select>
        </label>

        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">File (PDF or image)</span>
          <input
            type="file"
            accept="application/pdf,image/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="w-full text-sm"
          />
        </label>

        {selected && (
          <div>
            <p className="mb-2 text-sm font-medium text-slate-700">
              Reference values <span className="font-normal text-slate-400">(optional — to check against)</span>
            </p>
            <div className="space-y-2">
              {selected.fields.map((f) => (
                <div key={f.name} className="flex items-center gap-2">
                  <span className="w-40 shrink-0 truncate text-xs text-slate-500" title={f.description}>
                    {f.name}
                  </span>
                  <input
                    className="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm"
                    placeholder="expected value"
                    value={reference[f.name] ?? ""}
                    onChange={(e) => setReference((r) => ({ ...r, [f.name]: e.target.value }))}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          onClick={submit}
          disabled={!file || busy}
          className="w-full rounded-md bg-indigo-600 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {busy ? "Reading document…" : "Extract & verify"}
        </button>
      </div>

      {/* Result panel */}
      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold">Result</h2>
        {busy && <p className="text-sm text-slate-500">Claude is reading the document — this takes a few seconds…</p>}
        {!busy && !result && <p className="text-sm text-slate-400">Results will appear here.</p>}

        {result && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-slate-500">Overall:</span>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium">
                {result.overall_status}
              </span>
              {result.doc_type_mismatch && (
                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                  ⚠ detected as “{result.document_type_detected}”
                </span>
              )}
            </div>

            <table className="w-full text-sm">
              <thead className="text-left text-slate-500">
                <tr>
                  <th className="py-1 font-medium">Field</th>
                  <th className="py-1 font-medium">Extracted</th>
                  <th className="py-1 font-medium">Expected</th>
                  <th className="py-1 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {result.field_results.map((fr) => (
                  <tr key={fr.field} className="border-t border-slate-100 align-top">
                    <td className="py-2 pr-2 font-medium text-slate-700">{fr.field}</td>
                    <td className="py-2 pr-2 break-words">{String(fr.extracted ?? "—")}</td>
                    <td className="py-2 pr-2 text-slate-500">
                      {fr.expected == null ? "—" : String(fr.expected)}
                    </td>
                    <td className="py-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${fieldStatusBadge[fr.status]}`}>
                        {fr.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
