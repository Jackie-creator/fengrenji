import type { Entry } from "../dictionary";
import { forDisplay } from "../stress";

const CASES: [string, string][] = [
  ["nomn", "主格"],
  ["gent", "属格"],
  ["datv", "与格"],
  ["accs", "宾格"],
  ["ablt", "工具格"],
  ["loct", "前置格"],
];

const PERSONS: [string, string][] = [
  ["1per,sing", "я"],
  ["2per,sing", "ты"],
  ["3per,sing", "он / она́"],
  ["1per,plur", "мы"],
  ["2per,plur", "вы"],
  ["3per,plur", "они́"],
];

/** Cells are keyed by a sorted grammeme list, so look them up the same way. */
function cell(entry: Entry, ...tags: string[]): string | undefined {
  return entry.f[[...tags].sort().join(",")];
}

interface Props {
  entry: Entry;
  showStress: boolean;
}

export function ParadigmTable({ entry, showStress }: Props) {
  const show = (text: string | undefined) =>
    text ? forDisplay(text, showStress) : "—";

  if (entry.p === "noun") {
    return (
      <table className="paradigm">
        <thead>
          <tr>
            <th />
            <th>单数</th>
            <th>复数</th>
          </tr>
        </thead>
        <tbody>
          {CASES.map(([c, label]) => (
            <tr key={c}>
              <th>{label}</th>
              <td>{show(cell(entry, "sing", c))}</td>
              <td>{show(cell(entry, "plur", c))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  if (entry.p === "verb") {
    // A perfective has no present tense -- it conjugates into the future.
    const tense = entry.asp === "impf" ? "pres" : "futr";
    const past = ["masc", "femn", "neut", "plur"]
      .map((g) => cell(entry, "past", g))
      .filter(Boolean) as string[];
    const imperative = ["sing", "plur"]
      .map((n) => cell(entry, "impr", n))
      .filter(Boolean) as string[];

    return (
      <table className="paradigm">
        <thead>
          <tr>
            <th colSpan={2}>{entry.asp === "impf" ? "现在时" : "将来时"}</th>
          </tr>
        </thead>
        <tbody>
          {PERSONS.map(([key, label]) => {
            const [person, number] = key.split(",");
            const form = cell(entry, tense, person, number);
            return form ? (
              <tr key={key}>
                <th>{label}</th>
                <td>{show(form)}</td>
              </tr>
            ) : null;
          })}
          {past.length > 0 && (
            <tr>
              <th>过去时</th>
              <td>{past.map((f) => forDisplay(f, showStress)).join(" · ")}</td>
            </tr>
          )}
          {imperative.length > 0 && (
            <tr>
              <th>命令式</th>
              <td>{imperative.map((f) => forDisplay(f, showStress)).join(" · ")}</td>
            </tr>
          )}
        </tbody>
      </table>
    );
  }

  if (entry.p === "adj") {
    return (
      <table className="paradigm">
        <thead>
          <tr>
            <th />
            <th>阳</th>
            <th>阴</th>
            <th>中</th>
            <th>复</th>
          </tr>
        </thead>
        <tbody>
          {CASES.slice(0, 5).map(([c, label]) => (
            <tr key={c}>
              <th>{label}</th>
              {["masc", "femn", "neut"].map((g) => (
                <td key={g}>{show(cell(entry, "adjf", "sing", g, c))}</td>
              ))}
              <td>{show(cell(entry, "adjf", "plur", c))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  const forms = Object.entries(entry.f);
  if (forms.length <= 1) return null;
  return (
    <table className="paradigm">
      <tbody>
        {forms.map(([tag, text]) => (
          <tr key={tag}>
            <th>{tag}</th>
            <td>{forDisplay(text, showStress)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
