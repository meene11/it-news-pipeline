import os
import re
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

console = Console()

def supabase_request(method, table, data=None, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    return requests.request(method, url, headers=headers, json=data, params=params)

def fetch_it_news_rss():
    """네이버 IT/과학 뉴스 RSS로 무료 수집"""
    console.print("[cyan]🔍 네이버 RSS로 IT 뉴스 수집 중...[/cyan]")

    rss_url = "https://feeds.feedburner.com/navernews/it"
    fallback_urls = [
        "https://news.naver.com/main/rss/it.nhn",
        "https://rss.etnews.com/Section901.xml",
        "https://rss.zdnet.co.kr/zdnet/rss/news.xml",
        "https://feeds.feedburner.com/bloter",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    news_items = []

    for url in [rss_url] + fallback_urls:
        try:
            console.print(f"[dim]시도 중: {url}[/dim]")
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                continue

            root = ET.fromstring(res.content)

            # RSS 파싱
            for item in root.iter("item"):
                title_el = item.find("title")
                link_el = item.find("link")

                if title_el is not None and link_el is not None:
                    title = title_el.text or ""
                    link = link_el.text or ""

                    # 빈 값 또는 너무 짧은 제목 제외
                    if title and link and len(title) > 5:
                        news_items.append({
                            "title": title.strip(),
                            "url": link.strip()
                        })

                if len(news_items) >= 20:
                    break

            if news_items:
                console.print(f"[green]✅ {len(news_items)}개 뉴스 수집 완료! (출처: {url})[/green]")
                break

        except Exception as e:
            console.print(f"[yellow]⚠️ 실패: {url} → {e}[/yellow]")
            continue

    if not news_items:
        console.print("[red]❌ 모든 RSS 수집 실패[/red]")

    return news_items[:20]

def save_to_supabase(news_items):
    console.print("[yellow]💾 Supabase에 저장 중...[/yellow]")
    saved = 0
    for item in news_items:
        try:
            res = supabase_request("POST", "news_list", data={
                "title": item["title"],
                "url": item["url"]
            })
            if res.status_code in (200, 201):
                saved += 1
            else:
                console.print(f"[red]저장 실패: {res.text}[/red]")
        except Exception as e:
            console.print(f"[red]저장 오류: {e}[/red]")
    console.print(f"[green]✅ {saved}개 저장 완료![/green]")
    return saved

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

    console.print()
    console.print(Panel.fit(
        Text("📰 IT 뉴스 헤드라인 대시보드", style="bold white on blue", justify="center"),
        border_style="bright_blue"
    ))
    console.print(f"[dim]수집 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n")

    if not data:
        console.print("[yellow]⚠️ 저장된 뉴스가 없습니다.[/yellow]")
        return

    table = Table(
        show_header=True,
        header_style="bold magenta",
        border_style="bright_black",
        show_lines=True
    )
    table.add_column("No.", style="dim", width=4, justify="right")
    table.add_column("제목", min_width=40, max_width=55)
    table.add_column("링크", min_width=30, max_width=45, style="cyan")
    table.add_column("수집 시각", width=19, style="green")

    for i, row in enumerate(data, 1):
        created = row.get("created_at", "")[:19].replace("T", " ") if row.get("created_at") else "-"
        url_short = row["url"][:45] + "..." if len(row["url"]) > 45 else row["url"]
        title = row["title"][:52] + "..." if len(row["title"]) > 52 else row["title"]
        table.add_row(str(i), title, url_short, created)

    console.print(table)
    console.print(f"\n[bold]총 [cyan]{len(data)}[/cyan]개 뉴스 표시 중[/bold]")

if __name__ == "__main__":
    news = fetch_it_news_rss()
    if news:
        save_to_supabase(news)
    show_dashboard()
