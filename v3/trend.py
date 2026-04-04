import os
import json
import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from datetime import datetime
from collections import Counter

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

# ── OpenAI 키워드 추출 ─────────────────────────────────────

def extract_keywords_batch(titles):
    """여러 뉴스 제목에서 키워드를 일괄 추출 (API 호출 최소화)"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    numbered_titles = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))

    payload = {
        "model": "gpt-4o-mini",
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "너는 IT 뉴스 키워드 추출 전문가야.\n"
                    "주어진 뉴스 제목 목록에서 핵심 키워드/엔티티를 추출해.\n\n"
                    "규칙:\n"
                    "- 각 제목에서 1~3개의 핵심 키워드를 추출\n"
                    "- 기업명, 제품명, 기술 용어를 우선 추출\n"
                    "- 복합 키워드는 하나로 묶어 (예: 'AI 반도체', '갤럭시 S25')\n"
                    "- 너무 일반적인 단어(발표, 공개, 출시 등)는 제외\n\n"
                    "JSON 형식으로 응답:\n"
                    '{"results": [{"id": 1, "keywords": ["키워드1", "키워드2"]}, ...]}'
                )
            },
            {
                "role": "user",
                "content": f"뉴스 제목 목록:\n{numbered_titles}"
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1000
    }

    res = requests.post(url, headers=headers, json=payload, timeout=60)
    if res.status_code != 200:
        raise Exception(f"OpenAI API 오류: {res.status_code}")

    content = res.json()["choices"][0]["message"]["content"]
    return json.loads(content)

# ── 키워드 저장 ────────────────────────────────────────────

def save_keywords(news_id, keywords):
    """키워드를 news_keywords 테이블에 저장"""
    for kw in keywords:
        supabase_request("POST", "news_keywords", data={
            "news_id": news_id,
            "keyword": kw.strip()
        })

# ── 키워드 추출 실행 ───────────────────────────────────────

def run_keyword_extraction():
    console.print(Panel.fit(
        Text("🔑 키워드 추출기 (v3)", style="bold white on green", justify="center"),
        border_style="bright_green"
    ))
    console.print(f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n")

    if not OPENAI_API_KEY:
        console.print("[red]OPENAI_API_KEY가 설정되지 않았습니다.[/red]")
        return

    # 키워드 미추출 뉴스 조회 (news_keywords에 없는 뉴스)
    console.print("[cyan]📋 키워드 미추출 뉴스 조회 중...[/cyan]")

    # 전체 뉴스 가져오기
    res = supabase_request("GET", "news_list", params={
        "select": "id,title",
        "order": "created_at.desc",
        "limit": "50"
    })
    if res.status_code != 200:
        console.print(f"[red]뉴스 조회 실패: {res.text}[/red]")
        return

    all_news = res.json()

    # 이미 키워드가 추출된 뉴스 ID 조회
    kw_res = supabase_request("GET", "news_keywords", params={
        "select": "news_id"
    })
    existing_ids = set()
    if kw_res.status_code == 200:
        existing_ids = {item["news_id"] for item in kw_res.json()}

    # 미추출 뉴스 필터링
    unprocessed = [n for n in all_news if n["id"] not in existing_ids]

    if not unprocessed:
        console.print("[yellow]키워드 추출할 새 뉴스가 없습니다.[/yellow]")
        show_keyword_stats()
        return

    console.print(f"[green]✅ {len(unprocessed)}개 미추출 뉴스 발견[/green]\n")

    # 배치 처리 (10건씩)
    batch_size = 10
    total_extracted = 0

    for start in range(0, len(unprocessed), batch_size):
        batch = unprocessed[start:start + batch_size]
        titles = [n["title"] for n in batch]

        console.print(f"[cyan]  배치 {start//batch_size + 1}: {len(batch)}건 처리 중...[/cyan]")

        try:
            result = extract_keywords_batch(titles)
            results = result.get("results", [])

            for item in results:
                idx = item.get("id", 0) - 1
                keywords = item.get("keywords", [])

                if 0 <= idx < len(batch):
                    news = batch[idx]
                    save_keywords(news["id"], keywords)
                    total_extracted += 1
                    kw_str = ", ".join(keywords)
                    short_title = news["title"][:30] + "..." if len(news["title"]) > 30 else news["title"]
                    console.print(f"         🔑 {short_title} → [{kw_str}]")

        except Exception as e:
            console.print(f"  [red]배치 처리 실패: {e}[/red]")

    console.print(f"\n[bold]키워드 추출 완료: ✅ {total_extracted}건[/bold]\n")
    show_keyword_stats()

# ── 키워드 통계 ────────────────────────────────────────────

def show_keyword_stats():
    """키워드 빈도 통계 출력"""
    res = supabase_request("GET", "news_keywords", params={
        "select": "keyword"
    })
    if res.status_code != 200:
        console.print("[red]키워드 조회 실패[/red]")
        return

    keywords = [item["keyword"] for item in res.json()]
    if not keywords:
        console.print("[yellow]추출된 키워드가 없습니다.[/yellow]")
        return

    counter = Counter(keywords)
    top_keywords = counter.most_common(15)

    console.print(Panel.fit(
        Text("📊 키워드 빈도 TOP 15", style="bold white on purple", justify="center"),
        border_style="bright_magenta"
    ))

    table = Table(show_header=True, header_style="bold cyan", border_style="bright_black")
    table.add_column("순위", width=4, justify="right", style="dim")
    table.add_column("키워드", min_width=20)
    table.add_column("빈도", width=6, justify="right")
    table.add_column("비율", width=8, justify="right")
    table.add_column("그래프", min_width=20)

    max_count = top_keywords[0][1] if top_keywords else 1
    total = len(keywords)

    for rank, (kw, count) in enumerate(top_keywords, 1):
        pct = count / total * 100
        bar_len = int(count / max_count * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        table.add_row(str(rank), kw, str(count), f"{pct:.1f}%", f"[cyan]{bar}[/cyan]")

    console.print(table)
    console.print(f"\n[dim]총 {len(counter)}개 고유 키워드, {total}건 추출[/dim]")


if __name__ == "__main__":
    run_keyword_extraction()
