import { readFileSync } from "fs";
import { describe, expect, it } from "vitest";

const page = readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");
const dash = readFileSync(new URL("../components/dashboard.tsx", import.meta.url), "utf8");

describe("MetricLabel usage", () => {
  it("does not render glossary metric names as raw text in KPI cards", () => {
    expect(dash).toContain("<MetricLabel");
    expect(`${page}\n${dash}`).not.toMatch(/Neg %/);
  });
});
