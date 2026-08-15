import type { Dictionary } from "../dictionary";
import { forDisplay } from "../stress";
import { stats, type Card } from "../srs";

interface Props {
  dictionary: Dictionary;
  cards: Card[];
  showStress: boolean;
  onRemove: (entryId: number) => void;
  onStartReview: () => void;
  onNavigate: (lemma: string) => void;
}

export function Notebook({
  dictionary,
  cards,
  showStress,
  onRemove,
  onStartReview,
  onNavigate,
}: Props) {
  const s = stats(cards);

  if (!cards.length) {
    return (
      <div className="empty">
        <p>生词本是空的。</p>
        <p className="muted">在查词结果里点「＋ 加入生词本」就能收词。</p>
      </div>
    );
  }

  return (
    <div className="notebook">
      <div className="stat-row">
        <Stat label="总计" value={s.total} />
        <Stat label="待复习" value={s.due} highlight={s.due > 0} />
        <Stat label="学习中" value={s.learning} />
        <Stat label="熟词" value={s.mature} />
      </div>

      <button
        type="button"
        className="primary wide"
        disabled={s.due === 0}
        onClick={onStartReview}
      >
        {s.due > 0 ? `开始复习（${s.due}）` : "今天没有待复习的词"}
      </button>

      <ul className="cards">
        {[...cards]
          .sort((a, b) => a.due - b.due)
          .map((card) => {
            const entry = dictionary.entry(card.entryId);
            if (!entry) return null;
            return (
              <li key={card.entryId}>
                <button
                  type="button"
                  className="card-word"
                  onClick={() => onNavigate(entry.l)}
                >
                  {forDisplay(entry.s, showStress)}
                </button>
                <span className="card-gloss">{entry.sen[0]?.zh}</span>
                <span className="card-due">{dueLabel(card)}</span>
                <button
                  type="button"
                  className="card-remove"
                  onClick={() => onRemove(card.entryId)}
                  aria-label="移除"
                >
                  ✕
                </button>
              </li>
            );
          })}
      </ul>
    </div>
  );
}

function Stat({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className={`stat${highlight ? " highlight" : ""}`}>
      <b>{value}</b>
      <span>{label}</span>
    </div>
  );
}

function dueLabel(card: Card): string {
  const ms = card.due - Date.now();
  if (ms <= 0) return "待复习";
  const days = Math.ceil(ms / 86_400_000);
  if (days <= 1) return "今天稍后";
  return `${days} 天后`;
}
