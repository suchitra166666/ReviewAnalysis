"use client";

import { Check } from "lucide-react";
import { STAGE_LABELS, stagesForJob, stepStates, type StepState } from "@/lib/pipeline";

function StepMark({ index, state }: { index: number; state: StepState }) {
  if (state === "done") {
    return (
      <span className="inline-flex h-8 w-8 items-center justify-center rounded-pill border border-good text-good" aria-hidden>
        <Check size={16} strokeWidth={1.5} />
      </span>
    );
  }
  const ring =
    state === "working"
      ? "border-fg text-fg"
      : state === "failed"
        ? "border-bad text-bad"
        : "border-border text-fg-3";
  return (
    <span className={`inline-flex h-8 w-8 items-center justify-center rounded-pill border text-small ${ring}`}>
      {index + 1}
    </span>
  );
}

function stepCaption(state: StepState): string {
  if (state === "done") return "Done";
  if (state === "working") return "Working";
  if (state === "queued") return "Queued";
  if (state === "failed") return "Failed";
  return "Waiting";
}

export function PipelineFlow({
  job,
}: {
  job?: { status?: string; params?: { stages?: string[] }; progress?: { stage?: string; done?: number } } | null;
}) {
  const stages = stagesForJob(job);
  const states = stepStates(stages, job);
  return (
    <ol className="flex flex-wrap items-start gap-y-4" aria-label="Pipeline stages">
      {stages.map((stage, i) => {
        const state = states[i];
        const last = i === stages.length - 1;
        return (
          <li key={stage} className="flex min-w-[96px] flex-1 items-start">
            <div className="flex min-w-0 flex-col items-center text-center">
              <StepMark index={i} state={state} />
              <p className="mt-2 text-caption text-fg">{STAGE_LABELS[stage] ?? stage.replace(/_/g, " ")}</p>
              <p
                className={`text-caption ${
                  state === "working" ? "text-fg" : state === "failed" ? "text-bad" : state === "done" ? "text-good" : "text-fg-3"
                }`}
              >
                {stepCaption(state)}
              </p>
            </div>
            {last ? null : <span className="mt-4 h-px min-w-4 flex-1 bg-divider" aria-hidden />}
          </li>
        );
      })}
    </ol>
  );
}
