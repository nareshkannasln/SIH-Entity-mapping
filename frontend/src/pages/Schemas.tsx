import { useEffect, useState } from "react";
import { api, type DocType, type FieldType, type SchemaField } from "../api";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, EmptyState, Input, Select, Skeleton } from "../components/ui";
import { IconLayers, IconPlus, IconTrash } from "../components/icons";

const FIELD_TYPES: FieldType[] = ["string", "integer", "number", "boolean", "date"];
const emptyField = (): SchemaField => ({ name: "", type: "string", description: "", required: true });

export default function Schemas() {
  const toast = useToast();
  const [docTypes, setDocTypes] = useState<DocType[] | null>(null);
  const [editing, setEditing] = useState<DocType | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [saving, setSaving] = useState(false);

  const reload = () =>
    api
      .listDocTypes()
      .then(setDocTypes)
      .catch((e) => {
        toast.error(e instanceof Error ? e.message : "Could not load document types");
        setDocTypes([]);
      });
  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startNew = () => {
    setIsNew(true);
    setEditing({ key: "", label: "", fields: [emptyField()] });
  };

  const edit = (dt: DocType) => {
    setIsNew(false);
    setEditing(JSON.parse(JSON.stringify(dt)));
  };

  const save = async () => {
    if (!editing) return;
    setSaving(true);
    try {
      const cleaned = { ...editing, fields: editing.fields.filter((f) => f.name.trim() !== "") };
      if (isNew) await api.createDocType(cleaned);
      else await api.updateDocType(cleaned);
      toast.success(isNew ? "Document type created." : "Document type updated.");
      setEditing(null);
      reload();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const updateField = (i: number, patch: Partial<SchemaField>) => {
    if (!editing) return;
    setEditing({ ...editing, fields: editing.fields.map((f, idx) => (idx === i ? { ...f, ...patch } : f)) });
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Document types</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Define the fields extracted from each kind of document.
          </p>
        </div>
        <Button icon={<IconPlus width={16} height={16} />} onClick={startNew}>
          New type
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* List */}
        <div className="space-y-2">
          {!docTypes &&
            Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full rounded-2xl" />
            ))}

          {docTypes && docTypes.length === 0 && (
            <EmptyState
              icon={<IconLayers width={22} height={22} />}
              title="No document types"
              description="Create one to start verifying documents."
              action={<Button icon={<IconPlus width={16} height={16} />} onClick={startNew}>New type</Button>}
            />
          )}

          {docTypes?.map((dt) => (
            <button
              key={dt.key}
              onClick={() => edit(dt)}
              className={`flex w-full items-center justify-between rounded-2xl border bg-white px-4 py-3.5 text-left transition-colors dark:bg-slate-900 ${
                editing?.key === dt.key && !isNew
                  ? "border-indigo-500"
                  : "border-slate-200 hover:border-indigo-300 dark:border-slate-800 dark:hover:border-slate-600"
              }`}
            >
              <div>
                <div className="text-sm font-semibold">{dt.label}</div>
                <div className="text-xs text-slate-400">
                  {dt.key} · {dt.fields.length} fields
                </div>
              </div>
              <Badge tone="indigo">Edit</Badge>
            </button>
          ))}
        </div>

        {/* Editor */}
        <div>
          {editing ? (
            <Card className="p-6">
              <h2 className="mb-4 text-base font-semibold">
                {isNew ? "New document type" : `Edit: ${editing.label}`}
              </h2>
              <div className="space-y-3">
                <Input
                  placeholder="key (lowercase, e.g. invoice)"
                  value={editing.key}
                  disabled={!isNew}
                  onChange={(e) => setEditing({ ...editing, key: e.target.value })}
                />
                <Input
                  placeholder="Label (e.g. Invoice)"
                  value={editing.label}
                  onChange={(e) => setEditing({ ...editing, label: e.target.value })}
                />

                <div className="space-y-2 pt-1">
                  {editing.fields.map((f, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <Input
                        className="w-32 py-1.5"
                        placeholder="field name"
                        value={f.name}
                        onChange={(e) => updateField(i, { name: e.target.value })}
                      />
                      <Select
                        className="w-28 py-1.5"
                        value={f.type}
                        onChange={(e) => updateField(i, { type: e.target.value as FieldType })}
                      >
                        {FIELD_TYPES.map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </Select>
                      <Input
                        className="flex-1 py-1.5"
                        placeholder="description"
                        value={f.description}
                        onChange={(e) => updateField(i, { description: e.target.value })}
                      />
                      <button
                        onClick={() =>
                          setEditing({ ...editing, fields: editing.fields.filter((_, idx) => idx !== i) })
                        }
                        className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-red-500 dark:hover:bg-slate-800"
                        aria-label="Remove field"
                      >
                        <IconTrash width={16} height={16} />
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={() => setEditing({ ...editing, fields: [...editing.fields, emptyField()] })}
                    className="inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                  >
                    <IconPlus width={14} height={14} /> Add field
                  </button>
                </div>

                <div className="flex gap-2 pt-2">
                  <Button onClick={save} loading={saving}>
                    Save
                  </Button>
                  <Button variant="secondary" onClick={() => setEditing(null)}>
                    Cancel
                  </Button>
                </div>
              </div>
            </Card>
          ) : (
            <EmptyState
              icon={<IconLayers width={22} height={22} />}
              title="Select a type to edit"
              description="Or create a new document type to define its fields."
            />
          )}
        </div>
      </div>
    </div>
  );
}
