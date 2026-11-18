"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

const MIN_WIDTH = 380;
const clampWidth = (width: number) => Math.min(Math.max(width, MIN_WIDTH), Math.round(window.innerWidth * 0.92));

/** Clicks on these don't close the panel: citation chips and source rows, pop-ups, dialogs, toasts. */
const KEEP_OPEN = "[data-citation-chip], [data-radix-popper-content-wrapper], [role='dialog'], [role='alertdialog'], [data-sonner-toaster]";

interface SlideOverProps {
  open: boolean;
  width: number;
  onWidthChange: (width: number) => void;
  onClose: () => void;
  label: string;
  children: React.ReactNode;
}

/**
 * A panel that slides in from the right over the page. The chat behind it stays usable:
 * clicking another citation updates the panel; clicking anywhere else, or Esc, closes it.
 */
export function SlideOver({ open, width, onWidthChange, onClose, label, children }: SlideOverProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    panelRef.current?.focus({ preventScroll: true });
    const onKey = (e: KeyboardEvent) => {
      const otherDialog = document.querySelector("[role='dialog'][data-state='open']:not([data-slide-over])");
      if (e.key === "Escape" && !otherDialog) onClose();
    };
    const onPointer = (e: PointerEvent) => {
      const target = e.target as Element | null;
      if (!target || panelRef.current?.contains(target) || target.closest(KEEP_OPEN)) return;
      onClose();
    };
    window.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [open, onClose]);

  const startDrag = (e: React.PointerEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = width;
    const move = (ev: PointerEvent) => onWidthChange(clampWidth(startWidth + startX - ev.clientX));
    const stop = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stop);
      document.body.style.userSelect = "";
    };
    document.body.style.userSelect = "none";
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop);
  };

  return (
    <div
      ref={panelRef}
      role="dialog"
      data-slide-over
      aria-modal="false"
      aria-label={label}
      aria-hidden={!open}
      inert={!open}
      tabIndex={-1}
      style={{ width }}
      className={cn(
        "bg-background fixed inset-y-0 right-0 z-40 flex max-w-full flex-col border-l outline-none",
        "shadow-[-16px_0_40px_-16px_rgb(28_37_65/0.3)] transition-transform duration-300 ease-out motion-reduce:transition-none",
        open ? "translate-x-0" : "pointer-events-none translate-x-full",
      )}
    >
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize the PDF panel (arrow keys)"
        tabIndex={0}
        onPointerDown={startDrag}
        onKeyDown={(e) => {
          if (e.key === "ArrowLeft") onWidthChange(clampWidth(width + 40));
          if (e.key === "ArrowRight") onWidthChange(clampWidth(width - 40));
        }}
        className="hover:bg-ring/30 focus-visible:bg-ring/40 absolute inset-y-0 -left-1 z-10 hidden w-2 cursor-col-resize sm:block"
      />
      {children}
    </div>
  );
}
