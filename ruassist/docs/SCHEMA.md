# 词条 Schema 定稿（v0.1）

可执行定义在 `src/ruassist/schema.py`，本文是它的说明与约定。两者不一致时以代码为准。

## 0. 设计原则

> **作者提供分类与意义，引擎提供词形。**

词条**不存储任何变格变位形式**。作者只标注一个扎利兹尼亚克范式索引（`zaliznyak`），
构建期由形态引擎把它展开成完整词形表。只有范式无法生成的补充形式（мать 的 -ер-、
идти 的 шёл、взять 的 возьму́）才手写进 `form_overrides`。

这样做的理由很实际：手写词形会出错，而且错了没人能发现。一个动词有 100 多个词形，
手写 5,000 个词条等于手写 30 万个带重音的形式——必然引入几百处静默错误，
学习者只会照着背下去。把手写面缩到最小、生成面放到最大，是唯一可控的做法。

## 1. 重音表示法

| 项 | 约定 |
|---|---|
| 重音符号 | `U+0301` COMBINING ACUTE ACCENT，紧跟在重读元音之后 |
| 规范化 | 全部走 `stress.normalize()`，`U+00B4`、`U+02CA`、预组合字符一律折算成 `U+0301` |
| 单音节词 | 不标（`дом`、`стол`） |
| 含 ё 的词 | ё 自带重音，不额外标（`ребёнок`） |
| 前置词吸音 | `взять за́ руку` —— 前置词标重音，后面的词合法地不带重音 |
| `lemma` 字段 | **不带**重音（它是检索键） |
| `stress` 字段 | 带重音（它是显示形式） |

派生形式由代码生成，不入库手写：

- `strip_stress()` —— 去重音，用户输入和索引用
- `fold_yo()` —— ё → е，因为实际文本里 ё 常写成 е
- `search_key()` —— 去重音 + 折 ё + 小写，最终检索键

## 2. 字段总表

### 身份

| 字段 | 类型 | 说明 |
|---|---|---|
| `lemma` | str | 规范形式，无重音 |
| `stress` | str | 同一形式，带重音 |
| `pos` | enum | noun / verb / adj / adv / pron / num / prep / conj / part / interj / predic |
| `homonym_id` | int? | 区分同形词：мир¹ 世界 / мир² 和平 |

### 形态挂钩

| 字段 | 类型 | 说明 |
|---|---|---|
| `zaliznyak` | str? | 范式索引，驱动词形生成 |
| `form_overrides` | dict | 范式生成不出来的补充形式，键是语法标签 |
| `indeclinable` | bool | 不变格（метро́、кино́） |

### 名词

`gender`(masc/femn/neut/common)、`animacy`(anim/inan)、`number_only`(sing/plur)、
`plural_lemma`（补充复数：человек → люди）

### 动词

`aspect`(impf/perf/both)、`aspect_pair`、`transitivity`、`reflexive`、
`government`（支配格）、`motion_group`(uni/multi/prefixed)、`motion_partner`

### 形容词

`short_form`、`comparative`、`superlative`

### 词典学

`level`、`freq_rank`、`senses`、`synonyms`、`antonyms`、`word_family`

### 教学注释 —— 相对通用双语词典的差异所在

| 字段 | 说明 |
|---|---|
| `aspect_note` | 体的用法辨析 |
| `common_errors` | 中国学生高频错误 |
| `notes` | 其他说明（俄汉词汇不对应、固定搭配、读音例外） |

### 溯源

| 字段 | 说明 |
|---|---|
| `verify` | 需与 OpenCorpora / OpenRussian 交叉核对的字段名，发布前必须清空 |
| `audio` | 音频引用 |

### Sense

`zh`（中文释义，必填）、`en`（对齐开源数据用）、`labels`（语域）、
`government`（该义项特有支配）、`collocations`、`examples`

## 3. 语法标签集

`form_overrides` 的键是逗号分隔的语法标签，**与 OpenCorpora 兼容**，
这样形态引擎能直接消费同一套标签：

