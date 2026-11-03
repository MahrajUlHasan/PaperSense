import type { Metadata } from "next";
import { Atkinson_Hyperlegible_Next, Literata } from "next/font/google";
import { Providers } from "@/components/providers";
import "katex/dist/katex.min.css";
import "./globals.css";

const ui = Atkinson_Hyperlegible_Next({ subsets: ["latin"], variable: "--font-ui", display: "swap" });
const reading = Literata({ subsets: ["latin"], variable: "--font-reading", display: "swap", axes: ["opsz"] });

export const metadata: Metadata = {
  title: "PaperSense",
  description: "Ask questions about research papers and check every answer against the exact passage.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning className={`${ui.variable} ${reading.variable}`}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
