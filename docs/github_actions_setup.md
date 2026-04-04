# GitHub Actions 자동 크롤러 설정 가이드

---

## 1. GitHub Secrets 설정

GitHub Actions에서 API 키를 안전하게 사용하기 위해 Secrets를 설정해야 합니다.

### 설정 방법

1. GitHub 레포지토리 페이지 접속
2. **Settings** 탭 클릭
3. 왼쪽 메뉴에서 **Secrets and variables** → **Actions** 클릭
4. **New repository secret** 버튼 클릭
5. 아래 3개를 각각 추가:

| Name | Value | 설명 |
|------|-------|------|
| `SUPABASE_URL` | `https://xxxx.supabase.co` | Supabase 프로젝트 URL |
| `SUPABASE_KEY` | `eyJhbG...` | Supabase anon key |
| `OPENAI_API_KEY` | `sk-...` | OpenAI API 키 |

### Supabase 키 확인 방법
- Supabase 대시보드 → Settings → API
- `Project URL` → SUPABASE_URL
- `anon public` 키 → SUPABASE_KEY

### OpenAI 키 확인 방법
- https://platform.openai.com/api-keys
- 새 키 생성 또는 기존 키 복사

---

## 2. 자동 실행 스케줄

워크플로우는 매일 **오전 9시(KST)** 에 자동 실행됩니다.

```
cron: '0 0 * * *'  ← UTC 00:00 = KST 09:00
```

실행 순서:
1. `v1/crawler.py` - RSS 뉴스 수집 + Supabase 저장
2. `v2/analyzer.py` - AI 요약 + 감성 분석
3. `v3/trend.py` - 키워드 추출
4. `v3/bias.py` - 편향 분석

---

## 3. 수동으로 워크플로우 실행하기

테스트하거나 즉시 실행하고 싶을 때:

1. GitHub 레포지토리 → **Actions** 탭
2. 왼쪽에서 **Daily News Crawler & AI Analysis** 클릭
3. 오른쪽 **Run workflow** 버튼 클릭
4. **Run workflow** 확인

---

## 4. 실행 로그 확인하기

1. GitHub 레포지토리 → **Actions** 탭
2. 최근 워크플로우 실행 클릭
3. **crawl-and-analyze** job 클릭
4. 각 step을 펼쳐서 로그 확인

### 로그에서 확인할 것:
- `Run RSS Crawler`: 몇 개의 뉴스가 수집되었는지
- `Run AI Analyzer`: 몇 개가 분석 성공/실패했는지
- `Run Keyword Extraction`: 키워드가 정상 추출되었는지
- `Run Bias Analysis`: 편향 점수가 산출되었는지

---

## 5. 실패 시 확인 체크리스트

### Secrets 문제
- [ ] SUPABASE_URL이 `https://`로 시작하는지
- [ ] SUPABASE_KEY가 올바른 anon key인지 (service_role key가 아닌지)
- [ ] OPENAI_API_KEY가 유효한지 (만료/잔액 확인)
- [ ] Secret 이름에 오타가 없는지

### Supabase 문제
- [ ] news_list 테이블이 존재하는지
- [ ] summary, sentiment, confidence, source 컬럼이 추가되었는지
- [ ] news_keywords, bias_reports 테이블이 생성되었는지
- [ ] Supabase 프로젝트가 일시정지(pause) 상태가 아닌지

### OpenAI 문제
- [ ] API 크레딧 잔액이 있는지
- [ ] Rate limit에 걸리지 않았는지

### 네트워크 문제
- [ ] RSS 피드 URL이 접근 가능한지
- [ ] GitHub Actions에서 외부 API 호출이 차단되지 않았는지

---

## 6. 비용 안내

### GitHub Actions
- **Public 레포**: 무료 (무제한)
- **Private 레포**: 월 2,000분 무료 (이 워크플로우는 약 2~3분/회 소요)
- 매일 실행 시 월 약 60~90분 사용 → 무료 범위 내

### OpenAI API
- gpt-4o-mini: $0.15/1M input tokens, $0.60/1M output tokens
- 뉴스 20건 분석 시 약 $0.01 미만
- 매일 실행 시 월 약 $0.30 미만 예상

---

## 7. 커스터마이징

### 실행 시간 변경
`.github/workflows/daily-crawler.yml`에서 cron 수정:

```yaml
# 매일 오전 9시 KST
- cron: '0 0 * * *'

# 매일 오후 6시 KST
- cron: '0 9 * * *'

# 매주 월요일 오전 9시 KST
- cron: '0 0 * * 1'

# 매 6시간마다
- cron: '0 */6 * * *'
```

### 특정 단계만 실행
각 step에 `if` 조건을 추가하여 선택적 실행 가능.
