import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Markdown } from "@/components/markdown/Markdown";
import { parseCitationNumbers } from "./remark-citations";

function chips(markdown: string, max?: number): (string | null)[] {
  render(
    <Markdown maxCitation={max} renderCitation={(n) => <span data-testid="chip">{n}</span>}>
      {markdown}
    </Markdown>,
  );
  return screen.queryAllByTestId("chip").map((el) => el.textContent);
}

describe("citation chips", () => {
  it("collapses repeats next to each other", () => {
    expect(chips("Adam was used [1][1].")).toEqual(["1"]);
  });

  it("expands lists and ranges", () => {
    expect(chips("See [1, 3] and [4-5].")).toEqual(["1", "3", "4", "5"]);
  });

  it("never touches math or code", () => {
    expect(chips("Inline $x_{[1]}$ and `a[2]` stay as they are.")).toEqual([]);
  });

  it("drops numbers beyond the sources", () => {
    expect(chips("A claim [7].", 3)).toEqual([]);
  });

  it("parses numbers", () => {
    expect(parseCitationNumbers("1, 2-4")).toEqual([1, 2, 3, 4]);
  });
});
