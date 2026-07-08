import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type VerificationResult } from "../api";

const statusBadge: Record<string, string> = {
  matched: "bg-green-100 text-green-800",
  mismatched: "bg-red-100 text-red-800",
  extracted: "bg-slate-100 text-slate-700",
};

export default function Dashboard() {
  const [items, setItems] = useState<VerificationResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listVerifications().then(setItems).catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Verifications</h1>
        <Link
          to="/verify"
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          New verification
        </Link>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {!items && !error && <p className="text-sm text-slate-500">Loading…</p>}
      {items && items.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 p-10 text-center text-slate-500">
          No verifications yet. Start by uploading a document.
        </div>
      )}

      {items && items.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-500">
              <tr>
                <th className="px-4 py-2 font-medium">Document</th>
                <th className="px-4 py-2 font-medium">Type</th>
                <th className="px-4 py-2 font-medium">Result</th>
                <th className="px-4 py-2 font-medium">When</th>
              </tr>
            </thead>
            <tbody>
              {items.map((v) => (
                <tr key={v.id} className="border-t border-slate-100">
                  <td className="px-4 py-3">{v.filename}</td>
                  <td className="px-4 py-3">{v.doc_type}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusBadge[v.overall_status]}`}>
                      {v.overall_status}
                    </span>
                    {v.doc_type_mismatch && (
                      <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                        type mismatch
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {v.created_at ? new Date(v.created_at).toLocaleString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
