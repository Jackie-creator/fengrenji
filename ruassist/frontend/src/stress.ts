/**
 * Stress handling, mirroring src/ruassist/stress.py.
 *
 * The display form always carries U+0301; the search key never does. Keeping
 * the two apart is what lets a learner type "рука" and still be shown "рука́".
 */

export const STRESS = "́";

const VOWELS = "аеёиоуыэюяАЕЁИОУЫЭЮЯ";

export function stripStress(text: string): string {
  return text.normalize("NFC").replaceAll(STRESS, "");
}

/** ё is routinely written as е in real Russian text, so search folds them. */
export function foldYo(text: string): string {
  return text.replaceAll("ё", "е").replaceAll("Ё", "Е");
}

export function searchKey(text: string): string {
  return foldYo(stripStress(text)).toLowerCase().trim();
}

export function countVowels(text: string): number {
  return [...text].filter((ch) => VOWELS.includes(ch)).length;
}

/**
 * Hide stress marks for readers who no longer need them.
 *
 * ё is left alone: it is a letter, not a diacritic, and removing it would
 * misspell the word.
 */
export function forDisplay(text: string, showStress: boolean): string {
  return showStress ? text : stripStress(text);
}
