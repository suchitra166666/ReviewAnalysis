export function validateProviderKey(key: string): string | null {
  if (!key.trim()) return "Paste a key before saving.";
  if (key.trim().length < 8) return "That key looks too short.";
  return null;
}

export function validateCostCap(value: number): string | null {
  if (!Number.isFinite(value) || value <= 0) return "Cost cap must be greater than 0.";
  return null;
}
