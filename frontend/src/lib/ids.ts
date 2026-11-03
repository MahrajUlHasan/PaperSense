/** A random id the backend accepts (letters, digits, "-", 8–64 characters). */
export function newId(prefix: string): string {
  const raw =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`;
  return `${prefix}-${raw.replace(/-/g, "").slice(0, 24)}`;
}
