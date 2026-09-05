export const PIPELINE_STAGES = [
  "scrape",
  "extract_a",
  "extract_b",
  "reconcile",
  "translate",
  "flags",
  "summarize",
] as const;

export type PipelineStage = (typeof PIPELINE_STAGES)[number];

export type StepState = "done" | "working" | "queued" | "waiting" | "failed";

export const STAGE_LABELS: Record<string, string> = {
  scrape: "Scrape",
  extract_a: "Extract A",
  extract_b: "Extract B",
  reconcile: "Reconcile",
  translate: "Translate",
  flags: "Flags",
  summarize: "Summarise",
};

export function stagesForJob(job?: { params?: { stages?: string[] } } | null): string[] {
  const listed = job?.params?.stages?.filter(Boolean);
  return listed?.length ? listed : [...PIPELINE_STAGES];
}

export function stepStates(
  stages: string[],
  job?: { status?: string; progress?: { stage?: string; done?: number } } | null,
): StepState[] {
  if (!job) return stages.map(() => "waiting");
  const current = job.progress?.stage ?? "";
  if (job.status === "ok" || current === "done") return stages.map(() => "done");
  const failed = job.status === "failed";
  const queued = job.status === "queued" || current === "queued" || current === "";
  if (current === "extract") {
    return stages.map((stage) => {
      if (stage === "scrape") return "done";
      if (stage === "extract_a" || stage === "extract_b") return failed ? "failed" : "working";
      return "waiting";
    });
  }
  if (current === "translate_flags") {
    return stages.map((stage) => {
      if (["scrape", "extract_a", "extract_b", "reconcile"].includes(stage)) return "done";
      if (stage === "translate" || stage === "flags") return failed ? "failed" : "working";
      return "waiting";
    });
  }
  const idx = stages.indexOf(current);
  return stages.map((_, i) => {
    if (queued) return i === 0 ? "queued" : "waiting";
    if (idx < 0) return i < (job.progress?.done ?? 0) ? "done" : "waiting";
    if (i < idx) return "done";
    if (i === idx) return failed ? "failed" : "working";
    return "waiting";
  });
}
