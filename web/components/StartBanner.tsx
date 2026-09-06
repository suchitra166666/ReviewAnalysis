"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Button, Input } from "@/components/ui";
import { apiGet, apiSend } from "@/lib/api";
import { validateProviderKey } from "@/lib/settings-validate";

type Presence = { visited: number; online: number; has_own_key?: boolean };

export function StartBanner() {
  const qc = useQueryClient();
  const presence = useQuery({
    queryKey: ["presence"],
    queryFn: () => apiSend<Presence>("/presence", "POST"),
    refetchInterval: 20000,
  });
  const providers = useQuery({
    queryKey: ["providers"],
    queryFn: () => apiGet<Array<{ slug: string; display_name: string; has_key: boolean }>>("/providers"),
  });
  const [open, setOpen] = useState(false);
  const [slug, setSlug] = useState("openai");
  const [key, setKey] = useState("");
  const [status, setStatus] = useState("");
  const visited = presence.data?.visited ?? 0;
  const online = presence.data?.online ?? 0;
  const ready = Boolean(presence.data?.has_own_key);

  async function save() {
    const invalid = validateProviderKey(key);
    if (invalid) {
      setStatus(invalid);
      return;
    }
    try {
      await apiSend(`/providers/${slug}`, "PUT", { api_key: key });
      setKey("");
      setStatus("Saved. You can run a report now.");
      setOpen(false);
      presence.refetch();
      qc.invalidateQueries({ queryKey: ["providers"] });
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Could not save the key.");
    }
  }

  return (
    <div className="border-b border-border bg-wash">
      <div className="mx-auto flex max-w-page flex-wrap items-center justify-between gap-3 page-gutter py-2.5">
        <div className="min-w-0">
          {ready ? (
            <p className="text-small text-fg-2">Your key stays on this browser. It is not the site owner&apos;s key.</p>
          ) : (
            <p className="text-small text-fg">
              Add your OpenAI or DeepSeek key to get started.{" "}
              <button type="button" className="underline" onClick={() => setOpen((v) => !v)}>
                Add a key
              </button>
              {" · "}
              <Link href="/settings" className="underline">
                Settings
              </Link>
            </p>
          )}
          {status ? <p className="mt-1 text-caption text-fg-2">{status}</p> : null}
        </div>
        <p className="shrink-0 text-caption text-fg-3">
          <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-pill bg-good" aria-hidden />
          {online.toLocaleString()} online · {visited.toLocaleString()} visited
        </p>
      </div>
      {open && !ready ? (
        <div className="mx-auto flex max-w-page flex-wrap items-end gap-2 page-gutter pb-3">
          <label className="text-caption text-fg-3">
            Provider
            <select
              className="mt-1 block h-10 rounded-control border border-border bg-bg px-2 text-small"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
            >
              {(providers.data ?? [{ slug: "openai", display_name: "OpenAI" }, { slug: "deepseek", display_name: "DeepSeek" }]).map((p) => (
                <option key={p.slug} value={p.slug}>
                  {p.display_name}
                </option>
              ))}
            </select>
          </label>
          <Input
            type="password"
            className="max-w-sm"
            placeholder="Paste your API key"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            autoComplete="off"
          />
          <Button onClick={save}>Save key</Button>
        </div>
      ) : null}
    </div>
  );
}
