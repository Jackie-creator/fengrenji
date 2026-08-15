import { describe, expect, it } from "vitest";
import { Dictionary, type Bundle } from "../dictionary";
import { searchKey, forDisplay } from "../stress";
import { toCyrillic } from "../translit";

/**
 * A miniature bundle in the same shape build.py emits. Keeping it hand-written
 * means these tests fail if the Python side changes the contract.
 */
const bundle: Bundle = {
  version: "test",
  generated: "",
  stats: { entries: 3, forms: 5, senses: 3 },
  entries: [
    {
      i: 0, l: "стать", s: "стать", p: "verb", asp: "perf",
      sen: [{ zh: "成为" }],
      f: { "past,plur": "ста́ли", "futr,1per,sing": "ста́ну" },
    },
    {
      i: 1, l: "сталь", s: "сталь", p: "noun", g: "femn",
      sen: [{ zh: "钢" }],
      f: { "gent,sing": "ста́ли", "nomn,sing": "сталь" },
    },
    {
      i: 2, l: "город", s: "го́род", p: "noun", g: "masc",
      sen: [{ zh: "城市" }],
      f: { "nomn,sing": "го́род", "nomn,plur": "города́" },
    },
  ],
  forms: {
    стали: [0, 1],
    стану: [0],
    сталь: [1],
    город: [2],
    города: [2],
  },
};

const dictionary = new Dictionary(bundle);

describe("tiered lookup, mirroring search.py", () => {
  it("returns every reading of an ambiguous form", () => {
    const results = dictionary.lookup("стали");
    expect(results.map((r) => r.entry.l).sort()).toEqual(["сталь", "стать"]);
    expect(results.every((r) => r.kind === "exact")).toBe(true);
  });

  it("labels which cell matched", () => {
    const [first] = dictionary.lookup("города");
    expect(first.via).toEqual({ tag: "nomn,plur", text: "города́" });
  });

  it("does not label the lemma itself as a matched cell", () => {
    expect(dictionary.lookup("город")[0].via).toBeUndefined();
  });

  it("transliterates Latin input", () => {
    const [first] = dictionary.lookup("gorod");
    expect(first.entry.l).toBe("город");
    expect(first.kind).toBe("translit");
  });

  it("completes a prefix", () => {
    const results = dictionary.lookup("горо");
    expect(results[0].kind).toBe("prefix");
    expect(results[0].entry.l).toBe("город");
  });

  it("tolerates a typo", () => {
    const results = dictionary.lookup("горад");
    expect(results[0].kind).toBe("fuzzy");
    expect(results[0].entry.l).toBe("город");
  });

  it("gives one hit per entry", () => {
    const ids = dictionary.lookup("стали").map((r) => r.entry.i);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("returns nothing for an unknown word", () => {
    expect(dictionary.lookup("щщщщщ")).toEqual([]);
  });
});

describe("normalisation", () => {
  it("ignores stress marks in the query", () => {
    expect(searchKey("ста́ли")).toBe("стали");
  });

  it("folds ё to е for search but keeps it for display", () => {
    expect(searchKey("шёл")).toBe("шел");
    expect(forDisplay("шёл", false)).toBe("шёл");
  });

  it("strips stress when the display toggle is off", () => {
    expect(forDisplay("го́род", false)).toBe("город");
    expect(forDisplay("го́род", true)).toBe("го́род");
  });

  it("transliterates the shapes people actually type", () => {
    expect(toCyrillic("privet")).toBe("привет");
    expect(toCyrillic("shchi")).toBe("щи");
  });
});
