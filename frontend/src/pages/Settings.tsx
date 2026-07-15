import { useEffect, useState, type FormEvent } from "react";
import { api, type LLMSettings, type Provider } from "../api";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, Field, Input } from "../components/ui";
import { IconShield } from "../components/icons";

interface Preset {
  label: string;
  free: boolean;
  needsKey: boolean;
  needsBaseUrl: boolean;
  defaultModel: string;
  defaultBaseUrl: string;
  hint: string;
  keyUrl?: string;
}

const PRESETS: Record<Provider, Preset> = {
  offline: {
    label: "Offline OCR + NER",
    free: true,
    needsKey: false,
    needsBaseUrl: false,
    defaultModel: "",
    defaultBaseUrl: "",
    hint: "Built-in Tesseract OCR + spaCy NER engine. Runs on the server with no API key and no GPU. Best for privacy and zero cost; accuracy is lower than the vision models.",
  },
  gemini: {
    label: "Google Gemini",
    free: true,
    needsKey: true,
    needsBaseUrl: true,
    defaultModel: "gemini-2.5-flash",
    defaultBaseUrl: "https://generativelanguage.googleapis.com/v1beta/openai/",
    hint: "Generous free tier (~1,500 requests/day). Model must be vision-capable.",
    keyUrl: "https://aistudio.google.com/apikey",
  },
  groq: {
    label: "Groq",
    free: true,
    needsKey: true,
    needsBaseUrl: true,
    defaultModel: "meta-llama/llama-4-scout-17b-16e-instruct",
    defaultBaseUrl: "https://api.groq.com/openai/v1",
    hint: "Free tier, extremely fast. Use a vision-capable Llama model.",
    keyUrl: "https://console.groq.com/keys",
  },
  openrouter: {
    label: "OpenRouter",
    free: true,
    needsKey: true,
    needsBaseUrl: true,
    defaultModel: "meta-llama/llama-3.2-11b-vision-instruct:free",
    defaultBaseUrl: "https://openrouter.ai/api/v1",
    hint: "Routes to many models; “:free” variants cost nothing (rate-limited). Use a vision model.",
    keyUrl: "https://openrouter.ai/keys",
  },
  openai: {
    label: "OpenAI-compatible / Ollama",
    free: false,
    needsKey: true,
    needsBaseUrl: true,
    defaultModel: "qwen2.5vl:32b",
    defaultBaseUrl: "http://localhost:11434/v1",
    hint: "Any OpenAI-compatible endpoint, e.g. a self-hosted Ollama server. Model must be vision-capable.",
  },
  anthropic: {
    label: "Anthropic (Claude)",
    free: false,
    needsKey: true,
    needsBaseUrl: false,
    defaultModel: "claude-opus-4-8",
    defaultBaseUrl: "",
    hint: "Claude via the Anthropic API. Highest accuracy. Base URL is not used.",
    keyUrl: "https://console.anthropic.com/settings/keys",
  },
};

const ORDER: Provider[] = ["offline", "gemini", "groq", "openrouter", "openai", "anthropic"];

export default function Settings() {
  const toast = useToast();
  const [provider, setProvider] = useState<Provider>("offline");
  const [model, setModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [keySet, setKeySet] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const preset = PRESETS[provider];

  const apply = (s: LLMSettings) => {
    setProvider(s.provider);
    setModel(s.model);
    setBaseUrl(s.base_url);
    setKeySet(s.api_key_set);
  };

  useEffect(() => {
    api
      .getSettings()
      .then(apply)
      .catch((e) => toast.error(e instanceof Error ? e.message : "Could not load settings"))
      .finally(() => setLoaded(true));
  }, [toast]);

  const changeProvider = (p: Provider) => {
    setProvider(p);
    // Prefill sensible defaults for the chosen provider.
    setModel(PRESETS[p].defaultModel);
    setBaseUrl(PRESETS[p].defaultBaseUrl);
    setApiKey("");
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const updated = await api.updateSettings({
        provider,
        model,
        base_url: baseUrl,
        api_key: apiKey || undefined,
      });
      apply(updated);
      setApiKey("");
      toast.success("Settings saved.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not save settings");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight">AI Settings</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Choose which engine reads your documents. Overrides the server defaults. Admin only.
        </p>
      </div>

      <Card className="p-6">
        <form onSubmit={submit} className="space-y-5">
          {/* Provider picker */}
          <div>
            <span className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Provider
            </span>
            <div className="grid gap-2 sm:grid-cols-2">
              {ORDER.map((p) => {
                const pr = PRESETS[p];
                const active = provider === p;
                return (
                  <button
                    type="button"
                    key={p}
                    onClick={() => changeProvider(p)}
                    className={`flex items-center justify-between rounded-xl border px-3 py-2.5 text-left text-sm transition-colors ${
                      active
                        ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-500/10"
                        : "border-slate-200 hover:border-slate-300 dark:border-slate-700 dark:hover:border-slate-600"
                    }`}
                  >
                    <span className="font-medium">{pr.label}</span>
                    {pr.free && <Badge tone="green">Free</Badge>}
                  </button>
                );
              })}
            </div>
            <p className="mt-2 text-xs text-slate-400">{preset.hint}</p>
          </div>

          {provider !== "offline" && (
            <>
              <Field label="Model">
                <Input
                  placeholder={preset.defaultModel}
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  required
                />
              </Field>

              {preset.needsBaseUrl && (
                <Field label="Base URL">
                  <Input
                    placeholder={preset.defaultBaseUrl}
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                  />
                </Field>
              )}

              <Field
                label="API key"
                hint={
                  preset.keyUrl ? (
                    <>
                      {keySet ? "A key is configured — leave blank to keep it. " : "No key set yet. "}
                      <a
                        href={preset.keyUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="text-indigo-600 hover:underline dark:text-indigo-400"
                      >
                        Get a free key →
                      </a>
                    </>
                  ) : keySet ? (
                    "A key is configured — leave blank to keep it."
                  ) : (
                    "No key set yet."
                  )
                }
              >
                <Input
                  type="password"
                  placeholder={keySet ? "••••••••" : "Enter API key"}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
              </Field>
            </>
          )}

          {provider === "offline" && (
            <div className="flex items-start gap-3 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-800 dark:bg-emerald-500/10 dark:text-emerald-200">
              <IconShield className="mt-0.5 shrink-0" width={18} height={18} />
              <p>
                No configuration needed. Documents are processed locally on the server — nothing is
                sent to a third-party API.
              </p>
            </div>
          )}

          <Button type="submit" loading={busy} disabled={!loaded} className="w-full">
            Save settings
          </Button>
        </form>
      </Card>
    </div>
  );
}
