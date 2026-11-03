import { describe, expect, it } from "vitest";
import { newId } from "./ids";

describe("newId", () => {
  it("makes ids the backend accepts", () => {
    const id = newId("ws");
    expect(id).toMatch(/^[A-Za-z0-9_-]{8,64}$/);
    expect(id.startsWith("ws-")).toBe(true);
  });

  it("never repeats", () => {
    expect(newId("chat")).not.toBe(newId("chat"));
  });
});
