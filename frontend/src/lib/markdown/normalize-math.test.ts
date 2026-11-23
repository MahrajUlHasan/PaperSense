import { describe, expect, it } from "vitest";
import { normalizeMath } from "./normalize-math";

describe("normalizeMath", () => {
  it("turns \\( \\) into inline dollars", () => {
    expect(normalizeMath("a \\(x^2\\) b")).toBe("a $x^2$ b");
  });

  it("turns \\[ \\] into a display block", () => {
    expect(normalizeMath("\\[E=mc^2\\]")).toBe("\n$$\nE=mc^2\n$$\n");
  });

  it("puts display math on its own lines", () => {
    expect(normalizeMath("Rate: $$a+b$$ [1]")).toBe("Rate: \n$$\na+b\n$$\n [1]");
  });

  it("leaves code alone", () => {
    expect(normalizeMath("`\\(x\\)` and\n```\n$$y$$\n```")).toBe("`\\(x\\)` and\n```\n$$y$$\n```");
  });
});
