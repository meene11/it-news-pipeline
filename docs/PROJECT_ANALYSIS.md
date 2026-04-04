# IT News AI Pipeline -- 기술 분석 및 품질 검증 가이드

---

## 1. 현재 AI 기술 적용 현황 (솔직한 분석)

### 현재 상태 (v1) -- AI 없음

**v1에는 AI 기술이 포함되어 있지 않습니다.** 현재 구현된 것:

| 구현됨 | 미구현 (계획) |
|--------|--------------|
| RSS XML 파싱 (표준 라이브러리) | LLM 요약 생성 |
| Supabase REST API 연동 | 감성 분석 |
| 터미널 대시보드 (rich) | 편향 탐지 |
| 웹 대시보드 (Vanilla JS) | 키워드 추출 |
| 다중 소스 Fallback | 트렌드 시각화 |

### v2에서 도입 예정인 AI 기술

#### 1) LLM 기반 뉴스 요약 (Text Summarization)

```
입력: "삼성전자, AI 반도체 HBM4 양산 본격화...SK하이닉스와 경쟁 심화"
      ↓ OpenAI gpt-4o-mini API 호출
출력: "삼성전자가 HBM4 양산을 시작하며 SK하이닉스와의 AI 반도체 경쟁이 격화됨"
```

- **기술**: OpenAI Chat Completions API
- **모델**: gpt-4o-mini
- **방식**: 뉴스 제목 → 시스템 프롬프트로 요약 지시 → 1문장 요약 생성
- **AI 분류**: 자연어 생성 (NLG, Natural Language Generation)
- **이것이 AI인 이유**: 단순 문자열 조작이 아니라, 모델이 문맥을 이해하고 새로운 문장을 생성함

#### 2) LLM 기반 감성 분석 (Sentiment Analysis)

```
입력: "카카오 대규모 감원 단행, 수익성 개선 기대"
      ↓ gpt-4o-mini + Structured Output (JSON mode)
출력: {
  "sentiment": "negative",
  "confidence": 0.72,
  "reasoning": "감원이라는 부정적 사건이 주 내용이나, 수익성 기대라는 긍정 요소도 있어 신뢰도가 낮음"
}
```

- **기술**: OpenAI Structured Output (JSON mode)
- **AI 분류**: 자연어 이해 (NLU, Natural Language Understanding) + 텍스트 분류 (Text Classification)
- **이것이 AI인 이유**: 규칙 기반이 아닌, 학습된 언어 모델이 문맥과 뉘앙스를 파악하여 분류함
- **핵심 기법**: 프롬프트 엔지니어링 -- 시스템 프롬프트에서 분류 기준과 출력 형식을 정의

#### 3) Confidence Score (신뢰도 점수)

- 모델이 자신의 분석 결과에 대해 얼마나 확신하는지를 0.0~1.0으로 수치화
- **활용**: 낮은 신뢰도(< 0.6) 결과를 별도 검토 대상으로 플래깅
- **한계**: LLM의 self-reported confidence는 실제 정확도와 항상 일치하지 않음 (이것은 면접에서 말할 수 있어야 하는 한계)

### v3에서 도입 예정인 AI 기술

#### 4) LLM 기반 키워드/엔티티 추출 (Named Entity Recognition)

```
입력: "네이버 클로바X, 기업용 AI 시장 공략 가속화"
      ↓ gpt-4o-mini
출력: ["네이버", "클로바X", "기업용 AI"]
```

- **AI 분류**: 정보 추출 (Information Extraction)
- **대안 기술과의 비교**:
  - konlpy (한국어 형태소 분석): "네이버"는 추출하지만 "클로바X"나 "기업용 AI"는 놓침
  - TF-IDF: 통계 기반이라 짧은 제목에서 정확도 낮음
  - LLM: 문맥을 이해하여 복합 엔티티를 하나의 단위로 추출

#### 5) LLM 기반 프레이밍 분석

