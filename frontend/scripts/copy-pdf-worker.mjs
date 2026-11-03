/**
 * Copies pdf.js's worker into public/, so the viewer can load it from /pdf.worker.min.mjs.
 * Runs after every npm install; the copy always matches the installed react-pdf.
 */
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { join } from "node:path";

const candidates = ["node_modules/react-pdf/node_modules/pdfjs-dist", "node_modules/pdfjs-dist"];
const dir = candidates.find((d) => existsSync(join(d, "build", "pdf.worker.min.mjs")));

if (!dir) {
  console.warn("pdf.worker.min.mjs not found; run npm install first.");
  process.exit(0);
}
mkdirSync("public", { recursive: true });
copyFileSync(join(dir, "build", "pdf.worker.min.mjs"), join("public", "pdf.worker.min.mjs"));
console.log(`Copied the PDF worker from ${dir}`);
