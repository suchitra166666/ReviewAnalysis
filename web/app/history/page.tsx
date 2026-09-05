"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Button, Card, Input, Pill, Skeleton } from "@/components/ui";
import { apiGet, apiSend, type SavedComparison } from "@/lib/api";
import { formatRange, formatStamp } from "@/lib/dates";
import { liveHref, savedHref, savedTitle } from "@/lib/history";

function basisLine(row: SavedComparison): string {
  if (row.sample?.used) {
    return `${row.sample.n_a.toLocaleString()} of ${row.sample.usable_a.toLocaleString()} usable reviews for ${row.a_name}, ${row.sample.n_b.toLocaleString()} of ${row.sample.usable_b.toLocaleString()} for ${row.b_name}`;
  }
  return `${row.n_a.toLocaleString()} reviews for ${row.a_name}, ${row.n_b.toLocaleString()} for ${row.b_name}`;
}

function HistoryRow({ row }: { row: SavedComparison }) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(row.title ?? "");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const patch = useMutation({
    mutationFn: (body: { title?: string; pinned?: boolean }) => apiSend<SavedComparison>(`/history/${row.id}`, "PATCH", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["history"] }),
  });
  const remove = useMutation({
    mutationFn: () => apiSend<{ ok: boolean }>(`/history/${row.id}`, "DELETE"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["history"] }),
  });

  function saveTitle() {
    patch.mutate({ title: draft });
    setEditing(false);
  }

  return (
    <Card>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          {editing ? (
            <form
              className="flex flex-wrap items-center gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                saveTitle();
              }}
            >
              <Input
                aria-label="Comparison title"
                className="max-w-sm"
                value={draft}
                placeholder={`${row.a_name} vs ${row.b_name}`}
                autoFocus
                onChange={(e) => setDraft(e.target.value)}
              />
              <Button type="submit">Save</Button>
              <Button type="button" variant="ghost" onClick={() => setEditing(false)}>
                Cancel
              </Button>
            </form>
          ) : (
            <div className="flex flex-wrap items-center gap-2">
              <Link href={savedHref(row.id)} className="text-card text-fg underline-offset-4 hover:underline">
                {savedTitle(row)}
              </Link>
              {row.pinned ? <Pill>Pinned</Pill> : null}
              {row.sample?.used ? <Pill>Sample</Pill> : null}
              {!row.has_summary ? <Pill>No narrative yet</Pill> : null}
            </div>
          )}
          <p className="mt-1 text-caption text-fg-3">
            {formatRange(row.date_from, row.date_to)} · {basisLine(row)}
          </p>
          <p className="text-caption text-fg-3">
            Saved {formatStamp(row.created_at)}
            {row.last_viewed_at !== row.created_at ? ` · last opened ${formatStamp(row.last_viewed_at)}` : ""}
          </p>
          {row.headline ? <p className="mt-3 line-clamp-2 text-body text-fg-2">{row.headline}</p> : null}
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Link href={savedHref(row.id)} className="inline-flex h-10 items-center rounded-control bg-fg px-3 text-small text-bg">
            Open
          </Link>
          <Link href={liveHref(row)} className="inline-flex h-10 items-center rounded-control border border-border px-3 text-small text-fg">
            Open with current data
          </Link>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-border pt-3">
        <Button variant="ghost" onClick={() => patch.mutate({ pinned: !row.pinned })} disabled={patch.isPending}>
          {row.pinned ? "Unpin" : "Pin"}
        </Button>
        <Button
          variant="ghost"
          onClick={() => {
            setDraft(row.title ?? "");
            setEditing(true);
          }}
        >
          Rename
        </Button>
        {confirmDelete ? (
          <>
            <span className="text-small text-fg-2">Remove this saved result?</span>
            <Button variant="danger" onClick={() => remove.mutate()} disabled={remove.isPending}>
              Delete
            </Button>
            <Button variant="ghost" onClick={() => setConfirmDelete(false)}>
              Keep
            </Button>
          </>
        ) : (
          <Button variant="ghost" onClick={() => setConfirmDelete(true)}>
            Delete
          </Button>
        )}
        {patch.isError || remove.isError ? (
          <span className="text-small text-bad">{(patch.error ?? remove.error)?.message}</span>
        ) : null}
      </div>
    </Card>
  );
}

export default function HistoryPage() {
  const history = useQuery({
    queryKey: ["history"],
    queryFn: () => apiGet<SavedComparison[]>("/history"),
  });
  const rows = history.data ?? [];

  return (
    <main className="mx-auto max-w-page space-y-6 page-gutter py-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-section">History</h1>
          <p className="mt-1 text-caption text-fg-3">
            Every comparison you have opened is kept here with its result as it was at the time.
          </p>
        </div>
        <Link href="/" className="inline-flex h-10 shrink-0 items-center rounded-control bg-fg px-3 text-small text-bg">
          Back to dashboard
        </Link>
      </div>
      {history.isLoading ? (
        <div className="space-y-6">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : null}
      {history.isError ? (
        <Card>
          <p className="text-body">History could not be loaded. Check that the API is running.</p>
        </Card>
      ) : null}
      {history.isSuccess && rows.length === 0 ? (
        <Card>
          <p className="text-body">No saved comparisons yet. Open the dashboard for two companies and the result will appear here.</p>
          <Link href="/" className="mt-4 inline-flex h-10 items-center text-small text-fg-2">
            Go to the dashboard
          </Link>
        </Card>
      ) : null}
      {rows.map((row) => (
        <HistoryRow key={row.id} row={row} />
      ))}
    </main>
  );
}
