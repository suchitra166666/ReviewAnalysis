import { describe, expect, it } from "vitest";
import { describeDelta, formatDelta, formatPct, maskKey } from "./delta";

describe("formatDelta", () => {
  it("colours a lower negative rate as good", () => {
    const d = formatDelta(-0.04, "%", true);
    expect(d.cls).toBe("text-good");
    expect(d.text).toBe("-4.0 pts");
  });
  it("colours a higher negative rate as bad", () => {
    const d = formatDelta(0.04, "%", true);
    expect(d.cls).toBe("text-bad");
  });
  it("treats point differences as fractions like shares", () => {
    // net sentiment −53.3% vs −12.3% is a 41-point gap, not 0.4
    expect(formatDelta(-0.41, "pts").text).toBe("-41.0 pts");
  });
});

describe("describeDelta", () => {
  it("reads A minus B in words", () => {
    const d = describeDelta(-43, "", "Careem", "Deliveroo");
    expect(d.text).toBe("Careem is 43 lower");
    expect(d.vs).toBe("than Deliveroo");
    expect(d.cls).toBe("text-bad");
  });
  it("uses the metric unit and judges colour from A's side", () => {
    expect(describeDelta(0.226, "%", "Careem", "Deliveroo", true).text).toBe("Careem is 22.6 pts higher");
    expect(describeDelta(0.226, "%", "Careem", "Deliveroo", true).cls).toBe("text-bad");
    expect(describeDelta(-0.8, "★", "Careem", "Deliveroo").text).toBe("Careem is 0.8★ lower");
  });
  it("handles ties and missing values", () => {
    expect(describeDelta(0, "%", "A", "B").text).toBe("Same for both");
    expect(describeDelta(null, "%", "A", "B").text).toBe("Not comparable");
  });
});

describe("formatPct", () => {
  it("uses one decimal", () => {
    expect(formatPct(0.184)).toBe("18.4%");
  });
});

describe("maskKey", () => {
  it("never shows the full key", () => {
    expect(maskKey("9xyz")).toBe("••••9xyz");
    expect(maskKey(null)).toBe("No key");
  });
});
