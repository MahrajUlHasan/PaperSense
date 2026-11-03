import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const swatches = [
  ["Paper", "bg-background"],
  ["Shelf", "bg-shelf"],
  ["Ink", "bg-primary"],
  ["Graphite", "bg-muted-foreground"],
  ["Highlighter", "bg-highlight"],
  ["Rule", "bg-border"],
];

export default function StyleSheet() {
  return (
    <main className="mx-auto max-w-3xl space-y-12 px-6 py-12">
      <h1 className="font-serif text-3xl font-semibold">PaperSense style sheet</h1>

      <section>
        <h2 className="mb-3 font-semibold">Colours</h2>
        <div className="grid grid-cols-3 gap-4 sm:grid-cols-6">
          {swatches.map(([name, cls]) => (
            <div key={name}>
              <div className={`h-14 rounded-md border ${cls}`} />
              <p className="mt-1 text-sm">{name}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 font-semibold">Reading text</h2>
        <div className="answer-prose">
          <p>
            The model is trained with the Adam optimizer, with β₁ = 0.9 and β₂ = 0.98, and the learning rate
            rises linearly for the first 4000 steps before decaying
            <span className="cite-chip">1</span>.
          </p>
        </div>
      </section>

      <section>
        <h2 className="mb-3 font-semibold">The same passage on the PDF page</h2>
        <div className="rounded-md border bg-white p-6 font-serif text-[15px] leading-7 text-black shadow-sm">
          5.3 Optimizer.{" "}
          <span className="relative">
            We used the Adam optimizer with β₁ = 0.9, β₂ = 0.98 and ε = 10⁻⁹.
            <span className="pdf-highlight" style={{ inset: "-2px" }} />
          </span>{" "}
          We varied the learning rate over the course of training.
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="font-semibold">Controls</h2>
        <div className="flex flex-wrap gap-2">
          <Button>Save brief</Button>
          <Button variant="secondary">Test key</Button>
          <Button variant="outline">Add API key</Button>
          <Button variant="ghost">New chat</Button>
          <Button variant="destructive">Remove</Button>
        </div>
        <Input className="max-w-sm" placeholder="Ask about your papers" />
      </section>
    </main>
  );
}
