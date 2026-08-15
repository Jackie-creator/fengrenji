/**
 * Local persistence for the notebook and review schedule.
 *
 * localStorage, not IndexedDB: the payload is a few hundred cards of small
 * numbers, and a synchronous read keeps the UI free of loading states. If the
 * notebook ever grows past a few thousand entries this should move.
 *
 * There is no server and no account, so this is the only copy of the user's
 * progress -- every write is guarded, and a corrupt blob degrades to an empty
 * notebook rather than a crash that loses the app entirely.
 */

import type { Card } from "./srs";

const KEY = "ruassist.notebook.v1";
const SETTINGS_KEY = "ruassist.settings.v1";

export interface Settings {
  showStress: boolean;
  dailyLimit: number;
}

export const DEFAULT_SETTINGS: Settings = { showStress: true, dailyLimit: 30 };

export function loadCards(): Card[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isCard);
  } catch {
    return [];
  }
}

export function saveCards(cards: Card[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(cards));
  } catch {
    /* quota exceeded or storage disabled; the session still works in memory */
  }
}

export function loadSettings(): Settings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function saveSettings(settings: Settings): void {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch {
    /* ignore */
  }
}

function isCard(value: unknown): value is Card {
  if (typeof value !== "object" || value === null) return false;
  const c = value as Partial<Card>;
  return (
    typeof c.entryId === "number" &&
    typeof c.ease === "number" &&
    typeof c.interval === "number" &&
    typeof c.due === "number"
  );
}

/** Export as JSON so a user can move devices without an account. */
export function exportNotebook(cards: Card[]): string {
  return JSON.stringify({ version: 1, exported: Date.now(), cards }, null, 2);
}

export function importNotebook(text: string): Card[] {
  const parsed = JSON.parse(text);
  const cards = Array.isArray(parsed) ? parsed : parsed?.cards;
  if (!Array.isArray(cards)) throw new Error("文件格式不对");
  return cards.filter(isCard);
}
