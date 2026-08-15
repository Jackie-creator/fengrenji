import { describe, expect, it } from "vitest";
import {
  LEARNING_STEPS, dueCards, isDue, newCard, schedule, stats, type Card,
} from "../srs";

const NOW = 1_700_000_000_000;
const DAY = 86_400_000;
const MINUTE = 60_000;

function graduated(overrides: Partial<Card> = {}): Card {
  return { ...newCard(1, NOW), step: null, interval: 10, reps: 5, ...overrides };
}

describe("learning steps", () => {
  it("starts a new card in the first step, due immediately", () => {
    const card = newCard(1, NOW);
    expect(card.step).toBe(0);
    expect(isDue(card, NOW)).toBe(true);
  });

  it("advances through the steps on good", () => {
    const card = schedule(newCard(1, NOW), "good", NOW);
    expect(card.step).toBe(1);
    expect(card.due).toBe(NOW + LEARNING_STEPS[1] * MINUTE);
  });

  it("graduates to days after the last step", () => {
    let card = newCard(1, NOW);
    for (const _ of LEARNING_STEPS) card = schedule(card, "good", NOW);
    expect(card.step).toBeNull();
    expect(card.interval).toBe(1);
  });

  it("hard repeats the current step rather than advancing", () => {
    const card = schedule(newCard(1, NOW), "hard", NOW);
    expect(card.step).toBe(0);
  });

  it("easy skips the remaining steps", () => {
    const card = schedule(newCard(1, NOW), "easy", NOW);
    expect(card.step).toBeNull();
    expect(card.interval).toBe(4);
  });

  it("again sends the card back to the first step", () => {
    const card = schedule(schedule(newCard(1, NOW), "good", NOW), "again", NOW);
    expect(card.step).toBe(0);
  });
});

describe("review scheduling", () => {
  it("multiplies the interval by ease on good", () => {
    const card = schedule(graduated({ interval: 10, ease: 2.5 }), "good", NOW);
    expect(card.interval).toBe(25);
  });

  it("always grows the interval by at least a day", () => {
    // Rounding could otherwise leave a 1-day card at 1 day forever.
    const card = schedule(graduated({ interval: 1, ease: 1.3 }), "hard", NOW);
    expect(card.interval).toBeGreaterThan(1);
  });

  it("halves rather than resets on a lapse", () => {
    const card = schedule(graduated({ interval: 20 }), "again", NOW);
    expect(card.interval).toBe(10);
    expect(card.lapses).toBe(1);
    expect(card.step).toBe(0);
  });

  it("lowers ease on again and hard, raises it on easy", () => {
    expect(schedule(graduated(), "again", NOW).ease).toBeLessThan(2.5);
    expect(schedule(graduated(), "hard", NOW).ease).toBeLessThan(2.5);
    expect(schedule(graduated(), "easy", NOW).ease).toBeGreaterThan(2.5);
  });

  it("clamps ease to a usable band", () => {
    let card = graduated();
    for (let i = 0; i < 20; i++) card = schedule(card, "again", NOW);
    expect(card.ease).toBeGreaterThanOrEqual(1.3);

    card = graduated();
    for (let i = 0; i < 20; i++) card = schedule(card, "easy", NOW);
    expect(card.ease).toBeLessThanOrEqual(3.0);
  });

  it("counts every answer as a repetition", () => {
    expect(schedule(graduated({ reps: 4 }), "good", NOW).reps).toBe(5);
  });
});

describe("queue and stats", () => {
  it("returns only due cards", () => {
    const cards = [
      graduated({ entryId: 1, due: NOW - DAY }),
      graduated({ entryId: 2, due: NOW + DAY }),
    ];
    expect(dueCards(cards, NOW).map((c) => c.entryId)).toEqual([1]);
  });

  it("puts learning cards ahead of review cards", () => {
    const cards = [
      graduated({ entryId: 1, due: NOW - 2 * DAY }),
      { ...newCard(2, NOW), due: NOW - MINUTE },
    ];
    expect(dueCards(cards, NOW)[0].entryId).toBe(2);
  });

  it("classifies maturity by interval", () => {
    const s = stats(
      [
        newCard(1, NOW),
        graduated({ entryId: 2, interval: 5 }),
        graduated({ entryId: 3, interval: 40 }),
      ],
      NOW,
    );
    expect(s).toMatchObject({ total: 3, learning: 1, young: 1, mature: 1 });
  });
});
