import { useState } from "react";
import type { Entry, Result } from "../dictionary";
import { forDisplay } from "../stress";
import { ParadigmTable } from "./ParadigmTable";

const POS_LABEL: Record<string, string> = {
  noun: "名词", verb: "动词", adj: "形容词", adv: "副词",
  pron: "代词", num: "数词", prep: "前置词", conj: "连接词",
  part: "语气词", interj: "感叹词", predic: "谓语副词",
};

const GENDER_LABEL: Record<string, string> = {
  masc: "阳性", femn: "阴性", neut: "中性", common: "通性",
};

const ASPECT_LABEL: Record<string, string> = {
  impf: "未完成体", perf: "完成体", both: "兼体",
};

/** Grammar facts worth showing as chips rather than burying in prose. */
function badges(entry: Entry): string[] {
  const out = [POS_LABEL[entry.p] ?? entry.p];
  if (entry.g) out.push(GENDER_LABEL[entry.g] ?? entry.g);
  if (entry.an === "anim") out.push("动物名词");
  if (entry.asp) out.push(ASPECT_LABEL[entry.asp] ?? entry.asp);
  if (entry.num === "plur") out.push("只用复数");
  if (entry.mg === "uni") out.push("定向");
  if (entry.mg === "multi") out.push("不定向");
  return out;
}

interface Props {
  result: Result;
  showStress: boolean;
  onNavigate: (lemma: string) => void;
  inNotebook: boolean;
  onAdd: () => void;
  onRemove: () => void;
}

export function EntryCard({
  result, showStress, onNavigate, inNotebook, onAdd, onRemove,
}: Props) {
  const [open, setOpen] = useState(false);
  const entry = result.entry;

  return (
    <article className="entry">
      <header>
        <h2>
          {forDisplay(entry.s, showStress)}
          {entry.hom ? <sup>{entry.hom}</sup> : null}
        </h2>
        <div className="badges">
          {badges(entry).map((b) => (
            <span className="badge" key={b}>{b}</span>
          ))}
          {entry.lv?.map((l) => (
            <span className="badge level" key={l}>{l}</span>
          ))}
        </div>
      </header>

      {result.via && (
        <p className="via">
          查询词形 <b>{forDisplay(result.via.text, showStress)}</b>
          <span className="tag">{result.via.tag}</span>
        </p>
      )}

      {entry.pair && (
        <p className="pair">
          体对：
          <button type="button" className="link" onClick={() => onNavigate(entry.pair!)}>
            {entry.pair}
          </button>
        </p>
      )}
      {entry.mp && (
        <p className="pair">
          运动动词对：
          <button type="button" className="link" onClick={() => onNavigate(entry.mp!)}>
            {entry.mp}
          </button>
        </p>
      )}

      <ol className="senses">
        {entry.sen.map((sense, n) => (
          <li key={n}>
            <div className="gloss">
              {sense.zh}
              {sense.lb?.map((l) => (
                <span className="label" key={l}>{l}</span>
              ))}
            </div>
            {sense.col && <div className="collocations">{sense.col.map((c) => forDisplay(c, showStress)).join(" · ")}</div>}
            {sense.ex?.map(([ru, zh], k) => (
              <div className="example" key={k}>
                <div className="ru">{forDisplay(ru, showStress)}</div>
                <div className="zh">{zh}</div>
              </div>
            ))}
          </li>
        ))}
      </ol>

      {entry.n?.aspect && <Note title="体的用法" body={entry.n.aspect} />}
      {entry.n?.errors && <Note title="常见错误" body={entry.n.errors} kind="warn" />}
      {entry.n?.notes && <Note title="说明" body={entry.n.notes} />}

      <div className="entry-actions">
        <button type="button" className="toggle" onClick={() => setOpen(!open)}>
          {open ? "收起变位表" : "展开变位表"}
          {entry.z && <span className="index">«{entry.z}»</span>}
        </button>
        <button
          type="button"
          className={inNotebook ? "toggle in-notebook" : "toggle"}
          onClick={inNotebook ? onRemove : onAdd}
        >
          {inNotebook ? "✓ 已在生词本" : "＋ 加入生词本"}
        </button>
      </div>
      {open && <ParadigmTable entry={entry} showStress={showStress} />}
    </article>
  );
}

function Note({ title, body, kind }: { title: string; body: string; kind?: "warn" }) {
  return (
    <div className={`note${kind ? ` ${kind}` : ""}`}>
      <strong>{title}</strong>
      {body.trim().split("\n").map((line, i) => (
        <p key={i}>{line}</p>
      ))}
    </div>
  );
}
