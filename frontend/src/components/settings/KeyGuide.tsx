"use client";

import { KEY_GUIDES } from "@/lib/key-guides";
import { useSettings } from "@/stores/settings";
import { useUi } from "@/stores/ui";

/** Step-by-step guides; the current provider comes first. */
export function KeyGuide() {
  const provider = useSettings((s) => s.provider);
  const setTab = useUi((s) => s.setSettingsTab);
  const guides = [...KEY_GUIDES].sort((a, b) => Number(b.provider === provider) - Number(a.provider === provider));

  return (
    <div className="space-y-8 pt-3">
      {guides.map((guide) => (
        <section key={guide.provider} aria-labelledby={`guide-${guide.provider}`}>
          <h3 id={`guide-${guide.provider}`} className="font-serif text-lg font-semibold">
            {guide.name}
          </h3>
          <p className="text-muted-foreground mt-1 text-sm">{guide.summary}</p>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm">
            {guide.steps.map((step) => (
              <li key={step.text}>
                {step.text}
                {step.link && (
                  <>
                    {" "}
                    <a href={step.link.href} target="_blank" rel="noreferrer" className="underline underline-offset-2">
                      {step.link.label}
                    </a>
                  </>
                )}
              </li>
            ))}
          </ol>
          <p className="bg-muted mt-3 rounded-md px-3 py-2 text-sm">{guide.freeTier}</p>
        </section>
      ))}
      <button type="button" className="text-sm underline underline-offset-2" onClick={() => setTab("keys")}>
        Back to your keys
      </button>
    </div>
  );
}
