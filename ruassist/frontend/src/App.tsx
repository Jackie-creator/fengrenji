import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CyrillicKeyboard } from "./components/CyrillicKeyboard";
import { EntryCard } from "./components/EntryCard";
import { Notebook } from "./components/Notebook";
import { Review, buildQuestion } from "./components/Review";
import { WordBooks } from "./components/WordBooks";
import { Dictionary, loadBundle, type Bundle, type Result } from "./dictionary";
import { dueCards, newCard, schedule, stats, type Card, type Grade } from "./srs";
import { loadCards, loadSettings, saveCards, saveSettings } from "./storage";
import { isLatin, toCyrillic } from "./translit";

const BUNDLE_URL = "./dictionary.json";

type Tab = "search" | "notebook" | "books";

export function App() {
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("search");
  const [query, setQuery] = useState("");
  const [keyboard, setKeyboard] = useState(false);
  const [cards, setCards] = useState<Card[]>(() => loadCards());
  const [settings, setSettings] = useState(() => loadSettings());
  const [session, setSession] = useState<number[] | null>(null);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadBundle(BUNDLE_URL).then(setBundle).catch((e) => setError(String(e)));
  }, []);

  useEffect(() => saveCards(cards), [cards]);
  useEffect(() => saveSettings(settings), [settings]);

  const dictionary = useMemo(() => (bundle ? new Dictionary(bundle) : null), [bundle]);
  const showStress = settings.showStress;

  const results: Result[] = useMemo(
    () => (dictionary && query.trim() ? dictionary.lookup(query, 25) : []),
    [dictionary, query],
  );

  const inNotebook = useMemo(() => new Set(cards.map((c) => c.entryId)), [cards]);
  const due = useMemo(() => stats(cards).due, [cards]);

  const navigate = useCallback((lemma: string) => {
    setTab("search");
    setQuery(lemma);
    input.current?.focus();
  }, []);

  const addCard = useCallback((entryId: number) => {
    setCards((cs) => (cs.some((c) => c.entryId === entryId) ? cs : [...cs, newCard(entryId)]));
  }, []);

  const addMany = useCallback((ids: number[]) => {
    setCards((cs) => {
      const have = new Set(cs.map((c) => c.entryId));
      return [...cs, ...ids.filter((i) => !have.has(i)).map((i) => newCard(i))];
    });
  }, []);

  const removeCard = useCallback((entryId: number) => {
    setCards((cs) => cs.filter((c) => c.entryId !== entryId));
  }, []);

  const startReview = useCallback(() => {
    const queue = dueCards(cards).slice(0, settings.dailyLimit).map((c) => c.entryId);
    setSession(queue);
  }, [cards, settings.dailyLimit]);

  const gradeCurrent = useCallback(
    (grade: Grade) => {
      setSession((queue) => {
        if (!queue?.length) return queue;
        const [head, ...rest] = queue;
        setCards((cs) =>
          cs.map((c) => (c.entryId === head ? schedule(c, grade) : c)),
        );
        // "Again" sends the card to the back of this session rather than out of
        // it: the point of a lapse is to see the word again today.
        return grade === "again" ? [...rest, head] : rest;
      });
    },
    [],
  );

  const converted = isLatin(query) ? toCyrillic(query) : null;

  if (error) return <div className="app"><p className="error">{error}</p></div>;
  if (!bundle || !dictionary) return <div className="app"><p className="hint">正在加载词库…</p></div>;

  const currentCard =
    session?.length ? cards.find((c) => c.entryId === session[0]) : undefined;

  return (
    <div className="app">
      <header className="top">
        <h1>俄语助手</h1>
        <div className="controls">
          <label className="switch">
            <input
              type="checkbox"
              checked={showStress}
              onChange={(e) => setSettings({ ...settings, showStress: e.target.checked })}
            />
            显示重音
          </label>
        </div>
      </header>

      <nav className="tabs">
        {(
          [
            ["search", "查词"],
            ["notebook", `生词本${due ? ` · ${due}` : ""}`],
            ["books", "词书"],
          ] as [Tab, string][]
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={tab === id ? "tab active" : "tab"}
            onClick={() => {
              setTab(id);
              setSession(null);
            }}
          >
            {label}
          </button>
        ))}
      </nav>

      {tab === "search" && (
        <>
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
              <button type="button" className="clear" onClick={() => setQuery("")}>✕</button>
            )}
          </div>

          <div className="row-between">
            {converted && converted !== query ? (
              <p className="hint">转写：{query} → <b>{converted}</b></p>
            ) : <span />}
            <button
              type="button"
              className={keyboard ? "active small" : "small"}
              onClick={() => setKeyboard(!keyboard)}
            >
              ⌨ 西里尔键盘
            </button>
          </div>

          {keyboard && (
            <CyrillicKeyboard
              onKey={(c) => setQuery((q) => q + c)}
              onBackspace={() => setQuery((q) => q.slice(0, -1))}
              onClear={() => setQuery("")}
            />
          )}

          {!query.trim() && (
            <div className="empty">
              <p>词库 {bundle.stats.entries} 条词条 · {bundle.stats.forms} 个词形 · 完全离线</p>
              <p className="muted">
                可以直接输入任意变格变位形式：
                {["стали", "руку", "шёл", "людей", "городах"].map((w) => (
                  <button key={w} type="button" className="link" onClick={() => navigate(w)}>{w}</button>
                ))}
              </p>
            </div>
          )}

          {query.trim() && results.length === 0 && <p className="empty">没有找到「{query}」。</p>}
          {results.length > 1 && results[0].kind === "exact" && (
            <p className="hint ambiguous">该词形有 {results.length} 种解读，以下全部列出。</p>
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
                key={result.entry.i}
                result={result}
                showStress={showStress}
                onNavigate={navigate}
                inNotebook={inNotebook.has(result.entry.i)}
                onAdd={() => addCard(result.entry.i)}
                onRemove={() => removeCard(result.entry.i)}
              />
            ))}
          </main>
        </>
      )}

      {tab === "notebook" &&
        (session && currentCard ? (
          <>
            <Review
              question={buildQuestion(dictionary.entry(currentCard.entryId), currentCard)}
              card={currentCard}
              showStress={showStress}
              onGrade={gradeCurrent}
              remaining={session.length}
            />
            <button type="button" className="small" onClick={() => setSession(null)}>
              结束这轮
            </button>
          </>
        ) : session ? (
          <div className="empty">
            <p>这轮复习完成了。</p>
            <button type="button" className="primary" onClick={() => setSession(null)}>
              返回生词本
            </button>
          </div>
        ) : (
          <Notebook
            dictionary={dictionary}
            cards={cards}
            showStress={showStress}
            onRemove={removeCard}
            onStartReview={startReview}
            onNavigate={navigate}
          />
        ))}

      {tab === "books" && (
        <WordBooks dictionary={dictionary} cards={cards} onAddMany={addMany} />
      )}
    </div>
  );
}
