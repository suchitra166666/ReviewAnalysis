import { describe, expect, it } from "vitest";
import { validateCostCap, validateProviderKey } from "./settings-validate";

describe("settings form validation", () => {
  it("rejects an empty key", () => {
    expect(validateProviderKey("")).toBeTruthy();
  });
  it("accepts a long key", () => {
    expect(validateProviderKey("sk-test-12345678")).toBeNull();
  });
  it("rejects a zero cost cap", () => {
    expect(validateCostCap(0)).toBeTruthy();
  });
});
