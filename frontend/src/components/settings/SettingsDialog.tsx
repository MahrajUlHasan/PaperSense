"use client";

import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FALLBACK_PROVIDERS, KEY_PLACEHOLDERS } from "@/lib/key-guides";
import type { ProviderId } from "@/lib/types";
import { useKeys } from "@/stores/keys";
import { useSettings } from "@/stores/settings";
import { type SettingsTab, useUi } from "@/stores/ui";
import { KeyGuide } from "./KeyGuide";
import { KeyTester } from "./KeyTester";

function Field({ id, label, hint, children }: { id: string; label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {hint && <p className="text-muted-foreground text-sm">{hint}</p>}
    </div>
  );
}

function SecretField(props: { id: string; label: string; hint?: string; value: string; placeholder: string; onChange: (value: string) => void }) {
  const [visible, setVisible] = useState(false);
  return (
    <Field id={props.id} label={props.label} hint={props.hint}>
      <div className="relative">
        <Input
          id={props.id}
          type={visible ? "text" : "password"}
          value={props.value}
          placeholder={props.placeholder}
          onChange={(e) => props.onChange(e.target.value)}
          autoComplete="off"
          spellCheck={false}
          className="pr-10"
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="absolute top-0 right-0 h-full"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Hide key" : "Show key"}
        >
          {visible ? <EyeOff /> : <Eye />}
        </Button>
      </div>
    </Field>
  );
}

function KeysForm() {
  const providers = useUi((s) => s.providers?.providers) ?? FALLBACK_PROVIDERS;
  const serverKey = useUi((s) => s.providers?.server_key_available ?? false);
  const provider = useSettings((s) => s.provider);
  const setProvider = useSettings((s) => s.setProvider);
  const model = useSettings((s) => s.models[s.provider] ?? "");
  const setModel = useSettings((s) => s.setModel);
  const keys = useKeys((s) => s.keys);
  const setKey = useKeys((s) => s.setKey);
  const remember = useKeys((s) => s.remember);
  const setRemember = useKeys((s) => s.setRemember);
  const forgetAll = useKeys((s) => s.forgetAll);
  const info = providers.find((p) => p.id === provider) ?? providers[0];
  const apiKey = keys[provider] ?? "";

  return (
    <div className="space-y-5 pt-3">
      <Field id="provider" label="Provider">
        <Select value={provider} onValueChange={(v) => setProvider(v as ProviderId)}>
          <SelectTrigger id="provider" className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {providers.map((p) => (
              <SelectItem key={p.id} value={p.id}>
                {p.name}
                {p.supports_images ? "" : " (text only)"}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </Field>

      <SecretField
        id="llm-key"
        label={`${info.name} API key`}
        value={apiKey}
        placeholder={KEY_PLACEHOLDERS[provider]}
        onChange={(v) => setKey(provider, v)}
      />

      <Field id="model" label="Model" hint={`Leave empty to use ${info.default_model}.`}>
        <Input
          id="model"
          value={model}
          placeholder={info.default_model}
          onChange={(e) => setModel(provider, e.target.value)}
          autoComplete="off"
          spellCheck={false}
        />
      </Field>

      {provider !== "gemini" && (
        <SecretField
          id="gemini-key"
          label="Gemini key for figures (optional)"
          hint="Describes figures when you upload papers, because Groq and OpenRouter can't read images."
          value={keys.gemini ?? ""}
          placeholder={KEY_PLACEHOLDERS.gemini}
          onChange={(v) => setKey("gemini", v)}
        />
      )}

      <KeyTester key={`${provider}|${apiKey}|${model}`} provider={provider} apiKey={apiKey} model={model} />

      <div className="flex items-start justify-between gap-4 rounded-md border p-3">
        <div className="space-y-0.5">
          <Label htmlFor="remember">Remember keys on this device</Label>
          <p className="text-muted-foreground text-sm">When this is off, keys are forgotten when you close the tab.</p>
        </div>
        <Switch id="remember" checked={remember} onCheckedChange={setRemember} />
      </div>

      <p className="text-muted-foreground text-sm">
        Keys go only to your PaperSense server, with the requests that need them. The server uses a key for that one
        request and never stores or logs it.
        {serverKey && " This server also has a built-in key for local testing, so your own key is optional here."}
      </p>

      <div className="flex justify-end">
        <Button variant="ghost" onClick={forgetAll} disabled={!Object.values(keys).some(Boolean)}>
          Forget all keys
        </Button>
      </div>
    </div>
  );
}

export function SettingsDialog() {
  const open = useUi((s) => s.settingsOpen);
  const setOpen = useUi((s) => s.setSettingsOpen);
  const tab = useUi((s) => s.settingsTab);
  const setTab = useUi((s) => s.setSettingsTab);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="font-serif text-xl">API keys</DialogTitle>
          <DialogDescription>PaperSense answers with your own free key. It stays in this browser.</DialogDescription>
        </DialogHeader>
        <Tabs value={tab} onValueChange={(v) => setTab(v as SettingsTab)}>
          <TabsList>
            <TabsTrigger value="keys">Your keys</TabsTrigger>
            <TabsTrigger value="guide">How to get a key</TabsTrigger>
          </TabsList>
          <TabsContent value="keys">
            <KeysForm />
          </TabsContent>
          <TabsContent value="guide">
            <KeyGuide />
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
