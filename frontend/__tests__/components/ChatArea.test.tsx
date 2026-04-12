import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import ChatArea from "@/components/ChatArea";
import type { ChatMessage, Source } from "@/types";

jest.mock("lucide-react", () => ({
  Send: (p: any) => <span data-testid="icon-send" {...p} />,
  Loader2: (p: any) => <span data-testid="icon-loader" {...p} />,
  MessageSquare: (p: any) => <span data-testid="icon-msg" {...p} />,
}));

// Mock react-markdown to avoid ESM issues in Jest
jest.mock("react-markdown", () => {
  return ({ children }: { children: string }) => <div data-testid="markdown">{children}</div>;
});
jest.mock("remark-gfm", () => () => {});

const readySource: Source = {
  documentId: "d1",
  filename: "p.pdf",
  status: "ready",
  file: new File(["x"], "p.pdf"),
  blobUrl: "blob://1",
};

const baseProps = {
  messages: [] as ChatMessage[],
  isLoading: false,
  onSend: jest.fn(),
  onCitationClick: jest.fn(),
  sources: [readySource],
  isEmpty: true,
};

describe("ChatArea — empty state", () => {
  it("renders centered input when isEmpty", () => {
    render(<ChatArea {...baseProps} />);
    expect(screen.getByText("PaperSense")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/ask about your papers/i)).toBeInTheDocument();
  });

  it("disables input when no ready sources", () => {
    render(<ChatArea {...baseProps} sources={[]} />);
    const input = screen.getByPlaceholderText(/upload a pdf first/i);
    expect(input).toBeDisabled();
  });

  it("calls onSend and clears input on submit", () => {
    const onSend = jest.fn();
    render(<ChatArea {...baseProps} onSend={onSend} />);

    const input = screen.getByPlaceholderText(/ask about your papers/i);
    fireEvent.change(input, { target: { value: "What is X?" } });
    fireEvent.submit(input.closest("form")!);

    expect(onSend).toHaveBeenCalledWith("What is X?");
  });

  it("does not send empty string", () => {
    const onSend = jest.fn();
    render(<ChatArea {...baseProps} onSend={onSend} />);

    fireEvent.submit(screen.getByPlaceholderText(/ask about your papers/i).closest("form")!);
    expect(onSend).not.toHaveBeenCalled();
  });
});

describe("ChatArea — chat view", () => {
  const msgs: ChatMessage[] = [
    { id: "1", role: "user", content: "What is AI?", timestamp: new Date() },
    {
      id: "2",
      role: "assistant",
      content: "AI is artificial intelligence [1].",
      citations: [
        { index: 1, section: "intro", score: 0.9, document_id: "d1", filename: "p.pdf", text: "AI def", page: 2 },
      ],
      timestamp: new Date(),
    },
  ];

  it("renders user and assistant messages", () => {
    render(<ChatArea {...baseProps} messages={msgs} isEmpty={false} />);
    expect(screen.getByText("What is AI?")).toBeInTheDocument();
    expect(screen.getByText(/AI is artificial intelligence/)).toBeInTheDocument();
  });

  it("shows Thinking indicator when loading", () => {
    render(<ChatArea {...baseProps} messages={msgs} isEmpty={false} isLoading={true} />);
    expect(screen.getByText("Thinking…")).toBeInTheDocument();
  });

  it("renders bottom input in chat mode", () => {
    render(<ChatArea {...baseProps} messages={msgs} isEmpty={false} />);
    expect(screen.getByPlaceholderText(/ask about your papers/i)).toBeInTheDocument();
  });
});
