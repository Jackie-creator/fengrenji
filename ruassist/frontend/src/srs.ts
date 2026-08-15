/**
 * Spaced repetition scheduling.
 *
 * An SM-2 variant with explicit learning steps. Two deliberate departures from
 * textbook SM-2:
 *
 * 1. New cards go through short learning steps before graduating to days. A word
 *    seen once and then not again for a day is usually just forgotten.
 * 2. A lapse does not reset the interval to zero. Re-learning a word you once
 *    knew is faster than learning it cold, and resetting punishes the learner
 *    for reviewing at all.
 *
 * Everything here is pure: given a card and a grade it returns the next card.
 * That keeps it testable and keeps storage a separate concern.
 */

export type Grade = "again" | "hard" | "good" | "easy";

export interface Card {
  entryId: number;
  /** Difficulty multiplier; lower means the word comes back sooner. */
  ease: number;
  /** Days until the next review. 0 while still in learning steps. */
  interval: number;
  /** Index into LEARNING_STEPS, or null once graduated. */
  step: number | null;
  due: number;
  reps: number;
  lapses: number;
  added: number;
}

/** Minutes. Short enough to finish inside one sitting. */
export const LEARNING_STEPS = [1, 10];

const MIN_EASE = 1.3;
const MAX_EASE = 3.0;
const DEFAULT_EASE = 2.5;
const GRADUATING_INTERVAL = 1;
const EASY_INTERVAL = 4;

const MINUTE = 60_000;
const DAY = 86_400_000;

export function newCard(entryId: number, now = Date.now()): Card {
  return {
    entryId,
    ease: DEFAULT_EASE,
    interval: 0,
    step: 0,
    due: now,
    reps: 0,
    lapses: 0,
    added: now,
  };
}

export function schedule(card: Card, grade: Grade, now = Date.now()): Card {
  const next: Card = { ...card, reps: card.reps + 1 };

  if (card.step !== null) return scheduleLearning(next, grade, now);
  return scheduleReview(next, grade, now);
}

function scheduleLearning(card: Card, grade: Grade, now: number): Card {
  if (grade === "again") {
    return { ...card, step: 0, due: now + LEARNING_STEPS[0] * MINUTE };
  }
  if (grade === "easy") {
    // Skip the remaining steps entirely: the learner already knows this one.
    return { ...card, step: null, interval: EASY_INTERVAL, due: now + EASY_INTERVAL * DAY };
  }

  const step = (card.step ?? 0) + (grade === "hard" ? 0 : 1);
  if (step >= LEARNING_STEPS.length) {
    return {
      ...card,
      step: null,
      interval: GRADUATING_INTERVAL,
      due: now + GRADUATING_INTERVAL * DAY,
    };
  }
  return { ...card, step, due: now + LEARNING_STEPS[step] * MINUTE };
}

function scheduleReview(card: Card, grade: Grade, now: number): Card {
  let { ease, interval } = card;

  switch (grade) {
    case "again":
      // Halve rather than reset: relearning is faster than learning cold.
      return {
        ...card,
        ease: clampEase(ease - 0.2),
        interval: Math.max(1, Math.round(interval * 0.5)),
        lapses: card.lapses + 1,
        step: 0,
        due: now + LEARNING_STEPS[0] * MINUTE,
      };
    case "hard":
      ease = clampEase(ease - 0.15);
      interval = Math.max(interval + 1, Math.round(interval * 1.2));
      break;
    case "good":
      interval = Math.max(interval + 1, Math.round(interval * ease));
      break;
    case "easy":
      ease = clampEase(ease + 0.15);
      interval = Math.max(interval + 1, Math.round(interval * ease * 1.3));
      break;
  }

  return { ...card, ease, interval, due: now + interval * DAY };
}

function clampEase(value: number): number {
  return Math.min(MAX_EASE, Math.max(MIN_EASE, Number(value.toFixed(2))));
}

export function isDue(card: Card, now = Date.now()): boolean {
  return card.due <= now;
}

export function dueCards(cards: Card[], now = Date.now()): Card[] {
  // Learning cards first: they are the ones at risk of being forgotten today.
  return cards
    .filter((c) => isDue(c, now))
    .sort((a, b) => Number(b.step !== null) - Number(a.step !== null) || a.due - b.due);
}

export interface Stats {
  total: number;
  due: number;
  learning: number;
  young: number;
  mature: number;
}

/** A card is "mature" once its interval passes three weeks. */
export function stats(cards: Card[], now = Date.now()): Stats {
  return {
    total: cards.length,
    due: cards.filter((c) => isDue(c, now)).length,
    learning: cards.filter((c) => c.step !== null).length,
    young: cards.filter((c) => c.step === null && c.interval < 21).length,
    mature: cards.filter((c) => c.step === null && c.interval >= 21).length,
  };
}

export function describeInterval(card: Card, grade: Grade, now = Date.now()): string {
  const next = schedule(card, grade, now);
  const ms = next.due - now;
  if (ms < 60 * MINUTE) return `${Math.round(ms / MINUTE)} 分钟`;
  if (ms < DAY) return `${Math.round(ms / (60 * MINUTE))} 小时`;
  const days = Math.round(ms / DAY);
  return days >= 30 ? `${(days / 30).toFixed(1)} 个月` : `${days} 天`;
}
