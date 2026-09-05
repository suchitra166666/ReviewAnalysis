"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, Card, Input, Pill } from "@/components/ui";
import { apiGet, apiSend, type Company } from "@/lib/api";
import { maskKey } from "@/lib/delta";
import { validateProviderKey } from "@/lib/settings-validate";

export default function SetupPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [slug, setSlug] = useState("openai");
  const [key, setKey] = useState("");
  const [status, setStatus] = useState("");
  const providers = useQuery({ queryKey: ["providers"], queryFn: () => apiGet<any[]>("/providers") });
  const companies = useQuery({ queryKey: ["companies"], queryFn: () => apiGet<Company[]>("/companies") });
  const settings = useQuery({ queryKey: ["settings"], queryFn: () => apiGet<any[]>("/settings") });

  async function saveKey() {
    const invalid = validateProviderKey(key);
    if (invalid) {
      setStatus(invalid);
      return;
    }
    await apiSend(`/providers/${slug}`, "PUT", { api_key: key });
    setKey("");
    setStatus("Saved");
    providers.refetch();
  }
  async function test() {
    try {
      const out = await apiSend<{ status: string; error?: string | null; note?: string | null }>(
        `/providers/${slug}/test`,
        "POST",
      );
      setStatus(out.status === "ok" ? "ok" : out.error || out.status);
      providers.refetch();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : String(err));
    }
  }
  async function saveCap(value: number) {
    await apiSend("/settings", "PUT", { values: { "costs.max_run_cost_usd": value } });
    settings.refetch();
  }

  return (
    <main className="mx-auto max-w-page space-y-6 page-gutter py-10">
      <h1 className="text-section">First-run setup</h1>
      <p className="text-body text-fg-2">Step {step} of 5. You cannot skip this until one provider is verified and two companies exist.</p>
      {step === 1 && (
        <Card>
          <h2 className="text-card">Paste an API key</h2>
          <div className="mt-3 space-y-3">
            <select className="h-10 rounded-control border border-border px-2" value={slug} onChange={(e) => setSlug(e.target.value)}>
              {(providers.data ?? []).map((p) => (
                <option key={p.slug} value={p.slug}>
                  {p.display_name} {p.has_key ? maskKey(p.key_last4) : ""}
                </option>
              ))}
            </select>
            <Input type="password" placeholder="API key" value={key} onChange={(e) => setKey(e.target.value)} />
            <div className="flex gap-2">
              <Button onClick={saveKey}>Save changes</Button>
              <Button variant="ghost" onClick={test}>
                Test connection
              </Button>
            </div>
            {status ? <Pill tone={status === "ok" ? "good" : "muted"}>{status}</Pill> : null}
          </div>
        </Card>
      )}
      {step === 2 && (
        <Card>
          <h2 className="text-card">Model roles</h2>
          <p className="text-body text-fg-2">Defaults are already set. You can change them later in Settings.</p>
        </Card>
      )}
      {step === 3 && (
        <Card>
          <h2 className="text-card">Cost cap</h2>
          <Input
            type="number"
            defaultValue={settings.data?.find((s) => s.key === "costs.max_run_cost_usd")?.value ?? 25}
            onBlur={(e) => saveCap(Number(e.target.value))}
          />
        </Card>
      )}
      {step === 4 && (
        <Card>
          <h2 className="text-card">Companies</h2>
          <p className="text-body">{companies.data?.length ?? 0} companies seeded. Add more in Settings if needed.</p>
          <ul className="mt-2 text-small">
            {(companies.data ?? []).map((c) => (
              <li key={c.slug}>{c.display_name}</li>
            ))}
          </ul>
        </Card>
      )}
      {step === 5 && (
        <Card>
          <h2 className="text-card">Run first scrape</h2>
          <Button
            onClick={async () => {
              const slugs = (companies.data ?? []).slice(0, 2).map((c) => c.slug);
              await apiSend("/jobs", "POST", { kind: "scrape", params: { slugs, stores: ["appstore", "play"] }, confirm: true });
              router.push("/");
            }}
          >
            Run first scrape
          </Button>
        </Card>
      )}
      <div className="flex gap-2">
        {step > 1 ? (
          <Button variant="ghost" onClick={() => setStep(step - 1)}>
            Back
          </Button>
        ) : null}
        {step < 5 ? (
          <Button
            onClick={() => {
              if (step === 1 && !(providers.data ?? []).some((p) => p.last_verify_status === "ok")) return;
              if (step === 4 && (companies.data ?? []).length < 2) return;
              setStep(step + 1);
            }}
          >
            Continue
          </Button>
        ) : (
          <Button variant="ghost" onClick={() => router.push("/")}>
            Go to dashboard
          </Button>
        )}
      </div>
    </main>
  );
}
