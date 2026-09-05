"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";
import { PipelineFlow } from "@/components/PipelineFlow";
import { Drawer, RunPipelineModal } from "@/components/RunPipelineModal";
import { Button, Card } from "@/components/ui";
import { apiGet, apiSend, type Company } from "@/lib/api";
import { defaultState, parseState } from "@/lib/url-state";

export default function JobsPage() {
  const [runOpen, setRunOpen] = useState(false);
  const state = useMemo(() => (typeof window === "undefined" ? defaultState() : parseState(window.location.search)), []);
  const jobs = useQuery({
    queryKey: ["jobs"],
    queryFn: () => apiGet<any[]>("/jobs"),
    refetchInterval: 2000,
  });
  const companies = useQuery({
    queryKey: ["companies"],
    queryFn: () => apiGet<Company[]>("/companies"),
  });
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<{ worker: string }>("/health"),
    refetchInterval: 5000,
  });

  return (
    <main className="mx-auto max-w-page space-y-6 page-gutter py-8">
      <div className="flex items-center justify-between">
        <h1 className="text-section">Jobs</h1>
        <div className="flex items-center gap-3">
          <Button onClick={() => setRunOpen(true)}>Run pipeline</Button>
          <Link href="/" className="text-small text-fg-2">
            Back to dashboard
          </Link>
        </div>
      </div>
      {health.data && health.data.worker !== "ok" ? (
        <Card>
          <p className="text-body">
            The worker is {health.data.worker}. Queued jobs will not start until you run <code>rap worker</code> or{" "}
            <code>docker compose up</code>.
          </p>
        </Card>
      ) : null}
      {(jobs.data ?? []).length === 0 ? (
        <Card>
          <p className="text-body">No jobs yet. Run the pipeline to scrape and analyse the selected companies.</p>
        </Card>
      ) : null}
      {(jobs.data ?? []).map((job) => (
        <Card key={job.id}>
          <div className="flex items-center justify-between">
            <p className="text-card">
              #{job.id} {job.kind} · {job.status}
            </p>
            {job.status === "running" || job.status === "queued" ? (
              <Button variant="ghost" onClick={() => apiSend(`/jobs/${job.id}/cancel`, "POST")}>
                Cancel
              </Button>
            ) : null}
          </div>
          <p className="text-caption text-fg-3">
            est ${job.est_cost_usd?.toFixed(2)} · actual ${job.actual_cost_usd?.toFixed(2)}
            {job.progress?.rows_per_minute != null ? ` · ${job.progress.rows_per_minute} rows/min` : ""}
            {" · "}
            {job.progress?.stage}
          </p>
          <div className="mt-4">
            <PipelineFlow job={job} />
          </div>
          <div className="mt-4 h-2 rounded-control bg-wash">
            <div
              className="h-full bg-fg"
              style={{
                width: `${job.progress?.total ? (100 * (job.progress.done || 0)) / job.progress.total : 0}%`,
              }}
            />
          </div>
          <pre className="mt-3 max-h-48 overflow-auto text-caption text-fg-2">{job.log}</pre>
        </Card>
      ))}
      {runOpen ? (
        <Drawer title="Run pipeline" onClose={() => setRunOpen(false)}>
          <RunPipelineModal state={state} companies={companies.data ?? []} onClose={() => setRunOpen(false)} />
        </Drawer>
      ) : null}
    </main>
  );
}
