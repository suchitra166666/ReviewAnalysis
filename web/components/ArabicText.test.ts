import { describe, expect, it } from "vitest";
import { hasArabic } from "./ArabicText";

describe("ArabicText helpers", () => {
  it("detects Arabic characters", () => {
    expect(hasArabic("وصلت متأخر")).toBe(true);
    expect(hasArabic("arrived late")).toBe(false);
  });
});
