import { describe, expect, it } from "vitest";
import { boxToRect, fitZoomForBox, groupBoxesByPage } from "./geometry";

describe("boxToRect", () => {
  it("scales a box from PDF points to pixels on a US Letter page", () => {
    expect(boxToRect({ page: 1, l: 72, t: 100, r: 540, b: 150 }, 1.5, 0)).toEqual({
      left: 108,
      top: 150,
      width: 702,
      height: 75,
    });
  });

  it("pads the box and copes with swapped edges", () => {
    expect(boxToRect({ page: 1, l: 100, t: 60, r: 50, b: 40 }, 2, 2)).toEqual({
      left: 96,
      top: 76,
      width: 108,
      height: 48,
    });
  });
});

describe("groupBoxesByPage", () => {
  it("groups boxes per page, pages in order", () => {
    const a = { page: 2, l: 0, t: 0, r: 1, b: 1 };
    const b = { page: 1, l: 0, t: 0, r: 1, b: 1 };
    const c = { page: 2, l: 0, t: 2, r: 1, b: 3 };
    expect(groupBoxesByPage([a, b, c])).toEqual([
      { page: 1, boxes: [b] },
      { page: 2, boxes: [a, c] },
    ]);
  });
});

describe("fitZoomForBox", () => {
  it("zooms a narrow figure to about 90% of the width, at most 3x", () => {
    expect(fitZoomForBox({ page: 1, l: 200, t: 0, r: 400, b: 10 }, 600)).toBeCloseTo(2.7);
    expect(fitZoomForBox({ page: 1, l: 0, t: 0, r: 50, b: 10 }, 600)).toBe(3);
    expect(fitZoomForBox({ page: 1, l: 0, t: 0, r: 600, b: 10 }, 600)).toBe(1);
  });
});
