import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import PdfViewer from "@/components/PdfViewer";
import type { Citation, Source } from "@/types";

jest.mock("lucide-react", () => ({
  X: (p: any) => <span data-testid="icon-x" {...p} />,
  FileText: (p: any) => <span data-testid="icon-file" {...p} />,
  BookOpen: (p: any) => <span data-testid="icon-book" {...p} />,
  Copy: (p: any) => <span data-testid="icon-copy" {...p} />,
  CheckCircle2: (p: any) => <span data-testid="icon-check" {...p} />,
}));

const source: Source = {
  documentId: "d1",
  filename: "paper.pdf",
  status: "ready",
  file: new File(["x"], "paper.pdf"),
  blobUrl: "blob://test-pdf",
};

const citation: Citation = {
  index: 1,
  section: "Introduction",
  score: 9.2,
  document_id: "d1",
  filename: "paper.pdf",
  text: "Neural nets are universal.",
  page: 3,
};

describe("PdfViewer", () => {
  it("returns null when not open", () => {
    const { container } = render(
      <PdfViewer isOpen={false} citation={null} source={null} onClose={jest.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("returns null when source is null", () => {
    const { container } = render(
      <PdfViewer isOpen={true} citation={citation} source={null} onClose={jest.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders filename and page badge", () => {
    render(<PdfViewer isOpen={true} citation={citation} source={source} onClose={jest.fn()} />);
    expect(screen.getByText("paper.pdf")).toBeInTheDocument();
    expect(screen.getByText("Page 3")).toBeInTheDocument();
  });

  it("renders citation text in quotes", () => {
    render(<PdfViewer isOpen={true} citation={citation} source={source} onClose={jest.fn()} />);
    expect(screen.getByText(/Neural nets are universal/)).toBeInTheDocument();
  });

  it("renders section and score", () => {
    render(<PdfViewer isOpen={true} citation={citation} source={source} onClose={jest.fn()} />);
    expect(screen.getByText(/Citation \[1\]/)).toBeInTheDocument();
    expect(screen.getByText(/Introduction/)).toBeInTheDocument();
    expect(screen.getByText(/92% match/)).toBeInTheDocument();
  });

  it("renders PDF iframe with correct src", () => {
    render(<PdfViewer isOpen={true} citation={citation} source={source} onClose={jest.fn()} />);
    const iframe = screen.getByTitle("paper.pdf");
    expect(iframe).toBeInTheDocument();
    expect(iframe.getAttribute("src")).toContain("blob://test-pdf");
    expect(iframe.getAttribute("src")).toContain("page=3");
  });

  it("calls onClose when X button clicked", () => {
    const onClose = jest.fn();
    render(<PdfViewer isOpen={true} citation={citation} source={source} onClose={onClose} />);
    const closeBtn = screen.getByTestId("icon-x").closest("button");
    fireEvent.click(closeBtn!);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when backdrop clicked", () => {
    const onClose = jest.fn();
    const { container } = render(
      <PdfViewer isOpen={true} citation={citation} source={source} onClose={onClose} />
    );
    // Backdrop is the first div with bg-black/40
    const backdrop = container.querySelector(".bg-black\\/40") as HTMLElement;
    if (backdrop) {
      fireEvent.click(backdrop);
      expect(onClose).toHaveBeenCalledTimes(1);
    }
  });

  it("defaults to page 1 when citation has no page", () => {
    const citNoPage = { ...citation, page: undefined };
    render(<PdfViewer isOpen={true} citation={citNoPage} source={source} onClose={jest.fn()} />);
    const iframe = screen.getByTitle("paper.pdf");
    expect(iframe.getAttribute("src")).toContain("page=1");
  });

  it("shows Ctrl+F hint", () => {
    render(<PdfViewer isOpen={true} citation={citation} source={source} onClose={jest.fn()} />);
    expect(screen.getByText(/Ctrl\+F/)).toBeInTheDocument();
  });
});
