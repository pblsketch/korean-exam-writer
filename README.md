# korean-bimunhak-exam — 국어 비문학(독서) 시험지 생성 Claude Agent Skill

중·고등학교 국어 교사가 **자신이 구독한 Claude/GPT**로 수능 국어 **비문학(독서)** 지문·문항·해설을 만드는 Agent Skill.
인문·사회·과학·기술·예술 등 독서 영역이 대상이다. 서버·DB·API키 없이 교사의 모델로 실행한다.

> 국어 영역 스킬 패밀리: **비문학(이 스킬)** · 운문(향후 `korean-unmun-exam`) · 산문(향후 `korean-sanmun-exam`).

## 핵심 원칙 (P0) — 환각·오류 금지
모든 사실은 근거(교사 자료·교과서·리서치 스니펫)의 **축자(글자 그대로) 인용**을 달고,
`scripts/validate_exam.py`가 그것이 원자료의 **실제 부분문자열**인지 기계로 검증한다.
근거를 못 대는 사실은 삭제, 지문이 성립 안 되면 거부. 완성본에는 교사용 검증 리포트 + "최종 검토 필요" 고지 첨부.

## 구조 다이어그램 (비개발자용)
순차(↓ 화살표)와 병렬(⇉ 갈라졌다 모이는 분기·합류)을 그대로 그렸다. 인터랙티브 원본·상세 설명은
[`docs/architecture.html`](docs/architecture.html).

### ① 스킬을 만드는 공장 — 하네스
설계자 다음 **집필가∥기술자가 동시(병렬)로 갈라졌다** 다시 모여 검사로 이어진다.

![하네스 다이어그램](docs/images/harness.png)

### ② 스킬 안에서 일하는 AI 팀 — 멀티에이전트
지문이 확정되면 **문항들이 한 점에서 갈라져 동시 출제(팬아웃)** 되고, **한데 모여(팬인)** 검토관이 일괄 검증한다.

![멀티에이전트 다이어그램](docs/images/multiagent.png)

### ③ 선생님이 실제로 쓰는 흐름 — 대화형
체크포인트마다 멈추고(⏸) 선생님 승인을 받아 진행한다(딸깍 X).

![사용자 워크플로우 다이어그램](docs/images/workflow.png)

## 동작 방식
- **오케스트레이션(분업 · 하이브리드)**: 오케스트레이터가 지휘하고 서브에이전트(자료조사·설계·집필·사실검증·출제·검토·조립)가
  역할을 나눠 수행한다. **순차가 필요한 곳은 파이프라인, 독립인 곳은 병렬(팬아웃/팬인)** — 특히 문항은 동시 출제 후 모아서 검토·게이트.
  생성자와 검증자를 분리한다. (`references/12-orchestration.md`)
- **휴먼인더루프(대화형)**: 맥락 수집 → 글감 → 출처 확인 → 개요 → 지문 → 문항을 체크포인트마다 교사에게
  묻고 승인받으며 진행(딸깍 X). (`references/13-interactive-workflow.md`, `09-classroom-context.md`)

## 기능
- **지문 소스 3종**: 교과서 재구성 / 교사 자료 재구성 / AI 리서치 재구성
- **학년(중1~고3) × 세부 난이도(하/중/상/최상)** — 구성타당도 난이도 모델(어휘·길이가 아닌 인지요구·근거분산)
- **문항 출제**: 유형 7종 × 인지요구(demand) 4단 2축, 오답 8종 3범주(오개념 태그), 근거역할 8종, 안티-복제
- **전개·발문 다양화**: 14종 전개 방식 팔레트 + 발문 형태 다양화 (나열/분류 편중 방지)
- **출력**: 인쇄용 2단 A4 HTML(→PDF) 기본 + 한글(HWPX)
  - 지문 박스 = 흐르는 문단 4면 연결 테두리(단·페이지 넘어도 이어짐), `<보기>` = 표 박스

## 구성
```
SKILL.md                  오케스트레이터(8단계 + 2개 검증 게이트)
references/                규칙 문서(환각방지·유형·인지계약·오답·근거역할·전개방식·다양화 등)
scripts/                  exam.schema.json · validate_exam.py · render_html.py · exam_to_hwpx.py · security_scan.py
assets/templates/         exam.css (2단 A4 인쇄 CSS)
examples/                 고정 샘플 + 골든 스냅샷(LLM 없이 결정론적 테스트)
data/                     비재구성 실증 집계(2017~2026 수능 독서 통계 — 원문·정답·n-gram 없음)
docs/                     방법론·출처·비제휴·실증분석 정책 문서
gpt/                      ChatGPT 맞춤형 GPT용 지시문(코드 없는 라이트 계층)
.github/workflows/        CI(검증·렌더·보안스캔·린트)
```

## 설계 근거
문항 생성 방법론(유형·인지계약·오답·근거역할·지문공식·난이도·출처모드)은 공개 측정학·텍스트언어학
문헌(Haladyna·AERA/APA/NCME·Meyer 등)에 근거해 설계했다. 상세는
[`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) · [`docs/NON_AFFILIATION.md`](docs/NON_AFFILIATION.md).

## 설치·사용
- **Claude Code**: 이 폴더를 스킬 디렉터리에 두면 "국어 문제 출제해줘"로 발동.
- **HWPX 출력**: `python -m pip install -U python-hwpx lxml` ([hwpx-plugins](https://github.com/airmang/hwpx-plugins) 스택)
- **ChatGPT**: `gpt/GPT_INSTRUCTIONS.md`를 맞춤형 GPT Instructions에 붙여넣기.

## 테스트 (LLM 없이)
```bash
python scripts/validate_exam.py examples/sample_exam.json      # 게이트 통과(exit 0)
python scripts/validate_exam.py examples/sample_exam_bad.json  # 게이트 거부(exit 1)
python scripts/render_html.py examples/sample_exam.json -o out.html   # 골든 스냅샷과 동일
python scripts/exam_to_hwpx.py examples/sample_exam.json -o out.hwpx  # HWPX 조판
```

> ⚠️ 생성 도구입니다. 실제 출제 전 반드시 교사의 최종 검토가 필요합니다.

## 라이선스
**PolyForm Noncommercial License 1.0.0** — **비상업(NonCommercial) 목적만 허용, 상업적 이용 금지.**
교사·학교·교육기관·연구·개인 학습 용도의 사용·수정·공유는 자유입니다(라이선스 전문의 "Noncommercial
Purposes"에 교육기관·개인 학습이 명시). 상업적 판매·유료 서비스·상업 제품 편입은 별도 허락이 필요합니다.
자세한 조건은 [`LICENSE`](LICENSE) 참고.

## 출처·고지 (NOTICE)
- HWPX 출력은 [`python-hwpx` / hwpx-plugins](https://github.com/airmang/hwpx-plugins)(Apache-2.0)에 의존한다(코드 미포함, pip 설치).
- 본 도구의 **생성물(지문·문항)은 오류 가능성이 있으므로, 사용자는 실제 사용 전 반드시 사실·품질을 검토**해야 한다. 생성물의 정확성에 대해 저자는 보증하지 않는다.
