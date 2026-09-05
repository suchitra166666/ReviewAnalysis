import { describe, expect, it } from "vitest";
import { PIPELINE_STAGES, stepStates } from "./pipeline";

describe("pipeline step states", () => {
  it("marks earlier stages done and the current one working", () => {
    const states = stepStates([...PIPELINE_STAGES], { status: "running", progress: { stage: "extract_b", done: 2 } });
    expect(states.slice(0, 3)).toEqual(["done", "done", "working"]);
    expect(states[3]).toBe("waiting");
  });

  it("ticks every stage when the job finished", () => {
    const states = stepStates([...PIPELINE_STAGES], { status: "ok", progress: { stage: "done", done: 7 } });
    expect(states.every((s) => s === "done")).toBe(true);
  });

  it("marks both extract roles working during concurrent extract", () => {
    const states = stepStates([...PIPELINE_STAGES], { status: "running", progress: { stage: "extract" } });
    expect(states.slice(0, 4)).toEqual(["done", "working", "working", "waiting"]);
  });

  it("shows queued on the first step before the worker starts", () => {
    const states = stepStates([...PIPELINE_STAGES], { status: "queued", progress: { stage: "queued", done: 0 } });
    expect(states[0]).toBe("queued");
    expect(states[1]).toBe("waiting");
  });
});
