import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import ResearchPanel from "@/components/ResearchPanel";
import type { ResearchData } from "@/types";

jest.mock("lucide-react", () => ({
  ChevronLeft: (p: any) => <span {...p} />,
  ChevronRight: (p: any) => <span {...p} />,
  Loader2: (p: any) => <span {...p} />,
  FlaskConical: (p: any) => <span {...p} />,
}));

const emptyResearch: ResearchData = { topic: "", description: "" };
const filledResearch: ResearchData = {
  topic: "FL in IoT",
  description: "Studying federated learning",
  breakdown: "## Key Themes\n- Privacy",
};

const baseProps = {
  collapsed: false,
  onToggle: jest.fn(),
  research: emptyResearch,
  onSave: jest.fn(() => Promise.resolve()),
  isSaving: false,
};

describe("ResearchPanel", () => {
  it("renders topic and description inputs", () => {
    render(<ResearchPanel {...baseProps} />);
    expect(screen.getByPlaceholderText(/federated learning/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/describe your research/i)).toBeInTheDocument();
  });

  it("Save button is disabled when topic is empty", () => {
    render(<ResearchPanel {...baseProps} />);
    const btn = screen.getByText("Save Research");
    expect(btn).toBeDisabled();
  });

  it("Save button is enabled when topic is filled and dirty", () => {
    render(<ResearchPanel {...baseProps} />);
    fireEvent.change(screen.getByPlaceholderText(/federated learning/i), {
      target: { value: "New Topic" },
    });
    const btn = screen.getByText("Save Research");
    expect(btn).not.toBeDisabled();
  });

  it("calls onSave with topic and description", () => {
    const onSave = jest.fn(() => Promise.resolve());
    render(<ResearchPanel {...baseProps} onSave={onSave} />);

    fireEvent.change(screen.getByPlaceholderText(/federated learning/i), {
      target: { value: "Topic" },
    });
    fireEvent.change(screen.getByPlaceholderText(/describe your research/i), {
      target: { value: "Details" },
    });
    fireEvent.click(screen.getByText("Save Research"));

    expect(onSave).toHaveBeenCalledWith("Topic", "Details");
  });

  it("shows Saving… when isSaving is true", () => {
    render(<ResearchPanel {...baseProps} isSaving={true} research={filledResearch} />);
    expect(screen.getByText("Saving…")).toBeInTheDocument();
  });

  it("shows breakdown in collapse when research has breakdown", () => {
    render(<ResearchPanel {...baseProps} research={filledResearch} />);
    expect(screen.getByText("Research Breakdown")).toBeInTheDocument();
  });

  it("pre-fills inputs from existing research", () => {
    render(<ResearchPanel {...baseProps} research={filledResearch} />);
    const topicInput = screen.getByDisplayValue("FL in IoT");
    expect(topicInput).toBeInTheDocument();
  });

  it("calls onToggle when toggle is clicked", () => {
    const onToggle = jest.fn();
    render(<ResearchPanel {...baseProps} onToggle={onToggle} />);
    fireEvent.click(screen.getByLabelText("Toggle research"));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("renders collapsed view", () => {
    render(<ResearchPanel {...baseProps} collapsed={true} />);
    // In collapsed mode, topic input should not render
    expect(screen.queryByPlaceholderText(/federated learning/i)).not.toBeInTheDocument();
  });
});