```
입력:
  매체A: "삼성전자 AI 투자 확대, 글로벌 1위 도약"
  매체B: "삼성전자 무리한 AI 투자, 실적 악화 우려"
      ↓ gpt-4o-mini
출력: {
  "매체A_프레임": "성장/기회",
  "매체B_프레임": "리스크/우려",
  "분석": "동일한 투자 결정을 기회 vs 리스크로 반대 프레이밍"
}
```

### AI 기술 요약 정리

| # | AI 기술 | NLP 분류 | 구현 버전 | 현재 상태 |
|---|---------|----------|-----------|-----------|
| 1 | 뉴스 요약 | NLG (자연어 생성) | v2 | 미구현 |
| 2 | 감성 분석 | NLU + 텍스트 분류 | v2 | 미구현 |
| 3 | 신뢰도 산출 | 모델 보정 (Calibration) | v2 | 미구현 |
| 4 | 키워드 추출 | 정보 추출 (IE) | v3 | 미구현 |
| 5 | 프레이밍 분석 | 담화 분석 (Discourse Analysis) | v3 | 미구현 |

---

## 2. 편향 분석 기준과 신뢰도

### 2.1 편향 분석의 근거

#### 학술적 근거

| 이론/프레임워크 | 연구자 | 핵심 내용 | 이 프로젝트에 적용하는 방식 |
|----------------|--------|-----------|--------------------------|
| **프레이밍 이론** | Entman (1993) | 같은 사건도 어떤 측면을 선택·강조하느냐에 따라 수용자 해석이 달라짐 | 매체별 헤드라인의 프레이밍 차이를 LLM으로 비교 |
| **의제설정 이론** | McCombs & Shaw (1972) | 미디어가 무엇을 보도하느냐가 공중의 관심사를 결정 | 매체별 키워드 빈도(보도량) 차이 분석 |
| **게이트키핑 이론** | Shoemaker & Vos (2009) | 편집자가 뉴스를 선별하는 과정에서 편향 발생 | 매체별 뉴스 선택 패턴 비교 |

#### 실무적 참고 모델

| 모델 | 조직 | 방법론 | 이 프로젝트와의 차이 |
|------|------|--------|---------------------|
| **AllSides** | AllSides.com | 블라인드 설문 + 편집진 평가 + 독자 투표로 좌/중/우 5단계 분류 | 우리는 LLM 감성 분석 기반 자동 정량화 |
| **MBFC** | MediaBiasFactCheck.com | 전문가가 편향·사실성을 수동 평가 | 우리는 자동화된 통계적 접근 |
| **Ad Fontes** | Ad Fontes Media | 복수 평가자가 개별 기사를 평가하여 신뢰도·편향 매핑 | 우리는 제목 수준의 감성 분석 |

### 2.2 이 프로젝트의 편향 분석 방법 -- 신뢰도 평가

#### 이 방법이 신뢰할 수 있는 부분

| 강점 | 설명 |
|------|------|
| 정량적 | 감성 비율의 수치적 편차로 측정하므로 주관 개입 최소화 |
| 재현 가능 | 같은 데이터에 같은 모델을 적용하면 유사한 결과 |
| 자동화 가능 | 대량의 뉴스를 빠르게 처리 |
| 비교 가능 | 매체 간, 시점 간 편향도 비교 가능 |

#### 이 방법의 한계 (면접에서 반드시 언급해야 할 것)

| 한계 | 심각도 | 설명 |
|------|--------|------|
| **LLM 자체 편향** | 높음 | gpt-4o-mini의 학습 데이터에 영어·서양 관점 편향이 있을 수 있음 |
| **제목만 분석** | 높음 | 본문 없이 제목만으로 감성을 판단하므로 낚시성 제목에 취약 |
| **표본 크기** | 중간 | 3개 매체, 수집량이 적으면 통계적 유의성이 낮음 |
| **감성 ≠ 편향** | 중간 | 부정적 보도가 반드시 편향은 아님 (실제로 부정적인 사건일 수 있음) |
| **시간 스냅샷** | 낮음 | 특정 시점의 편향만 포착, 장기적 패턴은 별도 분석 필요 |

