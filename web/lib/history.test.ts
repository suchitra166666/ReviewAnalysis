import { describe, expect, it } from "vitest";
import { liveHref, parseSavedId, savedHref, savedTitle } from "./history";

describe("history links", () => {
  it("reads a positive integer saved id and ignores junk", () => {
    expect(parseSavedId("?saved=12")).toBe(12);
    expect(parseSavedId("?a=one&b=two")).toBeNull();
    expect(parseSavedId("?saved=abc")).toBeNull();
    expect(parseSavedId("?saved=0")).toBeNull();
    expect(parseSavedId("?saved=-3")).toBeNull();
  });

  it("builds a live dashboard url from a saved row", () => {
    expect(liveHref({ a: "one", b: "two", date_from: "2026-01-01", date_to: "2026-03-31" })).toBe(
      "/?a=one&b=two&from=2026-01-01&to=2026-03-31",
    );
    expect(savedHref(7)).toBe("/?saved=7");
  });

  it("falls back to A vs B when there is no custom title", () => {
    expect(savedTitle({ title: null, a_name: "Careem", b_name: "Deliveroo" })).toBe("Careem vs Deliveroo");
    expect(savedTitle({ title: "  ", a_name: "Careem", b_name: "Deliveroo" })).toBe("Careem vs Deliveroo");
    expect(savedTitle({ title: "Q3 review", a_name: "Careem", b_name: "Deliveroo" })).toBe("Q3 review");
  });
});
