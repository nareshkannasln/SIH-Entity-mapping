import { useEffect, useState } from "react";
import { api, type DocType, type FieldType, type SchemaField } from "../api";

const FIELD_TYPES: FieldType[] = ["string", "integer", "number", "boolean", "date"];

const emptyField = (): SchemaField => ({ name: "", type: "string", description: "", required: true });

export default function Schemas() {
  const [docTypes, setDocTypes] = useState<DocType[]>([]);
  const [editing, setEditing] = useState<DocType | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = () => api.listDocTypes().then(setDocTypes).catch((e) => setError(e.message));
  useEffect(() => {
    reload();
  }, []);

  const startNew = () => {
    setIsNew(true);
    setEditing({ key: "", label: "", fields: [emptyField()] });
    setError(null);
  };

  const edit = (dt: DocType) => {
    setIsNew(false);
    setEditing(JSON.parse(JSON.stringify(dt)));
    setError(null);
  };

  const save = async () => {
    if (!editing) return;
    setError(null);
    try {
      const cleaned = {
        ...editing,
        fields: editing.fields.filter((f) => f.name.trim() !== ""),
      };
      if (isNew) await api.createDocType(cleaned);
      else await api.updateDocType(cleaned);
      setEditing(null);
      reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  };

  const updateField = (i: number, patch: Partial<SchemaField>) => {
    if (!editing) return;
    const fields = editing.fields.map((f, idx) => (idx === i ? { ...f, ...patch } : f));
    setEditing({ ...editing, fields });
  };

  return (
    <div className="grid gap-8 md:grid-cols-2">
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-lg font-semibold">Document types</h1>
          <button
            onClick={startNew}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
          >
            + New
          </button>
        </div>
        <div className="space-y-2">
          {docTypes.map((dt) => (
            <button
              key={dt.key}
              onClick={() => edit(dt)}
              className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3 text-left hover:border-indigo-300"
            >
              <div>
                <div className="text-sm font-medium">{dt.label}</div>
                <div className="text-xs text-slate-400">
                  {dt.key} · {dt.fields.length} fields
                </div>
              </div>
              <span className="text-xs text-indigo-600">Edit</span>
            </button>
          ))}
        </div>
      </div>

      <div>
        {editing ? (
          <div className="rounded-lg border border-slate-200 bg-white p-6">
            <h2 className="mb-4 text-lg font-semibold">{isNew ? "New document type" : `Edit: ${editing.label}`}</h2>
            <div className="space-y-3">
              <input
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100"
                placeholder="key (lowercase, e.g. invoice)"
                value={editing.key}
                disabled={!isNew}
                onChange={(e) => setEditing({ ...editing, key: e.target.value })}
              />
              <input
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="Label (e.g. Invoice)"
                value={editing.label}
                onChange={(e) => setEditing({ ...editing, label: e.target.value })}
              />

              <div className="space-y-2">
                {editing.fields.map((f, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <input
                      className="w-32 rounded-md border border-slate-300 px-2 py-1 text-sm"
                      placeholder="field name"
                      value={f.name}
                      onChange={(e) => updateField(i, { name: e.target.value })}
                    />
                    <select
                      className="rounded-md border border-slate-300 px-2 py-1 text-sm"
                      value={f.type}
                      onChange={(e) => updateField(i, { type: e.target.value as FieldType })}
                    >
                      {FIELD_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                    <input
                      className="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm"
                      placeholder="description"
                      value={f.description}
                      onChange={(e) => updateField(i, { description: e.target.value })}
                    />
                    <button
                      onClick={() => setEditing({ ...editing, fields: editing.fields.filter((_, idx) => idx !== i) })}
                      className="px-1 text-slate-400 hover:text-red-600"
                    >
                      ✕
                    </button>
                  </div>
                ))}
                <button
                  onClick={() => setEditing({ ...editing, fields: [...editing.fields, emptyField()] })}
                  className="text-sm text-indigo-600 hover:underline"
                >
                  + Add field
                </button>
              </div>

              {error && <p className="text-sm text-red-600">{error}</p>}
              <div className="flex gap-2 pt-2">
                <button
                  onClick={save}
                  className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                >
                  Save
                </button>
                <button
                  onClick={() => setEditing(null)}
                  className="rounded-md border border-slate-300 px-4 py-2 text-sm hover:bg-slate-100"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-slate-300 p-10 text-center text-sm text-slate-500">
            Select a document type to edit, or create a new one.
          </div>
        )}
      </div>
    </div>
  );
}
