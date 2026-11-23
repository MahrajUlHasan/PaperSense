import { beforeEach, describe, expect, it } from "vitest";
import { useKeys } from "./keys";

describe("key storage", () => {
  beforeEach(() => {
    useKeys.setState({ keys: {}, remember: false });
    localStorage.clear();
    sessionStorage.clear();
  });

  it("keeps keys for this tab only by default", () => {
    useKeys.getState().setKey("gemini", "AIza-test");
    expect(sessionStorage.getItem("papersense.keys")).toContain("AIza-test");
    expect(localStorage.getItem("papersense.keys")).toBeNull();
  });

  it("moves keys to localStorage when they should be remembered", () => {
    useKeys.getState().setKey("gemini", "AIza-test");
    useKeys.getState().setRemember(true);
    expect(localStorage.getItem("papersense.keys")).toContain("AIza-test");
    expect(sessionStorage.getItem("papersense.keys")).toBeNull();
  });

  it("forgets every key", () => {
    useKeys.getState().setKey("groq", "gsk_test");
    useKeys.getState().forgetAll();
    expect(useKeys.getState().keys).toEqual({});
  });
});
