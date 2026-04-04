# IT News AI Pipeline

> RSS 수집부터 AI 분석, 편향 탐지, 트렌드 시각화까지 -- End-to-End 뉴스 데이터 파이프라인

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-green)
![OpenAI](https://img.shields.io/badge/OpenAI-gpt--4o--mini-orange)
![Chart.js](https://img.shields.io/badge/Chart.js-Visualization-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 프로젝트 개요

국내 주요 IT 매체(ZDNet, Bloter, ETNews)의 뉴스를 **자동 수집**하고, **LLM 기반 요약/감성 분석/편향 탐지**를 수행한 뒤, **트렌드를 시각화**하는 End-to-End 뉴스 데이터 파이프라인입니다.

### 핵심 가치
- 단순 크롤링이 아닌, AI를 활용한 **뉴스 콘텐츠 가공 및 인사이트 도출**
- 동일 이슈에 대한 매체별 보도 차이를 정량적으로 분석하는 **미디어 편향 탐지**
- v1 → v2 → v3 **단계적 확장**으로 데이터 파이프라인 설계 역량 입증

> 설계 근거, 기술 선택 이유, 편향 분석 방법론, 면접 대비 Q&A는 **[DOCUMENTATION.md](./DOCUMENTATION.md)** 참고

---

## 버전별 로드맵

| 버전 | 핵심 기능 | 브랜치 | 상태 |
|------|-----------|--------|------|
| **v1** | RSS 수집 + Supabase 저장 + 웹 대시보드 | `main` | Done |
| **v2** | LLM 요약 + 감성 분석 + 신뢰도 점수 | `feature/v2` | Planned |
| **v3** | 키워드 트렌드 + 매체별 편향 분석 + 시각화 | `feature/v3` | Planned |

---

## 프로젝트 구조

```
it-news-pipeline/
├── v1/                     # RSS 수집 + Supabase 저장 + 웹 대시보드
│   ├── crawler.py          # RSS 수집 엔진 + 터미널 대시보드
│   └── index.html          # 웹 대시보드 (Supabase JS SDK)
├── v2/                     # AI 요약 + 감성 분석 (feature/v2)
├── v3/                     # 키워드 트렌드 + 편향 분석 (feature/v3)
├── docs/                   # 프로젝트 문서
├── DOCUMENTATION.md        # 상세 기술 문서 + 면접 Q&A
└── README.md
```

---

## v1 -- RSS 수집 + Supabase 저장 + 웹 대시보드

### 기능
- 네이버 IT/과학 뉴스 RSS 자동 수집 (ZDNet, Bloter, ETNews 등 다중 소스)
- Supabase PostgreSQL `news_list` 테이블에 수집 데이터 저장
- Python 터미널 대시보드 (rich 라이브러리)
- 웹 대시보드 (index.html) -- 수집 / 새로고침 / 삭제 기능
- `.env` 환경변수로 API 키 보안 관리

### 기술 스택
| 구분 | 기술 | 선택 이유 |
|------|------|-----------|
| 언어 | Python 3.10+ | 데이터 처리 생태계, RSS 파싱 라이브러리 풍부 |
| RSS 파싱 | xml.etree.ElementTree + requests | 표준 라이브러리 활용, 외부 의존성 최소화 |
| 데이터베이스 | Supabase (PostgreSQL) | 무료 tier, REST API 기본 제공, 실시간 구독 가능 |
| DB 연동 | Supabase REST API (requests) | SDK 없이 HTTP 수준에서 동작 원리 학습 |
| 터미널 UI | rich | Python 터미널 시각화 표준 |
| 웹 UI | HTML + Vanilla JS + Supabase JS SDK | 프레임워크 없이 순수 웹 기술로 동작 원리 이해 |
| 환경변수 | python-dotenv | API 키 하드코딩 방지, 보안 관리 |

### Supabase 테이블 스키마
```sql
CREATE TABLE news_list (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  title      text NOT NULL,
  url        text NOT NULL,
  created_at timestamptz DEFAULT now()
);
```

### 아키텍처
```
RSS 피드 (ZDNet / Bloter / ETNews)
        |  HTTP GET
        v
crawler.py (Python)
  ├── XML 파싱 (ElementTree)
  ├── 제목 + URL 추출
  └── 중복/무효 데이터 필터링
        |  REST API (POST)
        v
Supabase PostgreSQL
  └── news_list 테이블
        |  REST API (GET) / JS SDK
        v
클라이언트
  ├── 터미널 대시보드 (rich)
  └── 웹 대시보드 (index.html)
      └── CORS 프록시 경유 RSS 직접 수집
```

### 실행 방법
```bash
pip install requests python-dotenv rich
cp .env.example .env
# .env에 SUPABASE_URL, SUPABASE_KEY 입력
cd v1 && python crawler.py
```

---

## v2 -- AI 요약 + 감성 분석 (branch: feature/v2)

### 추가 기능
- 수집된 뉴스 본문을 LLM(OpenAI gpt-4o-mini)으로 **한 줄 요약** 생성
- 뉴스 톤 분류 -- **긍정 / 부정 / 중립** 감성 분석 (Structured Output)
- 감성 분석 결과에 **confidence score** (0.0~1.0) 추가
- Supabase 테이블에 summary, sentiment, confidence 컬럼 확장
- 웹 대시보드에 AI 요약문 + 감성 뱃지 + 신뢰도 표시
- **배치 처리**: 미분석 뉴스만 선별하여 API 호출 최적화
- **프롬프트 엔지니어링**: 일관된 분석 결과를 위한 시스템 프롬프트 설계

### 추가 기술 스택
| 구분 | 기술 | 선택 이유 |
|------|------|-----------|
| AI 모델 | OpenAI gpt-4o-mini | 비용 효율적, 한국어 성능 우수, JSON 모드 지원 |
| API 연동 | openai Python SDK | 공식 SDK, 타입 힌트/재시도/스트리밍 지원 |
| 출력 형식 | Structured Output (JSON mode) | 파싱 안정성 보장, 스키마 강제 |

### 변경될 테이블 스키마
```sql
ALTER TABLE news_list
  ADD COLUMN summary    text,
  ADD COLUMN sentiment  text,      -- 'positive' | 'negative' | 'neutral'
  ADD COLUMN confidence float;     -- 0.0 ~ 1.0
```

### 아키텍처
```
v1 RSS 수집 파이프라인
        |
        v
AI 분석 모듈 (analyzer.py)
  ├── 미분석 뉴스 조회 (WHERE summary IS NULL)
  ├── OpenAI gpt-4o-mini 호출
  │   └── Structured Output (JSON)
  ├── 요약 + 감성 + 신뢰도 추출
  └── Supabase UPDATE
        |
        v
웹 대시보드 (v2 확장)
  ├── AI 요약문 표시
  ├── 감성 뱃지 (색상 코딩)
  └── 신뢰도 인디케이터
```

---

## v3 -- 트렌드 분석 + 편향 탐지 대시보드 (branch: feature/v3)

### 추가 기능

**키워드 트렌드 분석**
- 수집 뉴스에서 **키워드 자동 추출** (LLM 기반 엔티티 추출)
- 키워드별 등장 빈도 트렌드 차트 시각화
- 날짜별 뉴스 누적량 라인 차트

**매체별 편향 분석**
- 동일 이슈/키워드에 대한 **매체별 프레이밍 차이** 비교
- 매체별 감성 분포 비교 차트 (긍정/부정/중립 비율)
- **편향 점수(Bias Score)** 산출: 특정 주제에 대한 매체의 감성 편중도 정량화
- 편향 분석 리포트 자동 생성

**시각화 대시보드**
- 키워드 빈도 바 차트 / 워드클라우드
- 날짜별 뉴스량 라인 차트
- 매체별 감성 분포 파이/도넛 차트
- 편향 비교 레이더 차트

### 추가 기술 스택
| 구분 | 기술 | 선택 이유 |
|------|------|-----------|
| 시각화 | Chart.js | 경량 (< 200KB), Canvas 기반, 반응형, 풍부한 차트 타입 |
| 키워드 추출 | OpenAI API (엔티티 추출) | 한국어 형태소 분석 대비 문맥 이해력 우수 |
| 편향 분석 | 통계 집계 + LLM 프레이밍 분석 | LLM 감성 결과를 매체별로 집계하여 편향 점수 산출 |
| 데이터 집계 | Supabase PostgreSQL + JS | GROUP BY 집계 쿼리, 실시간 필터링 |

### 편향 분석 방법론
```
1. 동일 키워드/이슈 뉴스 그룹핑
   -- 같은 날짜, 같은 키워드를 다룬 뉴스끼리 묶음

2. 매체별 감성 분포 집계
   ├── 매체 A: positive 70% / neutral 20% / negative 10%
   └── 매체 B: positive 20% / neutral 30% / negative 50%

3. 편향 점수(Bias Score) 산출
   ├── 전체 평균 감성 대비 해당 매체의 감성 편차
   └── |매체 감성 비율 - 전체 평균 감성 비율| 의 합

4. 프레이밍 분석 (LLM)
   ├── 동일 이슈에 대한 헤드라인 표현 차이 비교
   └── 어떤 관점을 강조하는지 분류
```

### 변경될 테이블 스키마
```sql
-- 키워드 테이블
CREATE TABLE news_keywords (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  news_id    bigint REFERENCES news_list(id),
  keyword    text NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- 매체 정보 컬럼 추가
ALTER TABLE news_list ADD COLUMN source text;

-- 편향 분석 결과 테이블
CREATE TABLE bias_reports (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  keyword      text NOT NULL,
  date         date NOT NULL,
  source       text NOT NULL,
  positive_pct float,
  neutral_pct  float,
  negative_pct float,
  bias_score   float,
  created_at   timestamptz DEFAULT now()
);
```

---

## 전체 파이프라인 아키텍처 (v1 + v2 + v3)

```
             RSS 피드 소스
            ZDNet / Bloter / ETNews
                   |
            v1: 수집 계층
             crawler.py
             XML 파싱 + 저장
                   |
            v2: 분석 계층
             analyzer.py
             LLM 요약 / 감성 분석
                   |
        +----------+----------+
        |          |          |
   v3: 트렌드  v3: 편향   v3: 시각화
    trend.py   bias.py   dashboard
   키워드 추출 매체 비교  Chart.js
        |          |          |
        +----------+----------+
                   |
            Supabase DB
             PostgreSQL
             news_list
            news_keywords
            bias_reports
```

---

## 환경변수 설정

`.env.example` 참고:
```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your_supabase_anon_key
OPENAI_API_KEY=your_openai_api_key   # v2부터 필요
```

> `.env` 파일은 `.gitignore`에 등록되어 GitHub에 노출되지 않습니다.

---

## 파일 구조

| 파일 | 설명 |
|------|------|
| `v1/crawler.py` | RSS 수집 + Supabase 저장 + 터미널 대시보드 |
| `v1/index.html` | 웹 대시보드 (브라우저에서 바로 실행) |
| `DOCUMENTATION.md` | 프로젝트 상세 기술 문서 (설계, 면접 Q&A, 품질 전략) |
| `.env.example` | 환경변수 템플릿 |
| `.gitignore` | .env 등 민감 파일 제외 설정 |

---

## 개발자

- GitHub: [@meene11](https://github.com/meene11)
