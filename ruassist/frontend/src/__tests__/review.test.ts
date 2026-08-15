import { describe, expect, it } from "vitest";
import { buildQuestion, _internal } from "../components/Review";
import type { Entry } from "../dictionary";
import { newCard } from "../srs";

const { stressChoices } = _internal;

function entry(overrides: Partial<Entry> = {}): Entry {
  return {
    i: 0, l: "город", s: "го́род", p: "noun",
    sen: [{ zh: "城市" }], f: {}, ...overrides,
  };
}

describe("stress questions", () => {
  it("offers one choice per vowel and marks the right one", () => {
    const result = stressChoices(entry());
    expect(result).not.toBeNull();
    expect(result!.choices.map((c) => c.rendered)).toEqual(["го́род", "горо́д"]);
    expect(result!.choices[result!.answer].rendered).toBe("го́род");
  });

  it("skips monosyllables, which have nothing to ask about", () => {
    expect(stressChoices(entry({ l: "дом", s: "дом" }))).toBeNull();
  });

  it("skips words containing ё, which gives the answer away", () => {
    // ё is inherently stressed, so the question would answer itself.
    expect(stressChoices(entry({ l: "ребёнок", s: "ребёнок" }))).toBeNull();
  });

  it("skips words with no stress mark to test against", () => {
    expect(stressChoices(entry({ l: "город", s: "город" }))).toBeNull();
  });
});

describe("question selection", () => {
  it("starts a brand-new card on recognition, never a cold production test", () => {
    expect(buildQuestion(entry(), newCard(0)).kind).toBe("recall");
  });

  it("introduces stress and production once the word has been seen", () => {
    const kinds = new Set(
      [0, 1, 2, 3, 4, 5].map(
        (reps) => buildQuestion(entry(), { ...newCard(0), reps }).kind,
      ),
    );
    expect(kinds).toContain("recall");
    expect(kinds).toContain("produce");
    expect(kinds).toContain("stress");
  });

  it("never asks a stress question about a word that has no answer", () => {
    const monosyllable = entry({ l: "дом", s: "дом" });
    for (let reps = 0; reps < 8; reps++) {
      expect(buildQuestion(monosyllable, { ...newCard(0), reps }).kind).not.toBe("stress");
    }
  });
});
