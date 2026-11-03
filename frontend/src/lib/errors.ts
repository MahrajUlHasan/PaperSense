import { toast } from "sonner";
import { useUi } from "@/stores/ui";
import { ApiError } from "./api";

function formatWait(seconds: number): string {
  if (seconds < 90) return `${Math.ceil(seconds)} seconds`;
  if (seconds < 5400) return `${Math.ceil(seconds / 60)} minutes`;
  return `${Math.round(seconds / 3600)} hours`;
}

/** Shows an API problem as a toast in plain words, with a way to fix it where there is one. */
export function notifyError(error: unknown, fallback = "Something went wrong."): void {
  if (!(error instanceof ApiError)) {
    toast.error(fallback);
    return;
  }
  const openKeys = () => useUi.getState().openSettings("keys");
  switch (error.code) {
    case "missing_key":
      toast.error("Add an API key to ask questions.", {
        description: "It's free and stays in this browser.",
        action: { label: "Add key", onClick: openKeys },
      });
      return;
    case "invalid_key":
      toast.error(error.message, { action: { label: "Check key", onClick: openKeys } });
      return;
    case "rate_limited":
      toast.warning("This key's free limit is used up for now.", {
        description: error.retryAfter
          ? `Try again in about ${formatWait(error.retryAfter)}, or use another model or key.`
          : "Free keys have per-minute and per-day limits. Wait a little, or use another model or key.",
        action: { label: "Change", onClick: openKeys },
      });
      return;
    case "unavailable":
      toast.warning(error.message);
      return;
    default:
      toast.error(error.message || fallback);
  }
}

export function errorText(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong.";
}
