/**
 * Bundle types and tiered lookup, mirroring index.py / search.py.
 *
 * Everything here runs against a table that was expanded at build time. There
 * is no morphology engine in the browser and no network call: the whole point
 * of the offline design is that lookup is a map read.
 */

import { searchKey } from "./stress";
import { isLatin, toCyrillic } from "./translit";

export interface Sense {
  zh: string;
  en?: string;
  lb?: string[];
  col?: string[];
  ex?: [string, string][];
}

export interface Entry {
  i: number;
  l: string;
  s: string;
  p: string;
  sen: Sense[];
  f: Record<string, string>;
  g?: string;
  an?: string;
  asp?: string;
  tr?: string;
  mg?: string;
  z?: string;
  pair?: string;
  gov?: string;
  mp?: string;
  cmp?: string;
  sup?: string;
  hom?: number;
  freq?: number;
  num?: string;
  n?: { aspect?: string; errors?: string; notes?: string };
  lv?: string[];
  rel?: { syn: string[]; ant: string[] };
  hand?: boolean;
}

export interface Bundle {
  version: string;
  generated: string;
  stats: { entries: number; forms: number; senses: number };
  entries: Entry[];
  forms: Record<string, number[]>;
}

export type MatchKind = "exact" | "translit" | "prefix" | "fuzzy";

export interface Result {
  entry: Entry;
  kind: MatchKind;
  distance: number;
  /** The paradigm cell that matched, when it was not the lemma itself. */
  via?: { tag: string; text: string };
}

/** Letters Chinese learners routinely swap. */
const CONFUSABLE: Record<string, string[]> = {
  и: ["ы"], ы: ["и"],
  е: ["э", "и"], э: ["е"],
  о: ["а"], а: ["о"],
  ш: ["щ", "с"], щ: ["ш"],
  з: ["с"], с: ["з", "ш"],
  б: ["п"], п: ["б"],
  в: ["ф"], ф: ["в"],
  д: ["т"], т: ["д"],
  г: ["к"], к: ["г"],
  ж: ["ш"], ч: ["ц"], ц: ["ч"],
};

const SHORT_WORD = 4;

export class Dictionary {
  private buckets = new Map<string, string[]>();
  private formKeys: string[];

  constructor(readonly bundle: Bundle) {
    this.formKeys = Object.keys(bundle.forms);
    for (const key of this.formKeys) {
      const bucket = `${key[0]}:${key.length}`;
      const list = this.buckets.get(bucket);
      if (list) list.push(key);
      else this.buckets.set(bucket, [key]);
    }
  }

  entry(id: number): Entry {
    return this.bundle.entries[id];
  }

  lookup(query: string, limit = 20): Result[] {
    let key = searchKey(query);
    if (!key) return [];

    const exact = this.resolve(key, "exact", 0);
    if (exact.length) return exact.slice(0, limit);

    if (isLatin(query)) {
      const converted = searchKey(toCyrillic(query));
      const hits = this.resolve(converted, "translit", 0);
      if (hits.length) return hits.slice(0, limit);
      key = converted;
    }

    const prefix = this.prefix(key, limit);
    if (prefix.length) return prefix;

    return this.fuzzy(key, limit);
  }

  private resolve(key: string, kind: MatchKind, distance: number): Result[] {
    const ids = this.bundle.forms[key];
    if (!ids) return [];
    return ids.map((id) => {
      const entry = this.entry(id);
      return { entry, kind, distance, via: this.cellFor(entry, key) };
    });
  }

  /** Which paradigm cell the query matched, so the UI can label it. */
  private cellFor(entry: Entry, key: string): Result["via"] {
    if (searchKey(entry.l) === key) return undefined;
    for (const [tag, text] of Object.entries(entry.f)) {
      if (searchKey(text) === key) return { tag, text };
    }
    return undefined;
  }

  private prefix(key: string, limit: number): Result[] {
    if (key.length < 2) return [];
    const results: Result[] = [];
    for (const form of this.formKeys) {
      if (form.length > key.length && form.startsWith(key)) {
        results.push(...this.resolve(form, "prefix", form.length - key.length));
      }
    }
    return bestPerEntry(results, limit);
  }

  private fuzzy(key: string, limit: number): Result[] {
    const budget = key.length < SHORT_WORD ? 1 : 2;
    const results: Result[] = [];
    const seen = new Set<string>();

    for (const initial of [key[0], ...(CONFUSABLE[key[0]] ?? [])]) {
      for (let len = key.length - budget; len <= key.length + budget; len++) {
        for (const form of this.buckets.get(`${initial}:${len}`) ?? []) {
          if (seen.has(form)) continue;
          seen.add(form);
          const distance = boundedLevenshtein(key, form, budget);
          if (distance === null) continue;
          results.push(...this.resolve(form, "fuzzy", distance));
        }
      }
    }
    return bestPerEntry(results, limit);
  }
}

/** One hit per entry: the user wants a list of words, not of grammatical cells. */
function bestPerEntry(results: Result[], limit: number): Result[] {
  const best = new Map<number, Result>();
  for (const result of results) {
    const current = best.get(result.entry.i);
    if (!current || result.distance < current.distance) best.set(result.entry.i, result);
  }
  return [...best.values()]
    .sort((a, b) => a.distance - b.distance || a.entry.l.localeCompare(b.entry.l))
    .slice(0, limit);
}

function boundedLevenshtein(a: string, b: string, budget: number): number | null {
  if (Math.abs(a.length - b.length) > budget) return null;
  let previous = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    const current = [i];
    for (let j = 1; j <= b.length; j++) {
      current.push(
        Math.min(
          previous[j] + 1,
          current[j - 1] + 1,
          previous[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1),
        ),
      );
    }
    if (Math.min(...current) > budget) return null;
    previous = current;
  }
  return previous[b.length] <= budget ? previous[b.length] : null;
}

export async function loadBundle(url: string): Promise<Bundle> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`词库加载失败：${response.status}`);
  return (await response.json()) as Bundle;
}
