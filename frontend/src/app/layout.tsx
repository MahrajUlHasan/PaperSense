import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PaperSense — Smart Research Paper Analyzer",
  description: "Upload research papers, ask questions, get cited answers.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="light">
      <body className="h-screen">{children}</body>
    </html>
  );
}
