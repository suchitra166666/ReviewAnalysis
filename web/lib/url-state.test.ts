import { describe, expect, it } from "vitest";
import { compareQuery, parseState, serializeState } from "./url-state";

describe("url state", () => {
  it("round-trips companies and dates only", () => {
    const state = parseState("?a=one&b=two&from=2026-01-01&to=2026-03-31");
    expect(state.a).toBe("one");
    expect(state.b).toBe("two");
    expect(state.dateFrom).toBe("2026-01-01");
    expect(state.dateTo).toBe("2026-03-31");
    const encoded = serializeState(state);
    expect(encoded).toBe("?a=one&b=two&from=2026-01-01&to=2026-03-31");
    expect(encoded).not.toContain("view");
    expect(encoded).not.toContain("weighted");
    expect(encoded).not.toContain("exclude_flagged");
    expect(encoded).not.toContain("preset");
  });

  it("ignores removed view and filter params", () => {
    const state = parseState("?a=one&b=two&view=analyst&weighted=0&exclude_flagged=0&preset=30d");
    expect(state).not.toHaveProperty("view");
    expect(state).not.toHaveProperty("weighted");
    const q = compareQuery({ ...state, dateFrom: "2026-01-01", dateTo: "2026-03-31" });
    expect(q).toContain("exclude_flagged=true");
    expect(q).toContain("weighted=true");
    expect(q).not.toContain("view");
  });
});
