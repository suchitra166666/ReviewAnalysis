"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Button, Input } from "@/components/ui";
import { apiSend, type SavedComparison } from "@/lib/api";
import { formatRange } from "@/lib/dates";
import { savedHref } from "@/lib/history";
import type { DashState } from "@/lib/url-state";

export function defaultReportTitle(nameA: string, nameB: string, state: DashState): string {
  return `${nameA} vs ${nameB} · ${formatRange(state.dateFrom, state.dateTo)}`;
}

export function SaveReportModal({
  state,
  nameA,
  nameB,
  existingTitle,
  onSaved,
  onClose,
}: {
  state: DashState;
  nameA: string;
  nameB: string;
  /** Title of the saved copy this view came from, if any. */
  existingTitle?: string | null;
  onSaved: (row: SavedComparison) => void;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [title, setTitle] = useState(existingTitle ?? defaultReportTitle(nameA, nameB, state));
  const save = useMutation({
    mutationFn: () =>
      apiSend<SavedComparison>("/history/save", "POST", {
        a: state.a,
        b: state.b,
        date_from: state.dateFrom || null,
        date_to: state.dateTo || null,
        title: title.trim() || null,
        pinned: true,
      }),
    onSuccess: (row) => {
      qc.invalidateQueries({ queryKey: ["history"] });
      qc.invalidateQueries({ queryKey: ["saved", row.id] });
      onSaved(row);
    },
  });

  if (save.isSuccess) {
    const row = save.data;
    return (
      <div className="space-y-4">
        <p className="text-body">Saved. This report is kept exactly as it is now and is pinned at the top of History.</p>
        <p className="text-caption text-fg-3">
          {row.title ?? `${row.a_name} vs ${row.b_name} · ${formatRange(row.date_from, row.date_to)}`}
          {row.has_summary ? "" : " · narrative not generated yet, so it was saved without one"}
        </p>
        <div className="flex flex-wrap gap-2">
          <Link href={savedHref(row.id)} className="inline-flex h-10 items-center rounded-control bg-fg px-3 text-small text-bg" onClick={onClose}>
            Open saved copy
          </Link>
          <Link href="/history" className="inline-flex h-10 items-center rounded-control border border-border px-3 text-small text-fg">
            Go to History
          </Link>
          <Button variant="ghost" onClick={onClose}>
            Done
          </Button>
        </div>
        <p className="text-caption text-fg-3">
          Share it with this link: {typeof window !== "undefined" ? `${window.location.origin}${savedHref(row.id)}` : savedHref(row.id)}
        </p>
      </div>
    );
  }

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
    >
      <p className="text-body">
        Keeps a copy of everything on this page, numbers and narrative, as it is right now. New reviews or later runs will not change
        it.
      </p>
      <label className="block text-caption text-fg-3">
        Report name
        <Input className="mt-1" value={title} onChange={(e) => setTitle(e.target.value)} autoFocus aria-label="Report name" />
      </label>
      <p className="text-caption text-fg-3">
        {nameA} vs {nameB} · {formatRange(state.dateFrom, state.dateTo)}
      </p>
      {save.isError ? <p className="text-small text-bad">{save.error.message}</p> : null}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save report"}
        </Button>
        <Button type="button" variant="ghost" onClick={onClose}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
