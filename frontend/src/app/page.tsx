"use client";

import dynamic from "next/dynamic";

const AppShell = dynamic(() => import("@/components/shell/AppShell"), {
  ssr: false,
  loading: () => <div className="text-muted-foreground grid h-dvh place-items-center">Opening PaperSense…</div>,
});

export default function Home() {
  return <AppShell />;
}
