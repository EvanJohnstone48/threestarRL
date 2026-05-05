import type { BuildingPlacement, BaseLayoutMetadata } from "@/generated_types";

const AUTOSAVE_KEY = "editor_autosave";
const SCREENSHOT_KEY = "editor_screenshot";

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

export function saveScreenshotToLocalStorage(dataUrl: string): void {
  try {
    localStorage.setItem(SCREENSHOT_KEY, dataUrl);
  } catch {
    // QuotaExceededError on very large images — silently drop, screenshot won't persist
  }
}

export function loadScreenshotFromLocalStorage(): string | null {
  return localStorage.getItem(SCREENSHOT_KEY);
}

export function clearScreenshotFromLocalStorage(): void {
  localStorage.removeItem(SCREENSHOT_KEY);
}
