"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Button, Card, Input, Pill } from "@/components/ui";
import { apiGet, apiSend, type Company } from "@/lib/api";
import { maskKey } from "@/lib/delta";

const TABS = [
  "providers",
  "models",
  "costs",
  "scraping",
  "extraction",
  "aggregation",
  "companies",
  "display",
  "danger",
] as const;

export default function SettingsPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("providers");
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => apiGet<any[]>("/settings") });
  const providers = useQuery({ queryKey: ["providers"], queryFn: () => apiGet<any[]>("/providers") });
  const companies = useQuery({ queryKey: ["companies"], queryFn: () => apiGet<Company[]>("/companies") });
  const [toast, setToast] = useState("");

  async function save(key: string, value: unknown) {
    await apiSend("/settings", "PUT", { values: { [key]: value } });
    setToast("Saved");
    settings.refetch();
  }

  const group = (name: string) => (settings.data ?? []).filter((s) => s.group === name);

  return (
    <main className="mx-auto max-w-page space-y-6 page-gutter py-8">
      <div className="flex items-center justify-between">
        <h1 className="text-section">Settings</h1>
        <Link href="/" className="text-small text-fg-2">
          Back to dashboard
        </Link>
      </div>
      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            className={`h-10 rounded-control px-3 text-small ${tab === t ? "bg-fg text-bg" : "text-fg-2"}`}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>
      {toast ? <p className="text-caption text-fg-2">{toast}</p> : null}

      {tab === "providers" && (
        <div className="space-y-4">
          {(providers.data ?? []).map((p) => (
            <ProviderCard key={p.slug} provider={p} onDone={() => providers.refetch()} />
          ))}
        </div>
      )}
      {["models", "costs", "scraping", "extraction", "aggregation", "display"].includes(tab) && (
        <div className="space-y-4">
          {group(tab === "models" ? "models" : tab).map((s) => (
            <Card key={s.key}>
              <p className="text-card">{s.label}</p>
              <p className="text-small text-fg-2">{s.description}</p>
              <p className="text-caption text-fg-3">Default: {JSON.stringify(s.default)}</p>
              {s.value_type === "bool" ? (
                <label className="mt-2 inline-flex h-10 items-center gap-2 text-small">
                  <input type="checkbox" defaultChecked={Boolean(s.value)} onChange={(e) => save(s.key, e.target.checked)} />
                  Current
                </label>
              ) : s.value_type === "json" ? (
                <textarea
                  className="mt-2 w-full rounded-control border border-border p-2 text-small"
                  defaultValue={JSON.stringify(s.value, null, 2)}
                  onBlur={(e) => save(s.key, JSON.parse(e.target.value))}
                />
              ) : (
                <Input className="mt-2" defaultValue={s.value ?? ""} onBlur={(e) => save(s.key, e.target.value)} />
              )}
              <Button variant="ghost" className="mt-2" onClick={() => save(s.key, s.default)}>
                Reset to default
              </Button>
            </Card>
          ))}
        </div>
      )}
      {tab === "companies" && (
        <div className="space-y-3">
          {(companies.data ?? []).map((c) => (
            <Card key={c.slug}>
              <p className="text-card">{c.display_name}</p>
              <p className="text-caption text-fg-3">
                {c.slug} · {c.appstore_id} · {c.play_package}
              </p>
            </Card>
          ))}
          <AddCompany onDone={() => companies.refetch()} />
        </div>
      )}
      {tab === "danger" && (
        <Card>
          <Button
            variant="danger"
            onClick={async () => {
              await apiSend("/settings/reset", "POST");
              setToast("Saved");
              settings.refetch();
            }}
          >
            Reset settings to defaults
          </Button>
          <Link href="/setup" className="ml-3 text-small">
            Re-open setup
          </Link>
        </Card>
      )}
    </main>
  );
}

function verifyLabel(status: string | null | undefined) {
  if (status === "ok") return "Verified";
  if (status === "failed") return "Failed";
  return "Untested";
}

function ProviderCard({ provider, onDone }: { provider: any; onDone: () => void }) {
  const [key, setKey] = useState("");
  const [status, setStatus] = useState(provider.last_verify_status);
  const [verifiedAt, setVerifiedAt] = useState(provider.last_verified_at as string | null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  async function saveKey() {
    if (!key.trim()) {
      setError("Paste a key first.");
      return;
    }
    setBusy(true);
    setError("");
    setNote("");
    try {
      await apiSend(`/providers/${provider.slug}`, "PUT", {
        api_key: key,
        base_url: provider.base_url,
        display_name: provider.display_name,
        is_openai_compatible: provider.is_openai_compatible,
        supports_batch: provider.supports_batch,
        supports_structured_outputs: provider.supports_structured_outputs,
        disable_thinking: provider.disable_thinking,
      });
      setKey("");
      setStatus(null);
      setVerifiedAt(null);
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function test() {
    setBusy(true);
    setError("");
    setNote("");
    try {
      const out = await apiSend<{ status: string; error?: string | null; note?: string | null }>(
        `/providers/${provider.slug}/test`,
        "POST",
      );
      setStatus(out.status);
      setVerifiedAt(new Date().toISOString());
      if (out.status !== "ok") setError(out.error || "Connection failed.");
      if (out.note) setNote(out.note);
      onDone();
    } catch (err) {
      setStatus("failed");
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <div className="flex items-center justify-between">
        <h2 className="text-card">{provider.display_name}</h2>
        <Pill tone={status === "ok" ? "good" : status === "failed" ? "bad" : "muted"}>{verifyLabel(status)}</Pill>
      </div>
      <p className="text-caption text-fg-3">{provider.has_key ? maskKey(provider.key_last4) : "No key"}</p>
      {verifiedAt ? (
        <p className="text-caption text-fg-3">Last tested {verifiedAt.slice(0, 16).replace("T", " ")} UTC</p>
      ) : null}
      <label className="mt-3 block text-caption text-fg-3">
        API key
        <Input
          className="mt-1"
          type="password"
          autoComplete="off"
          placeholder="Paste key"
          value={key}
          onChange={(e) => setKey(e.target.value)}
        />
      </label>
      <div className="mt-2 flex gap-2">
        <Button onClick={saveKey} disabled={busy}>
          {provider.has_key ? "Replace key" : "Save key"}
        </Button>
        <Button variant="ghost" onClick={test} disabled={busy || !provider.has_key}>
          {busy ? "Testing" : "Test connection"}
        </Button>
      </div>
      {error ? <p className="mt-2 text-small text-bad">{error}</p> : null}
      {note ? <p className="mt-2 text-small text-fg-2">{note}</p> : null}
    </Card>
  );
}

function AddCompany({ onDone }: { onDone: () => void }) {
  const [name, setName] = useState("");
  const [hits, setHits] = useState<any>(null);
  return (
    <Card>
      <h3 className="text-card">Add company</h3>
      <Input className="mt-2" value={name} onChange={(e) => setName(e.target.value)} placeholder="Display name" />
      <Button
        className="mt-2"
        variant="ghost"
        onClick={async () => setHits(await apiSend(`/companies/lookup?name=${encodeURIComponent(name)}`, "POST"))}
      >
        Look up IDs
      </Button>
      {hits ? <pre className="mt-2 text-caption">{JSON.stringify(hits, null, 2)}</pre> : null}
      <Button
        className="mt-2"
        onClick={async () => {
          const slug = name.toLowerCase().replace(/\s+/g, "-");
          await apiSend("/companies", "POST", {
            slug,
            display_name: name,
            aliases: [name.toLowerCase()],
          });
          onDone();
        }}
      >
        Add company
      </Button>
    </Card>
  );
}
