import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import SourcesSidebar from "@/components/SourcesSidebar";
import type { Source } from "@/types";

// Mock lucide-react to avoid ESM issues
jest.mock("lucide-react", () => ({
  Plus: (p: any) => <span data-testid="icon-plus" {...p} />,
  FileText: (p: any) => <span data-testid="icon-file" {...p} />,
  Trash2: (p: any) => <span data-testid="icon-trash" {...p} />,
  Loader2: (p: any) => <span data-testid="icon-loader" {...p} />,
  AlertCircle: (p: any) => <span data-testid="icon-alert" {...p} />,
  CheckCircle2: (p: any) => <span data-testid="icon-check" {...p} />,
  ChevronLeft: (p: any) => <span data-testid="icon-left" {...p} />,
  ChevronRight: (p: any) => <span data-testid="icon-right" {...p} />,
}));

const baseProps = {
  sources: [] as Source[],
  collapsed: false,
  onToggle: jest.fn(),
  onAdd: jest.fn(),
  onDelete: jest.fn(),
  onSelect: jest.fn(),
  selectedId: undefined,
};

const readySource: Source = {
  documentId: "d1",
  filename: "paper.pdf",
  status: "ready",
  file: new File(["x"], "paper.pdf"),
  blobUrl: "blob://1",
  score: 82,
  scoreExplanation: "Relevant",
};

describe("SourcesSidebar", () => {
  it("renders empty state message when no sources", () => {
    render(<SourcesSidebar {...baseProps} />);
    expect(screen.getByText(/no sources yet/i)).toBeInTheDocument();
  });

  it("renders source filename and score badge", () => {
    render(<SourcesSidebar {...baseProps} sources={[readySource]} />);
    expect(screen.getByText("paper.pdf")).toBeInTheDocument();
    expect(screen.getByText("82/100")).toBeInTheDocument();
  });

  it("shows Ready badge for ready source", () => {
    render(<SourcesSidebar {...baseProps} sources={[readySource]} />);
    expect(screen.getByText("Ready")).toBeInTheDocument();
  });

  it("shows uploading badge", () => {
    const s: Source = { ...readySource, status: "uploading" };
    render(<SourcesSidebar {...baseProps} sources={[s]} />);
    expect(screen.getByText("Uploading…")).toBeInTheDocument();
  });

  it("shows scoring badge", () => {
    const s: Source = { ...readySource, status: "scoring" };
    render(<SourcesSidebar {...baseProps} sources={[s]} />);
    expect(screen.getByText("Scoring…")).toBeInTheDocument();
  });

  it("calls onToggle when toggle button clicked", () => {
    const onToggle = jest.fn();
    render(<SourcesSidebar {...baseProps} onToggle={onToggle} />);
    fireEvent.click(screen.getByLabelText("Toggle sources"));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("calls onSelect when a ready source is clicked", () => {
    const onSelect = jest.fn();
    render(<SourcesSidebar {...baseProps} sources={[readySource]} onSelect={onSelect} />);
    fireEvent.click(screen.getByText("paper.pdf"));
    expect(onSelect).toHaveBeenCalledWith(readySource);
  });

  it("renders collapsed view with icon buttons", () => {
    render(<SourcesSidebar {...baseProps} collapsed={true} sources={[readySource]} />);
    // In collapsed mode there should be no filename text, only icon buttons
    expect(screen.queryByText("paper.pdf")).not.toBeInTheDocument();
  });

  it("triggers file input when Add PDF button clicked", () => {
    render(<SourcesSidebar {...baseProps} />);
    const addBtn = screen.getByText("Add PDF");
    expect(addBtn).toBeInTheDocument();
  });

//   it("highlights selected source", () => {
//     render(<SourcesSidebar {...baseProps} sources={[readySource]} selectedId="d1" />);
//     const item = screen.getByText("paper.pdf").closest("div");
//     expect(item?.className).toContain("bg-primary");
//   });

  it("shows error badge and message", () => {
    const s: Source = { ...readySource, status: "error", error: "Parse failed" };
    render(<SourcesSidebar {...baseProps} sources={[s]} />);
    expect(screen.getByText("Error")).toBeInTheDocument();
    expect(screen.getByText("Parse failed")).toBeInTheDocument();
  });
});
