/**
 * Latin -> Cyrillic input, mirroring src/ruassist/translit.py.
 *
 * Chinese users have no Cyrillic keyboard, so this is the difference between a
 * usable dictionary and one they cannot type into at all.
 */

const RULES: [string, string][] = [
  ["shch", "щ"], ["sch", "щ"], ["shh", "щ"],
  ["yo", "ё"], ["jo", "ё"], ["yu", "ю"], ["ju", "ю"],
  ["ya", "я"], ["ja", "я"], ["ye", "е"], ["je", "е"],
  ["zh", "ж"], ["kh", "х"], ["ts", "ц"], ["ch", "ч"], ["sh", "ш"],
  ["a", "а"], ["b", "б"], ["v", "в"], ["g", "г"], ["d", "д"],
  ["e", "е"], ["z", "з"], ["i", "и"], ["j", "й"], ["k", "к"],
  ["l", "л"], ["m", "м"], ["n", "н"], ["o", "о"], ["p", "п"],
  ["r", "р"], ["s", "с"], ["t", "т"], ["u", "у"], ["f", "ф"],
  ["h", "х"], ["x", "х"], ["c", "ц"], ["w", "в"], ["y", "ы"],
  ["'", "ь"], ["`", "ъ"],
];

const LOOKUP = new Map(RULES);
const MAX_RULE = Math.max(...RULES.map(([latin]) => latin.length));

export function isLatin(text: string): boolean {
  return /[a-z]/i.test(text) && !/[а-яё]/i.test(text);
}

export function toCyrillic(text: string): string {
  if (!isLatin(text)) return text;
  const lowered = text.toLowerCase();
  let out = "";
  let i = 0;
  while (i < lowered.length) {
    let matched = false;
    for (let size = MAX_RULE; size > 0; size--) {
      const chunk = lowered.slice(i, i + size);
      const hit = LOOKUP.get(chunk);
      if (hit !== undefined) {
        out += hit;
        i += size;
        matched = true;
        break;
      }
    }
    if (!matched) {
      out += lowered[i];
      i += 1;
    }
  }
  return out;
}