#### 결론: 신뢰할 수 있는 방법인가?

**"경향성 탐색 도구"로서는 유효하지만, "편향 판정 도구"로서는 불충분합니다.**

- 이 프로젝트의 편향 분석은 "이 매체가 편향되었다"고 단정하는 것이 아니라
- "이 이슈에 대해 매체 간 보도 톤 차이가 존재한다"는 것을 데이터로 보여주는 것
- 학술 논문 수준의 엄밀성을 갖추려면: 본문 분석, 대규모 표본, 복수 평가자 교차 검증이 필요

---

## 3. 품질 분석, 평가, 검증 방법

### 3.1 지금 당장 할 수 있는 테스트

#### 테스트 1: RSS 수집 정상 동작 확인

```bash
cd C:\Users\hye\Documents\it-news-pipeline\v1
python crawler.py
```

**검증 포인트:**
- [ ] RSS 소스 중 하나 이상에서 뉴스가 수집되는가?
- [ ] 수집된 뉴스 수가 0보다 큰가?
- [ ] 터미널 대시보드에 제목이 정상 출력되는가?
- [ ] Supabase에 데이터가 저장되는가?

#### 테스트 2: 웹 대시보드 정상 동작 확인

```bash
cd C:\Users\hye\Documents\it-news-pipeline\v1
python -m http.server 8000
# 브라우저에서 http://localhost:8000/index.html 접속
```

**검증 포인트:**
- [ ] Supabase 연결 상태가 "ONLINE"으로 표시되는가?
- [ ] 저장된 뉴스가 카드 형태로 표시되는가?
- [ ] "뉴스 수집 시작" 버튼이 동작하는가?
- [ ] "새로고침" 버튼이 동작하는가?
- [ ] "데이터 초기화" 버튼이 동작하는가?

#### 테스트 3: RSS Fallback 동작 확인

```bash
# crawler.py에서 첫 번째 RSS URL을 의도적으로 잘못된 URL로 변경
# → 두 번째 URL에서 수집이 되는지 확인
# → 테스트 후 원래 URL로 복원
```

**검증 포인트:**
- [ ] 첫 번째 소스 실패 시 다음 소스로 자동 전환되는가?
- [ ] 실패 로그가 정상 출력되는가?

#### 테스트 4: 데이터 품질 검증

```bash
# Supabase 대시보드에서 직접 SQL 실행
SELECT COUNT(*) FROM news_list;                          -- 전체 건수
SELECT COUNT(*) FROM news_list WHERE title IS NULL;      -- NULL 제목
SELECT COUNT(*) FROM news_list WHERE LENGTH(title) < 5;  -- 너무 짧은 제목
SELECT title, COUNT(*) FROM news_list GROUP BY title HAVING COUNT(*) > 1;  -- 중복
```

**검증 포인트:**
- [ ] NULL 데이터가 없는가?
- [ ] 5자 미만 제목이 없는가?
- [ ] 중복 데이터가 있는가? (현재 중복 방지 로직 없음 → v2 개선 대상)

### 3.2 v2 구현 후 해야 할 테스트

#### AI 분석 정확도 평가 (Human Evaluation)

```
1. 뉴스 50건을 무작위 샘플링
2. 각 뉴스에 대해:
   a) AI가 생성한 요약이 원문 내용과 일치하는가? (정확도)
   b) AI의 감성 분류가 본인의 판단과 일치하는가? (일치율)
   c) confidence score가 높은 건이 실제로 더 정확한가? (보정도)
3. 결과를 표로 정리

예시:
| # | 제목 | AI 감성 | 내 판단 | 일치? | confidence |
|---|------|---------|---------|-------|-----------|
| 1 | ... | positive | positive | O | 0.91 |
| 2 | ... | negative | neutral | X | 0.58 |
```

**목표 지표:**
- 감성 분석 일치율 > 80%
- 요약 정확도 > 85%
- 낮은 confidence(< 0.6)에서 오류율이 더 높아야 함 (보정이 잘 되었다는 의미)

