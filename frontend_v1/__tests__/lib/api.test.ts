import {
  uploadDocument,
  queryDocuments,
  deleteDocument,
  setResearch,
  getResearch,
  scoreDocument,
} from "@/lib/api";

beforeEach(() => {
  jest.resetAllMocks();
});

describe("uploadDocument", () => {
  it("returns success on 200", async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true, document_id: "d1", filename: "a.pdf" }),
      })
    ) as jest.Mock;

    const file = new File(["pdf"], "a.pdf", { type: "application/pdf" });
    const res = await uploadDocument(file);
    expect(res.success).toBe(true);
    expect(res.document_id).toBe("d1");
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it("returns error on failure", async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: false,
        statusText: "Bad Request",
        json: () => Promise.resolve({ detail: "Invalid file" }),
      })
    ) as jest.Mock;

    const file = new File(["x"], "x.pdf", { type: "application/pdf" });
    const res = await uploadDocument(file);
    expect(res.success).toBe(false);
    expect(res.error).toBe("Invalid file");
  });
});

describe("queryDocuments", () => {
  it("sends question and returns answer", async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true, answer: "42", citations: [], context_used: 1 }),
      })
    ) as jest.Mock;

    const res = await queryDocuments("What is 6*7?");
    expect(res.success).toBe(true);
    expect(res.answer).toBe("42");

    const [url, opts] = (global.fetch as jest.Mock).mock.calls[0];
    expect(url).toContain("/query");
    const body = JSON.parse(opts.body);
    expect(body.question).toBe("What is 6*7?");
  });

  it("passes document_id and top_k", async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve({ success: true }) })
    ) as jest.Mock;

    await queryDocuments("q", "doc-1", 3);
    const body = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
    expect(body.document_id).toBe("doc-1");
    expect(body.top_k).toBe(3);
  });
});

describe("deleteDocument", () => {
  it("calls DELETE /documents/:id", async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve({ success: true }) })
    ) as jest.Mock;

    const res = await deleteDocument("d1");
    expect(res.success).toBe(true);

    const [url, opts] = (global.fetch as jest.Mock).mock.calls[0];
    expect(url).toContain("/documents/d1");
    expect(opts.method).toBe("DELETE");
  });
});

describe("setResearch", () => {
  it("posts topic and description", async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true, topic: "FL", breakdown: "## B" }),
      })
    ) as jest.Mock;

    const res = await setResearch("FL", "desc");
    expect(res.success).toBe(true);
    expect(res.topic).toBe("FL");

    const body = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
    expect(body.topic).toBe("FL");
    expect(body.description).toBe("desc");
  });
});

describe("getResearch", () => {
  it("fetches GET /research", async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve({ success: true, topic: "T" }) })
    ) as jest.Mock;

    const res = await getResearch();
    expect(res.topic).toBe("T");
  });
});

describe("scoreDocument", () => {
  it("posts to /score/:id", async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true, score: 85, explanation: "relevant" }),
      })
    ) as jest.Mock;

    const res = await scoreDocument("d1");
    expect(res.success).toBe(true);
    expect(res.score).toBe(85);
  });

  it("returns error when no research set", async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: false,
        statusText: "Bad Request",
        json: () => Promise.resolve({ detail: "No research topic set" }),
      })
    ) as jest.Mock;

    const res = await scoreDocument("d1");
    expect(res.success).toBe(false);
    expect(res.error).toContain("No research");
  });
});