```
数      sing plur
格      nomn gent datv accs ablt loct
        gen2（部分格 ча́ю） loc2（处所格 в лесу́） voct（呼格残留 Бо́же）
性      masc femn neut
人称    1per 2per 3per
时/式   pres past futr infn impr
形动词  prtf prts grnd actv pssv
形容词  adjf adjs comp supr
```

示例：`past,femn: взяла́`、`futr,1per,sing: возьму́`、`sing,accs: ру́ку`

## 4. 形态引擎接口约定（M1 实现）

```python
class Form(TypedDict):
    text:  str            # 带重音的显示形式
    plain: str            # search_key()，索引用
    tags:  frozenset[str] # 上表的语法标签

def inflect(entry: LexEntry) -> dict[str, Form]:
    """由 zaliznyak 索引生成全部词形，再用 form_overrides 覆盖。"""
```

引擎必须满足：

1. **每个生成词形都带重音。** 缺重音视为构建失败，不是警告。
2. **`form_overrides` 覆盖生成结果**，不是补充；键冲突时以手写为准。
3. **动物性影响第四格**：anim 的复数第四格 = 第二格，inan 的 = 第一格。
4. **完成体没有现在时**，只有将来时；未完成体没有简单将来时。（已由测试守住）
5. 生成失败必须报错并指名词条，不允许静默产出残缺范式。

## 5. 构建管道

```
YAML 词条
   │  1. schema 校验（逐条）
   │  2. lexicon 校验（跨条：体对互指、同形词去重、悬空引用）
   ▼
inflect() 展开全部词形
   │  3. 重音完整性校验
   ▼
词形 → 词元 倒排索引
   │  4. 压缩成 FST/DAWG
   ▼
SQLite + FST 词包  →  客户端离线加载
```

第 1、2 步已实现（`python -m ruassist.validate data/lexicon`），第 3–5 步属于 M1/M2。

**离线设计的关键取舍：客户端不跑形态引擎。** pymorphy3 是 Python 的，进不了浏览器；
但我们根本不需要运行时引擎——构建期把词形全部展开成查找表，客户端只查表。
确定性、毫秒级、零依赖。

## 6. 校验规则清单

已在代码中强制执行：

**逐条**
- `lemma` 不带重音，`stress` 带重音且去重音后与 `lemma` 一致
- 多音节词必须有重音（单音节、含 ё、跟在带重音前置词之后除外）
- 一个词最多一个重音符号，且必须紧跟元音
- 名词必须有 `gender` 和 `animacy`；动词必须有 `aspect` 和 `transitivity`
- 实词类必须有 `zaliznyak` 或 `form_overrides`（否则无法变格）
- `zaliznyak` 符合索引格式；`form_overrides` 的标签在标签集内、词形带重音
- 例句和搭配必须带重音；`level`、`labels` 在白名单内
- 至少一个义项，且中文释义非空
- 引用字段（`aspect_pair` / `motion_partner` / `plural_lemma`）是无重音词元
- 拒绝未知字段（`extra="forbid"`），防止手写 `forms` 绕过生成

**跨条**
- 同形词键唯一（靠 `homonym_id` 区分）
- 体对必须互指且体值相反
- 运动动词 uni/multi 必须配对互指
- `verify` 只能引用真实存在的字段名

## 7. 数据来源与许可

| 来源 | 提供 | 许可 |
|---|---|---|
| OpenRussian | 词形、全词形重音、变格表、真人音频 | CC BY-SA 4.0 |
| OpenCorpora / pymorphy3 | 形态分析与词形生成（源自扎利兹尼亚克语法词典） | CC BY-SA / MIT |
| 本项目手写 | **中文释义、义项划分、例句、搭配、教学注释** | 待定 |

**注意**：CC BY-SA 有传染性，衍生数据库再分发时须采用兼容许可。
若将来要闭源商用，必须在 M1 之前把开源数据的使用边界划清楚——
可行的做法是把开源形态数据与自撰释义在存储上分离，各自适用不同许可。
