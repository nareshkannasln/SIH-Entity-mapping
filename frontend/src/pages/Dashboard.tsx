import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, type VerificationResult } from "../api";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, EmptyState, Skeleton } from "../components/ui";
import { IconCheck, IconGrid, IconPlus, IconScan, IconX } from "../components/icons";

const statusTone = { matched: "green", mismatched: "red", extracted: "slate" } as const;

function StatTile({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <Card className="p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${tone}`}>{value}</p>
    </Card>
  );
}

export default function Dashboard() {
  const [items, setItems] = useState<VerificationResult[] | null>(null);
  const toast = useToast();

  useEffect(() => {
    api
      .listVerifications()
      .then(setItems)
      .catch((e) => {
        toast.error(e instanceof Error ? e.message : "Could not load verifications");
        setItems([]);
      });
  }, [toast]);

  const stats = useMemo(() => {
    const list = items ?? [];
    return {
      total: list.length,
      matched: list.filter((v) => v.overall_status === "matched").length,
      mismatched: list.filter((v) => v.overall_status === "mismatched").length,
    };
  }, [items]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Recent document verifications.
          </p>
        </div>
        <Link to="/verify">
          <Button icon={<IconPlus width={16} height={16} />}>New verification</Button>
        </Link>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <StatTile label="Total" value={stats.total} tone="text-slate-900 dark:text-slate-100" />
        <StatTile label="Matched" value={stats.matched} tone="text-emerald-600 dark:text-emerald-400" />
        <StatTile label="Mismatched" value={stats.mismatched} tone="text-red-600 dark:text-red-400" />
      </div>

      {!items && (
        <Card className="divide-y divide-slate-100 dark:divide-slate-800">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-4 py-3.5">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="ml-auto h-5 w-20" />
            </div>
          ))}
        </Card>
      )}

      {items && items.length === 0 && (
        <EmptyState
          icon={<IconGrid width={22} height={22} />}
          title="No verifications yet"
          description="Upload your first document to extract and verify its fields."
          action={
            <Link to="/verify">
              <Button icon={<IconScan width={16} height={16} />}>Verify a document</Button>
            </Link>
          }
        />
      )}

      {items && items.length > 0 && (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-100 bg-slate-50/60 text-left text-xs uppercase tracking-wide text-slate-400 dark:border-slate-800 dark:bg-slate-800/40">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Document</th>
                  <th className="px-4 py-2.5 font-medium">Type</th>
                  <th className="px-4 py-2.5 font-medium">Result</th>
                  <th className="px-4 py-2.5 font-medium">Engine</th>
                  <th className="px-4 py-2.5 font-medium">When</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {items.map((v) => (
                  <tr key={v.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                    <td className="max-w-[16rem] truncate px-4 py-3 font-medium">{v.filename}</td>
                    <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{v.doc_type}</td>
                    <td className="px-4 py-3">
                      <span className="flex flex-wrap items-center gap-1.5">
                        <Badge tone={statusTone[v.overall_status]}>
                          {v.overall_status === "matched" && <IconCheck width={12} height={12} />}
                          {v.overall_status === "mismatched" && <IconX width={12} height={12} />}
                          {v.overall_status}
                        </Badge>
                        {v.doc_type_mismatch && <Badge tone="amber">type mismatch</Badge>}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">{v.engine ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                      {v.created_at ? new Date(v.created_at).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
