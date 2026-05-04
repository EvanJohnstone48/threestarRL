import type { BuildingPlacement, BaseLayoutMetadata } from "@/generated_types";

const AUTOSAVE_KEY = "editor_autosave";

export interface AutosaveDraft {
  placements: BuildingPlacement[];
  metadata: BaseLayoutMetadata;
  savedAt: string;
}

export function saveToLocalStorage(
  placements: BuildingPlacement[],
  metadata: BaseLayoutMetadata,
): void {
  const draft: AutosaveDraft = { placements, metadata, savedAt: new Date().toISOString() };
  localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(draft));
}

export function loadFromLocalStorage(): AutosaveDraft | null {
  try {
    const raw = localStorage.getItem(AUTOSAVE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as AutosaveDraft;
  } catch {
    return null;
  }
}

export function clearLocalStorage(): void {
  localStorage.removeItem(AUTOSAVE_KEY);
}