### 3.3 v3 구현 후 해야 할 테스트

#### 편향 점수 검증

```
1. 동일 키워드에 대한 매체별 기사를 수동으로 읽어봄
2. 직접 느낀 편향 방향과 Bias Score가 일치하는지 확인
3. Bias Score가 0에 가까운 키워드는 실제로 매체 간 톤 차이가 적은지 확인
4. 카이제곱 검정으로 매체 간 감성 분포 차이의 통계적 유의성 확인
```

### 3.4 품질 지표(KPI) 대시보드

| 지표 | 측정 방법 | 현재 | v2 목표 | v3 목표 |
|------|-----------|------|---------|---------|
| 수집 성공률 | 성공 수집 / 시도 수 | 측정 안함 | > 95% | > 95% |
| 데이터 완전성 | NULL 없는 레코드 비율 | 측정 안함 | > 99% | > 99% |
| 중복률 | 중복 레코드 / 전체 | 미방지 | < 1% | < 1% |
| AI 감성 정확도 | Human eval 일치율 | N/A | > 80% | > 80% |
| 분석 커버리지 | 분석 완료 / 전체 뉴스 | N/A | > 95% | > 95% |
| 편향 점수 유효성 | 수동 검증 일치율 | N/A | N/A | > 70% |

---

## 4. 뉴스 수집 스케줄링 -- 현재 상태

### 현재: 스케줄러 없음

**현재 뉴스 수집은 수동으로 실행해야 합니다.** `python crawler.py`를 직접 실행하거나, 웹 대시보드에서 "뉴스 수집 시작" 버튼을 누를 때만 수집됩니다.

자동으로 일주일에 한 번 수집하는 기능은 구현되어 있지 않습니다.

### 자동화 방법 (구현 예정)

#### 방법 1: Windows 작업 스케줄러

```bash
# Windows에서 매주 월요일 09:00에 실행
schtasks /create /tn "NewsCrawler" /tr "python C:\Users\hye\Documents\it-news-pipeline\v1\crawler.py" /sc weekly /d MON /st 09:00
```

#### 방법 2: GitHub Actions (추천)

```yaml
# .github/workflows/crawl.yml
name: Weekly News Crawl
on:
  schedule:
    - cron: '0 0 * * 1'  # 매주 월요일 00:00 UTC
jobs:
  crawl:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - run: pip install requests python-dotenv rich
      - run: python v1/crawler.py
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
```

#### 방법 3: Python 자체 스케줄러

```python
import schedule
import time

schedule.every().monday.at("09:00").do(fetch_and_save)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 5. 브라우저에서 보는 방법

### 방법 1: 가장 간단한 방법 (Python HTTP 서버)

```bash
cd C:\Users\hye\Documents\it-news-pipeline\v1
python -m http.server 8000
```

그 다음 브라우저에서 열기:
```
http://localhost:8000/index.html
```

**서버 하나만 키면 됩니다.** `python -m http.server`는 Python 내장 HTTP 서버로, 별도 설치가 필요 없습니다.

끄려면 터미널에서 `Ctrl+C`를 누르면 됩니다.

### 방법 2: 파일 직접 열기

```bash
# 그냥 파일을 더블클릭하거나:
start C:\Users\hye\Documents\it-news-pipeline\v1\index.html
```

이 방법도 동작하지만, 일부 브라우저에서 `file://` 프로토콜로 열면 CORS 정책이 더 엄격해질 수 있으므로 방법 1을 추천합니다.

### 방법 3: VS Code Live Server

VS Code에서 Live Server 확장 설치 후, `index.html`에서 우클릭 → "Open with Live Server"

### 요약

```bash
# 이 두 줄이면 끝
cd C:\Users\hye\Documents\it-news-pipeline\v1
python -m http.server 8000
# → 브라우저에서 http://localhost:8000/index.html
```

---

*이 문서는 프로젝트의 현재 상태를 솔직하게 분석하고, 테스트/검증 방법을 정리한 것입니다.*
