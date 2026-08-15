/**
 * Pronunciation via the Web Speech API.
 *
 * Uses the voices the operating system already has, which keeps the app's own
 * payload at zero: bundling recorded audio for a few thousand words would cost
 * tens of megabytes and undo the offline size budget entirely.
 *
 * Honest caveat: "offline" here depends on the platform. Desktop Windows, macOS
 * and Android generally synthesise locally once a Russian voice is installed;
 * some browsers route synthesis through a server. Speech is therefore treated
 * as an enhancement -- the button is hidden when no Russian voice exists rather
 * than failing silently when pressed.
 *
 * Stress marks are stripped before speaking. U+0301 is a combining diacritic
 * that engines either ignore or read as noise, and they have their own
 * pronunciation lexicons. ё is kept: there it is a real letter and changes the
 * vowel.
 */

import { stripStress } from "./stress";

let cache: SpeechSynthesisVoice[] | null = null;

function synth(): SpeechSynthesis | null {
  return typeof window !== "undefined" && "speechSynthesis" in window
    ? window.speechSynthesis
    : null;
}

export function russianVoices(): SpeechSynthesisVoice[] {
  const speech = synth();
  if (!speech) return [];
  // Voices load asynchronously in some browsers, so an empty list is never
  // memoised -- otherwise the first call permanently disables speech.
  if (cache && cache.length) return cache;
  const voices = speech
    .getVoices()
    .filter((v) => v.lang.toLowerCase().startsWith("ru"));
  if (voices.length) cache = voices;
  return voices;
}

/** Subscribe to the browser publishing its voice list. Returns an unsubscribe. */
export function onVoicesReady(callback: () => void): () => void {
  const speech = synth();
  if (!speech) return () => {};
  const handler = () => {
    cache = null;
    callback();
  };
  speech.addEventListener("voiceschanged", handler);
  return () => speech.removeEventListener("voiceschanged", handler);
}

export function canSpeak(): boolean {
  return russianVoices().length > 0;
}

export function speak(text: string, rate = 0.9): void {
  const speech = synth();
  const voices = russianVoices();
  if (!speech || !voices.length) return;

  speech.cancel(); // a second tap replaces rather than queues
  const utterance = new SpeechSynthesisUtterance(stripStress(text));
  utterance.voice = voices[0];
  utterance.lang = voices[0].lang;
  utterance.rate = rate; // slightly slow: this is a learning tool
  speech.speak(utterance);
}
