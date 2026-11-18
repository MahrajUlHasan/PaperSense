import { describe, expect, it } from "vitest";
import { escapeHtml, snippetMatcher } from "./text-match";

describe("snippetMatcher", () => {
  const matches = snippetMatcher("We used the Adam optimizer [20] with β1 = 0.9, β2 = 0.98 and ε = 10−9.");

  it("marks lines that belong to the passage, ignoring case and punctuation", () => {
    expect(matches("We used the ADAM optimizer")).toBe(true);
    expect(matches("with β1 = 0.9, β2 = 0.98")).toBe(true);
  });

  it("ignores short fragments and unrelated lines", () => {
    expect(matches("Adam")).toBe(false);
    expect(matches("We trained on 8 P100 GPUs")).toBe(false);
  });
});

describe("escapeHtml", () => {
  it("escapes markup in PDF text", () => {
    expect(escapeHtml('a < b & "c"')).toBe("a &lt; b &amp; &quot;c&quot;");
  });
});
