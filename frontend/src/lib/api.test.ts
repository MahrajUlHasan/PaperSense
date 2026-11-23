import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, buildHeaders, configureApi, type RequestIdentity } from "./api";

const identity: RequestIdentity = {
  workspaceId: "ws-test-00000001",
  sessionId: "chat-00000001",
  provider: "gemini",
  llmKey: "AIza-test-key",
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("buildHeaders", () => {
  it("adds keys only when asked", () => {
    expect(buildHeaders(identity, false)).toEqual({
      "X-Workspace-Id": "ws-test-00000001",
      "X-Session-Id": "chat-00000001",
    });
    expect(buildHeaders(identity, true)).toMatchObject({ "X-LLM-Provider": "gemini", "X-LLM-Key": "AIza-test-key" });
  });
});

describe("api", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("never sends a key when listing papers", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json({ documents: [] }));
    vi.stubGlobal("fetch", fetchMock);
    configureApi(() => identity);
    await api.listDocuments();
    const headers = fetchMock.mock.calls[0][1].headers as Record<string, string>;
    expect(headers["X-Workspace-Id"]).toBe("ws-test-00000001");
    expect(headers["X-LLM-Key"]).toBeUndefined();
  });

  it("sends the key with a question", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      json({ success: true, question: "q", answer: "a", citations: [], search_query: "q", contexts: [] }),
    );
    vi.stubGlobal("fetch", fetchMock);
    configureApi(() => identity);
    await api.query("q", []);
    expect((fetchMock.mock.calls[0][1].headers as Record<string, string>)["X-LLM-Key"]).toBe("AIza-test-key");
  });

  it("turns a missing key into a readable error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        json(
          {
            detail: {
              code: "missing_key",
              message: "Add your free API key in Settings → API keys to ask questions.",
              provider: "gemini",
              help_url: "https://aistudio.google.com/apikey",
              retry_after: null,
            },
          },
          401,
        ),
      ),
    );
    configureApi(() => identity);
    await expect(api.query("Which optimizer?", [])).rejects.toMatchObject({
      status: 401,
      code: "missing_key",
      helpUrl: "https://aistudio.google.com/apikey",
    });
  });

  it("reports an unreachable server", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    configureApi(() => identity);
    await expect(api.listDocuments()).rejects.toBeInstanceOf(ApiError);
  });
});
