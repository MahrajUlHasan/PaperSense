import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { api } from "@/lib/api";
import { KeyTester } from "./KeyTester";

afterEach(() => vi.restoreAllMocks());

it("shows the result of a key test", async () => {
  const testKey = vi
    .spyOn(api, "testKey")
    .mockResolvedValue({ ok: false, message: "Google rejected this Gemini API key.", code: "invalid_key" });
  render(<KeyTester provider="gemini" apiKey="AIza-wrong" model="" />);
  await userEvent.click(screen.getByRole("button", { name: /test key/i }));
  expect(await screen.findByText("Google rejected this Gemini API key.")).toBeInTheDocument();
  expect(testKey).toHaveBeenCalledWith("gemini", "AIza-wrong", "");
});

it("can't test without a key", () => {
  render(<KeyTester provider="gemini" apiKey="" model="" />);
  expect(screen.getByRole("button", { name: /test key/i })).toBeDisabled();
});
