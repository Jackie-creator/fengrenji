import { useEffect, useMemo, useRef, useState } from "react";
import { CyrillicKeyboard } from "./components/CyrillicKeyboard";
import { EntryCard } from "./components/EntryCard";
import { Dictionary, loadBundle, type Bundle, type Result } from "./dictionary";
import { toCyrillic, isLatin } from "./translit";

const BUNDLE_URL = "./dictionary.json";

export function App() {
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [showStress, setShowStress] = useState(true);
  const [keyboard, setKeyboard] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadBundle(BUNDLE_URL).then(setBundle).catch((e) => setError(String(e)));
  }, []);

  const dictionary = useMemo(
    () => (bundle ? new Dictionary(bundle) : null),
    [bundle],
  );

  const results: Result[] = useMemo(
    () => (dictionary && query.trim() ? dictionary.lookup(query, 25) : []),
    [dictionary, query],
  );

  const converted = isLatin(query) ? toCyrillic(query) : null;

  const append = (char: string) => setQuery((q) => q + char);
  const navigate = (lemma: string) => {
    setQuery(lemma);
    input.current?.focus();
  };

  return (
    <div className="app">
      <header className="top">
        <h1>俄语助手</h1>
        <div className="controls">
          <label className="switch">
            <input
              type="checkbox"
              checked={showStress}
              onChange={(e) => setShowStress(e.target.checked)}
            />
            显示重音
          </label>
          <button
            type="button"
            className={keyboard ? "active" : ""}
            onClick={() => setKeyboard(!keyboard)}
          >
            ⌨ 西里尔键盘
          </button>
        </div>
      </header>

      <div className="searchbar">
        <input
          ref={input}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="输入俄语单词，或用拼音式拉丁字母（ruka → рука）"
          autoFocus
          spellCheck={false}
        />
        {query && (
          <button type="button" className="clear" onClick={() => setQuery("")}>
            ✕
          </button>
        )}
      </div>

      {converted && converted !== query && (
        <p className="hint">
          转写：{query} → <b>{converted}</b>
        </p>
      )}

      {keyboard && (
        <CyrillicKeyboard
          onKey={append}
          onBackspace={() => setQuery((q) => q.slice(0, -1))}
          onClear={() => setQuery("")}
        />
      )}

      {error && <p className="error">{error}</p>}
      {!bundle && !error && <p className="hint">正在加载词库…</p>}

      {bundle && !query.trim() && (
        <div className="empty">
          <p>
            词库 {bundle.stats.entries} 条词条 · {bundle.stats.forms} 个词形 ·
            完全离线
          </p>
          <p className="muted">
            可以直接输入任意变格变位形式：
            {["стали", "руку", "шёл", "людей", "городах"].map((w) => (
              <button key={w} type="button" className="link" onClick={() => navigate(w)}>
                {w}
              </button>
            ))}
          </p>
        </div>
      )}

      {query.trim() && results.length === 0 && bundle && (
        <p className="empty">没有找到「{query}」。</p>
      )}

      {results.length > 1 && results[0].kind === "exact" && (
        <p className="hint ambiguous">
          该词形有 {results.length} 种解读，以下全部列出。
        </p>
      )}
      {results.length > 0 && results[0].kind === "fuzzy" && (
        <p className="hint">没有完全匹配，以下是最接近的词：</p>
      )}
      {results.length > 0 && results[0].kind === "prefix" && (
        <p className="hint">以「{query}」开头的词：</p>
      )}

      <main>
        {results.map((result) => (
          <EntryCard
            key={`${result.entry.i}`}
            result={result}
            showStress={showStress}
            onNavigate={navigate}
          />
        ))}
      </main>
    </div>
  );
}
