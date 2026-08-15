import { useMemo, useState } from "react";
import type { Entry } from "../dictionary";
import { STRESS, searchKey, stripStress } from "../stress";
import { describeInterval, type Card, type Grade } from "../srs";

/**
 * Three question types, each attacking a different failure mode:
 *
 *  recall   Russian -> Chinese. The baseline.
 *  produce  Chinese -> Russian, typed. Recognition is far easier than recall,
 *           and only production catches "I know it when I see it".
 *  stress   Which syllable carries the stress. Russian-specific and the reason
 *           this project marks stress on every form: a learner who never gets
 *           tested on it will read every word wrong without ever noticing.
 */
export type QuestionKind = "recall" | "produce" | "stress";

interface StressChoice {
  /** Vowel index within the stressless word. */
  at: number;
  rendered: string;
}

export interface Question {
  kind: QuestionKind;
  entry: Entry;
  choices?: StressChoice[];
  answer?: number;
}

const VOWELS = "аеёиоуыэюя";

/** Vowel positions of a stressless word, so each can be offered as a choice. */
function vowelPositions(word: string): number[] {
  return [...word].flatMap((ch, i) => (VOWELS.includes(ch) ? [i] : []));
}

function stressChoices(entry: Entry): { choices: StressChoice[]; answer: number } | null {
  const plain = stripStress(entry.s);
  const positions = vowelPositions(plain);
  // ё is inherently stressed, so asking where the stress falls gives it away.
  if (positions.length < 2 || plain.includes("ё")) return null;

  const marked = entry.s.indexOf(STRESS);
  if (marked <= 0) return null;
  const answerAt = marked - 1;

  const choices = positions.map((at) => ({
    at,
    rendered: plain.slice(0, at + 1) + STRESS + plain.slice(at + 1),
  }));
  const answer = choices.findIndex((c) => c.at === answerAt);
  return answer < 0 ? null : { choices, answer };
}

export function buildQuestion(entry: Entry, card: Card): Question {
  // New cards start with recognition; production and stress come once the word
  // has been seen a few times, so the first encounter is not a cold test.
  const pool: QuestionKind[] = ["recall"];
  if (card.reps >= 2) pool.push("produce");
  const stress = stressChoices(entry);
  if (card.reps >= 1 && stress) pool.push("stress");

  const kind = pool[card.reps % pool.length];
  if (kind === "stress" && stress) {
    return { kind, entry, choices: stress.choices, answer: stress.answer };
  }
  return { kind, entry };
}

interface Props {
  question: Question;
  card: Card;
  showStress: boolean;
  onGrade: (grade: Grade) => void;
  remaining: number;
}

export function Review({ question, card, onGrade, remaining }: Props) {
  const [revealed, setRevealed] = useState(false);
  const [typed, setTyped] = useState("");
  const [picked, setPicked] = useState<number | null>(null);
  const entry = question.entry;

  // A new question object means a new card; reset the local answer state.
  const key = `${entry.i}-${card.reps}-${question.kind}`;
  const [seen, setSeen] = useState(key);
  if (seen !== key) {
    setSeen(key);
    setRevealed(false);
    setTyped("");
    setPicked(null);
  }

  const glosses = useMemo(() => entry.sen.map((s) => s.zh).join("；"), [entry]);
  const typedCorrect = searchKey(typed) === searchKey(entry.l);
  const stressCorrect = picked !== null && picked === question.answer;

  const grade = (g: Grade) => {
    onGrade(g);
  };

  return (
    <section className="review">
      <div className="review-head">
        <span className="badge">
          {question.kind === "recall" && "认词"}
          {question.kind === "produce" && "拼写"}
          {question.kind === "stress" && "重音"}
        </span>
        <span className="muted">还剩 {remaining}</span>
      </div>

      {question.kind === "recall" && (
        <>
          <p className="prompt ru-big">{entry.s}</p>
          {revealed ? <p className="answer">{glosses}</p> : null}
        </>
      )}

      {question.kind === "produce" && (
        <>
          <p className="prompt">{glosses}</p>
          <input
            className="answer-input"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            placeholder="写出俄语单词（可用拉丁字母转写）"
            spellCheck={false}
            disabled={revealed}
            onKeyDown={(e) => e.key === "Enter" && setRevealed(true)}
          />
          {revealed && (
            <p className={`answer ${typedCorrect ? "ok" : "bad"}`}>
              {typedCorrect ? "✓ " : "✕ 正确答案："}
              <span className="ru-big">{entry.s}</span>
            </p>
          )}
        </>
      )}

      {question.kind === "stress" && (
        <>
          <p className="prompt muted">重音在哪个音节？</p>
          <div className="choices">
            {question.choices!.map((choice, i) => (
              <button
                key={choice.at}
                type="button"
                disabled={revealed}
                className={
                  revealed
                    ? i === question.answer
                      ? "choice ok"
                      : i === picked
                        ? "choice bad"
                        : "choice"
                    : "choice"
                }
                onClick={() => {
                  setPicked(i);
                  setRevealed(true);
                }}
              >
                {choice.rendered}
              </button>
            ))}
          </div>
          {revealed && !stressCorrect && (
            <p className="answer bad">正确重音：<span className="ru-big">{entry.s}</span></p>
          )}
          {revealed && <p className="answer">{glosses}</p>}
        </>
      )}

      {!revealed ? (
        question.kind !== "stress" && (
          <button type="button" className="primary" onClick={() => setRevealed(true)}>
            显示答案
          </button>
        )
      ) : (
        <div className="grades">
          {(
            [
              ["again", "忘了"],
              ["hard", "有点难"],
              ["good", "记得"],
              ["easy", "太简单"],
            ] as [Grade, string][]
          ).map(([g, label]) => (
            <button key={g} type="button" className={`grade ${g}`} onClick={() => grade(g)}>
              {label}
              <small>{describeInterval(card, g)}</small>
            </button>
          ))}
        </div>
      )}

      {revealed && entry.sen[0]?.ex?.[0] && (
        <div className="review-example">
          <div className="ru">{entry.sen[0].ex[0][0]}</div>
          <div className="zh">{entry.sen[0].ex[0][1]}</div>
        </div>
      )}
    </section>
  );
}

export const _internal = { stressChoices, vowelPositions };
