import { useMemo } from "react";
import type { Dictionary } from "../dictionary";
import type { Card } from "../srs";

/**
 * Level-based word books.
 *
 * The levels come from each entry's `lv` tags, so a book is a view over the
 * lexicon rather than a separate list that could drift out of sync with it.
 */
const BOOKS: [string, string][] = [
  ["A1", "入门 A1"],
  ["A2", "初级 A2"],
  ["B1", "中级 B1"],
  ["高考", "高考俄语"],
  ["ТРКИ-1", "ТРКИ 一级"],
  ["ТРКИ-2", "ТРКИ 二级"],
  ["专四", "俄语专四"],
];

interface Props {
  dictionary: Dictionary;
  cards: Card[];
  onAddMany: (entryIds: number[]) => void;
}

export function WordBooks({ dictionary, cards, onAddMany }: Props) {
  const inNotebook = useMemo(() => new Set(cards.map((c) => c.entryId)), [cards]);

  const books = useMemo(
    () =>
      BOOKS.map(([tag, label]) => {
        const ids = dictionary.bundle.entries
          .filter((e) => e.lv?.includes(tag))
          .map((e) => e.i);
        return { tag, label, ids, added: ids.filter((i) => inNotebook.has(i)).length };
      }).filter((b) => b.ids.length > 0),
    [dictionary, inNotebook],
  );

  return (
    <div className="books">
      <p className="muted">
        词书是按词条的等级标签生成的视图，不是另一份清单——词库改了，词书跟着改。
      </p>
      {books.map((book) => {
        const pending = book.ids.length - book.added;
        return (
          <div className="book" key={book.tag}>
            <div className="book-head">
              <b>{book.label}</b>
              <span className="muted">
                {book.added} / {book.ids.length}
              </span>
            </div>
            <div className="progress">
              <div style={{ width: `${(book.added / book.ids.length) * 100}%` }} />
            </div>
            <button
              type="button"
              disabled={pending === 0}
              onClick={() => onAddMany(book.ids.filter((i) => !inNotebook.has(i)))}
            >
              {pending === 0 ? "已全部加入" : `加入剩余 ${pending} 词`}
            </button>
          </div>
        );
      })}
    </div>
  );
}
