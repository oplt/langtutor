import type { StoryOut } from "./api/learningApi";
import type { CefrLevel } from "./api/learningPathApi";

const STORAGE_PREFIX = "languageapp:story:";

function storageKey(level: CefrLevel): string {
  return `${STORAGE_PREFIX}${level}`;
}

export function loadStoryFromSession(level: CefrLevel): StoryOut | null {
  try {
    const raw = sessionStorage.getItem(storageKey(level));
    if (!raw) return null;
    return JSON.parse(raw) as StoryOut;
  } catch {
    return null;
  }
}

export function saveStoryToSession(level: CefrLevel, story: StoryOut): void {
  try {
    sessionStorage.setItem(storageKey(level), JSON.stringify(story));
  } catch {
    // Ignore quota or private-mode errors.
  }
}

export function clearStorySession(): void {
  try {
    const keys: string[] = [];
    for (let index = 0; index < sessionStorage.length; index += 1) {
      const key = sessionStorage.key(index);
      if (key?.startsWith(STORAGE_PREFIX)) {
        keys.push(key);
      }
    }
    for (const key of keys) {
      sessionStorage.removeItem(key);
    }
  } catch {
    // Ignore storage errors.
  }
}
