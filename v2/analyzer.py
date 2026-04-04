import os
import json
import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

console = Console()

# ── Supabase 헬퍼 ──────────────────────────────────────────

def supabase_request(method, table, data=None, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    return requests.request(method, url, headers=headers, json=data, params=params)

# ── OpenAI API 호출 ────────────────────────────────────────

def analyze_with_openai(title):
    """뉴스 제목을 gpt-4o-mini로 요약 + 감성 분석"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "너는 IT 뉴스 분석 전문가야. "
                    "주어진 뉴스 제목을 분석해서 반드시 아래 JSON 형식으로만 응답해.\n\n"
                    "{\n"
                    '  "summary": "핵심 내용을 한 줄(20자 이내)로 요약",\n'
                    '  "sentiment": "positive 또는 negative 또는 neutral",\n'
                    '  "confidence": 0.0~1.0 사이의 확신도\n'
                    "}\n\n"
                    "감성 분류 기준:\n"
                    "- positive: 성장, 투자, 혁신, 성과, 기대 등 긍정적 전망\n"
                    "- negative: 하락, 감원, 위기, 규제, 손실 등 부정적 내용\n"
                    "- neutral: 단순 사실 전달, 양면적 내용, 판단 어려움\n\n"
                    "confidence 기준:\n"
                    "- 0.9 이상: 감성이 매우 명확한 경우\n"
                    "- 0.7~0.9: 감성이 비교적 명확한 경우\n"
                    "- 0.5~0.7: 양면적이거나 판단이 어려운 경우\n"
                    "- 0.5 미만: 감성 판단이 거의 불가능한 경우"
                )
            },
            {
                "role": "user",
                "content": f"뉴스 제목: {title}"
            }
        ],
        "temperature": 0.1,
        "max_tokens": 200
    }

    res = requests.post(url, headers=headers, json=payload, timeout=30)
    if res.status_code != 200:
        raise Exception(f"OpenAI API 오류: {res.status_code} - {res.text}")

    content = res.json()["choices"][0]["message"]["content"]
    return json.loads(content)

# ── 미분석 뉴스 조회 ───────────────────────────────────────

def get_unanalyzed_news(limit=10):
    """summary가 NULL인 뉴스만 조회"""
    res = supabase_request("GET", "news_list", params={
        "select": "*",
        "summary": "is.null",
        "order": "created_at.desc",
        "limit": str(limit)
    })
    if res.status_code != 200:
        console.print(f"[red]DB 조회 실패: {res.text}[/red]")
        return []
    return res.json()

# ── 분석 결과 업데이트 ─────────────────────────────────────

def update_news_analysis(news_id, summary, sentiment, confidence):
    """분석 결과를 Supabase에 업데이트"""
    res = supabase_request("PATCH", "news_list", data={
        "summary": summary,
        "sentiment": sentiment,
        "confidence": confidence
    }, params={"id": f"eq.{news_id}"})
    return res.status_code in (200, 204)

# ── 배치 분석 실행 ─────────────────────────────────────────

def run_analysis():
    console.print(Panel.fit(
        Text("🤖 AI 뉴스 분석기 (v2)", style="bold white on blue", justify="center"),
        border_style="bright_blue"
    ))
    console.print(f"[dim]실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n")

    # API 키 확인
    if not OPENAI_API_KEY:
        console.print("[red]OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.[/red]")
        return

    # 미분석 뉴스 조회
    console.print("[cyan]📋 미분석 뉴스 조회 중...[/cyan]")
    news_list = get_unanalyzed_news(limit=10)

    if not news_list:
        console.print("[yellow]분석할 새 뉴스가 없습니다.[/yellow]")
        show_dashboard()
        return

    console.print(f"[green]✅ {len(news_list)}개 미분석 뉴스 발견[/green]\n")

    # 배치 분석
    analyzed = 0
    failed = 0

    for i, news in enumerate(news_list, 1):
        title = news["title"]
        news_id = news["id"]
        short_title = title[:40] + "..." if len(title) > 40 else title

        console.print(f"[cyan]  [{i}/{len(news_list)}] 분석 중: {short_title}[/cyan]")

        try:
            result = analyze_with_openai(title)
            summary = result.get("summary", "")
            sentiment = result.get("sentiment", "neutral")
            confidence = float(result.get("confidence", 0.5))

            # 유효성 검증
            if sentiment not in ("positive", "negative", "neutral"):
                sentiment = "neutral"
            confidence = max(0.0, min(1.0, confidence))

            if update_news_analysis(news_id, summary, sentiment, confidence):
                sentiment_emoji = {"positive": "🟢", "negative": "🔴", "neutral": "🟡"}
                emoji = sentiment_emoji.get(sentiment, "⚪")
                console.print(f"         {emoji} {sentiment} (신뢰도: {confidence:.2f}) → {summary}")
                analyzed += 1
            else:
                console.print(f"         [red]DB 업데이트 실패[/red]")
                failed += 1

        except Exception as e:
            console.print(f"         [red]분석 실패: {e}[/red]")
            failed += 1

    console.print(f"\n[bold]분석 완료: ✅ {analyzed}건 성공 / ❌ {failed}건 실패[/bold]\n")
    show_dashboard()

# ── 분석 결과 대시보드 ─────────────────────────────────────

def show_dashboard():
    res = supabase_request("GET", "news_list", params={
        "select": "*",
        "order": "created_at.desc",
        "limit": "20"
    })

    if res.status_code != 200:
        console.print(f"[red]DB 조회 실패: {res.text}[/red]")
        return

    data = res.json()

    console.print(Panel.fit(
        Text("📊 AI 분석 결과 대시보드", style="bold white on purple", justify="center"),
        border_style="bright_magenta"
    ))

    if not data:
        console.print("[yellow]저장된 뉴스가 없습니다.[/yellow]")
        return

    table = Table(
        show_header=True,
        header_style="bold magenta",
        border_style="bright_black",
        show_lines=True
    )
    table.add_column("No.", style="dim", width=4, justify="right")
    table.add_column("제목", min_width=30, max_width=40)
    table.add_column("AI 요약", min_width=20, max_width=30, style="cyan")
    table.add_column("감성", width=10, justify="center")
    table.add_column("신뢰도", width=8, justify="center")

    sentiment_style = {
        "positive": "[green]🟢 긍정[/green]",
        "negative": "[red]🔴 부정[/red]",
        "neutral": "[yellow]🟡 중립[/yellow]"
    }

    for i, row in enumerate(data, 1):
        title = row["title"][:38] + "..." if len(row["title"]) > 38 else row["title"]
        summary = row.get("summary") or "[dim]미분석[/dim]"
        if row.get("summary") and len(row["summary"]) > 28:
            summary = row["summary"][:28] + "..."
        sentiment = sentiment_style.get(row.get("sentiment"), "[dim]—[/dim]")
        confidence = f"{row['confidence']:.2f}" if row.get("confidence") is not None else "—"

        table.add_row(str(i), title, summary, sentiment, confidence)

    console.print(table)

    # 통계
    total = len(data)
    analyzed_count = sum(1 for d in data if d.get("summary"))
    sentiments = [d.get("sentiment") for d in data if d.get("sentiment")]
    pos = sentiments.count("positive")
    neg = sentiments.count("negative")
    neu = sentiments.count("neutral")

    console.print(f"\n[bold]총 {total}건 | 분석 완료 {analyzed_count}건[/bold]")
    if sentiments:
        console.print(f"[green]긍정 {pos}[/green] / [yellow]중립 {neu}[/yellow] / [red]부정 {neg}[/red]")

if __name__ == "__main__":
    run_analysis()
