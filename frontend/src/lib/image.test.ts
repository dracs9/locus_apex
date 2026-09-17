import { describe, expect, it } from "vitest";

import { fitSize, hostOf, isSafeUrl } from "./image";

describe("image helpers", () => {
  it("scales the longer side down to the limit and keeps the ratio", () => {
    expect(fitSize(4000, 3000)).toEqual({ width: 1600, height: 1200 });
    expect(fitSize(1080, 1920)).toEqual({ width: 900, height: 1600 });
  });

  it("never scales small images up", () => {
    expect(fitSize(800, 600)).toEqual({ width: 800, height: 600 });
  });

  it("shows hostnames and allows only http(s) links", () => {
    expect(hostOf("https://www.github.com/me/project")).toBe("github.com");
    expect(isSafeUrl("https://example.com")).toBe(true);
    expect(isSafeUrl("javascript:alert(1)")).toBe(false);
    expect(isSafeUrl(null)).toBe(false);
  });
});
