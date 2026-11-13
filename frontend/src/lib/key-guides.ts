import type { ProviderId, ProviderInfo } from "./types";

export const KEY_PLACEHOLDERS: Record<ProviderId, string> = {
  gemini: "AIza…",
  groq: "gsk_…",
  openrouter: "sk-or-…",
};

/** Used until GET /config/providers has answered (or if it fails). */
export const FALLBACK_PROVIDERS: ProviderInfo[] = [
  { id: "gemini", name: "Google Gemini", default_model: "gemini-3.5-flash", supports_images: true, key_url: "https://aistudio.google.com/apikey" },
  { id: "groq", name: "Groq", default_model: "llama-3.3-70b-versatile", supports_images: false, key_url: "https://console.groq.com/keys" },
  { id: "openrouter", name: "OpenRouter", default_model: "google/gemma-4-31b-it:free", supports_images: false, key_url: "https://openrouter.ai/keys" },
];

export interface KeyGuideStep {
  text: string;
  link?: { label: string; href: string };
}

export interface KeyGuide {
  provider: ProviderId;
  name: string;
  summary: string;
  steps: KeyGuideStep[];
  freeTier: string;
}

export const KEY_GUIDES: KeyGuide[] = [
  {
    provider: "gemini",
    name: "Google Gemini",
    summary: "Recommended. Answers questions, describes figures when you upload papers, and looks at figures when you ask about them.",
    steps: [
      { text: "Open Google AI Studio and sign in with a Google account.", link: { label: "aistudio.google.com", href: "https://aistudio.google.com" } },
      { text: "Accept the terms if this is your first visit." },
      { text: "Choose Get API key, then Create API key.", link: { label: "Open the API keys page", href: "https://aistudio.google.com/apikey" } },
      { text: "Pick an existing Google Cloud project, or let AI Studio create one." },
      { text: "Copy the key. It starts with AIza." },
      { text: "Paste it under Your keys, with Google Gemini as the provider, and choose Test key." },
    ],
    freeTier:
      "No credit card needed. Limits are per model, per minute and per day; AI Studio shows yours under Rate limits. The default model allows only a few dozen questions a day, so if you run out, set Model to gemini-3.5-flash-lite. Google may use prompts sent with a free key to improve its products, so don't upload confidential papers.",
  },
  {
    provider: "groq",
    name: "Groq",
    summary: "Optional. Very fast text answers. It can't read images, so add a Gemini key too if you want figures described.",
    steps: [
      { text: "Open the Groq console and sign up with Google, GitHub or email.", link: { label: "console.groq.com", href: "https://console.groq.com" } },
      { text: "Go to API Keys and choose Create API Key. Give it a name.", link: { label: "Open the API keys page", href: "https://console.groq.com/keys" } },
      { text: "Copy the key right away; it starts with gsk_ and is shown only once." },
      { text: "Paste it under Your keys, with Groq as the provider, and choose Test key." },
    ],
    freeTier: "Free, with per-minute and per-day limits shown in the console under Settings → Limits.",
  },
  {
    provider: "openrouter",
    name: "OpenRouter",
    summary: "Optional. One key for many models, including free ones. Text only.",
    steps: [
      { text: "Open OpenRouter and sign in.", link: { label: "openrouter.ai", href: "https://openrouter.ai" } },
      { text: "Go to Keys and choose Create Key. Name it and copy it; it starts with sk-or-.", link: { label: "Open the keys page", href: "https://openrouter.ai/keys" } },
      { text: "Paste it under Your keys, with OpenRouter as the provider." },
      { text: "Under Model, keep the default or pick another model whose name ends in :free, then choose Test key." },
    ],
    freeTier: "Models ending in :free cost nothing but have a small daily request limit.",
  },
];
