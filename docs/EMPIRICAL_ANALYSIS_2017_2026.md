# Empirical analysis (2017–2026), non-reconstructive

A 10-admission-year aggregate of the main CSAT (수능) Korean **독서/비문학** reading
section, used only to **anchor** the clean demand model and passage formulas.
The machine-readable artifact is [`../data/empirical_aggregate.json`](../data/empirical_aggregate.json);
provenance is [PROVENANCE](PROVENANCE.md).

## Non-reconstructive guarantee

The aggregate contains **only corpus-level statistics and metadata**. It carries:

- ❌ no passage text, ❌ no item numbers, ❌ no answer keys, ❌ no n-grams,
- ❌ no per-passage / per-item feature rows,
- ✅ counts, ranges, ratios, and coding-reliability figures only.

Source authority: KICE official attachments (`www.suneung.re.kr`); odd form (홀수형)
canonical for coding, even form used for numbering cross-check.

## What the window shows (anchors used by the model)

- **Scope**: 국어 main CSAT only; literature / speech-writing / language-media and
  June·September mock exams excluded. 45 items per paper.
- **Common-format era (2022–2026)**: 4 reading passage-sets per year, 17 reading
  items per year (stable).
- **Items per standalone reading set**: min 3, median 4, max 6 — this anchors the
  `recommended_item_count = 3 + demand_rank` rule in
  `references/06-grade-difficulty-map.md`.
- **Domain evidence**: humanities, social, and science_tech appear as standalone
  독서 passage-sets; **arts** is not observed as a standalone 독서 domain in this
  window (it remains a teacher-selectable field).
- **Composite (주제통합)** and **reading-theory (독서론)** are treated as era features.
- Passage Hangul-length band (observed min/median/max) bounds the passage-length
  envelope; the model never targets below the observed min nor above the max.

## How it feeds the model

The aggregate is an **anchor, not a rulebook**: category vocabularies were
corroborated or adjusted only where the corpus-level evidence justified it. The
generation vocabularies themselves are designed from the public principles in
[METHODOLOGY](METHODOLOGY.md).

## Limitation

Corpus structure informs authoring plausibility, not empirical student difficulty
or fairness of generated items ([NON_AFFILIATION](NON_AFFILIATION.md)).
