/**
 * On-screen Cyrillic keyboard.
 *
 * Not a convenience: a Chinese user has no Cyrillic layout installed, so
 * without this (or transliteration) they cannot enter a query at all.
 */

const ROWS = [
  "йцукенгшщзхъ",
  "фывапролджэ",
  "ячсмитьбюё",
];

interface Props {
  onKey: (char: string) => void;
  onBackspace: () => void;
  onClear: () => void;
}

export function CyrillicKeyboard({ onKey, onBackspace, onClear }: Props) {
  return (
    <div className="keyboard">
      {ROWS.map((row) => (
        <div className="keyboard-row" key={row}>
          {[...row].map((char) => (
            <button key={char} type="button" onClick={() => onKey(char)}>
              {char}
            </button>
          ))}
        </div>
      ))}
      <div className="keyboard-row">
        <button type="button" className="wide" onClick={onBackspace}>
          ← 退格
        </button>
        <button type="button" className="wide" onClick={onClear}>
          清空
        </button>
      </div>
    </div>
  );
}
