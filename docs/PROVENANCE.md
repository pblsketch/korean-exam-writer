# Provenance

Two provenance surfaces exist. Neither carries any exam full text.

## 1. Source-window provenance (metadata only)

The clean demand model and passage formulas were anchored to the **most recent
10 admission-year window** of the official main CSAT (수능) Korean-language
section (국어영역), candidate years **2017–2026학년도**. Only public board metadata
is recorded — never passage or item text, and never per-passage/per-item rows.

- Machine-readable: [`../data/source_provenance.json`](../data/source_provenance.json)
- Authority: Korea Institute for Curriculum and Evaluation (KICE)
- Public board: `www.suneung.re.kr` (board id `1500234`)
- Scope: main CSAT only; June/September mock exams excluded.

For each admission year the record stores the board record id, the official
question/answer **file names**, the official file identifiers, the publish date,
and the **SHA-256 fingerprints** of the official attachments (`attachment_sha256`,
metadata only). The attachments themselves remain private and outside this repo;
no attachment bytes and no extracted text are stored here. Hash + URL provide
integrity re-verification, not a guarantee of byte-identical re-download.

### What is NOT here

- No downloaded attachments (question ZIPs/PDFs, answer keys).
- No passage text, item numbers, answer keys, or n-grams.

## 2. Generation provenance (per packet)

Every generated exam records its source mode in `meta.sourceMode`
(`A_textbook` / `B_material` / `C_research`) and grounds each factual sentence
with a verbatim `sourceQuote` tied to an entry in `sources[]`
(`references/07-source-modes.md`). This keeps review and the post-hoc
validation gate auditable.

## Design note

All generation identifiers, the schema's controlled vocabularies, and the
methodology are designed from the public principles cited in
[METHODOLOGY](METHODOLOGY.md).
