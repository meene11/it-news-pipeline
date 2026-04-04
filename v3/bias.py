import os
import json
import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from datetime import datetime
from collections import defaultdict
from urllib.parse import urlparse

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

console = Console()

# ── 매체 식별 ──────────────────────────────────────────────

SOURCE_MAP = {
    "zdnet": "ZDNet Korea",
    "bloter": "Bloter",
    "etnews": "ETNews",
    "feedburner.com/bloter": "Bloter",
}

def identify_source(url):
    """URL에서 매체를 식별"""
    url_lower = url.lower()
    for key, name in SOURCE_MAP.items():
        if key in url_lower:
            return name
    domain = urlparse(url).netloc
    return domain or "Unknown"

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

# ── 매체 정보 업데이트 ─────────────────────────────────────

def update_source_info():
    """news_list에 source 컬럼이 NULL인 뉴스의 매체를 식별하여 업데이트"""
    console.print("[cyan]📡 매체 정보 업데이트 중...[/cyan]")

    res = supabase_request("GET", "news_list", params={
        "select": "id,url,source",
        "source": "is.null",
        "limit": "100"
    })
    if res.status_code != 200:
        console.print(f"[red]조회 실패: {res.text}[/red]")
        return 0

    news = res.json()
    updated = 0

    for item in news:
        source = identify_source(item["url"])
        patch_res = supabase_request("PATCH", "news_list",
            data={"source": source},
            params={"id": f"eq.{item['id']}"}
        )
        if patch_res.status_code in (200, 204):
            updated += 1

    console.print(f"[green]✅ {updated}건 매체 정보 업데이트[/green]\n")
    return updated

# ── 편향 분석 ──────────────────────────────────────────────

def calculate_bias_scores():
    """매체별 감성 분포를 집계하고 Bias Score를 산출"""

    # 감성 분석 완료된 뉴스 조회
    res = supabase_request("GET", "news_list", params={
        "select": "id,title,url,sentiment,confidence,source,created_at",
        "sentiment": "not.is.null",
        "order": "created_at.desc",
        "limit": "200"
    })
    if res.status_code != 200:
        console.print(f"[red]뉴스 조회 실패: {res.text}[/red]")
        return {}

    news = res.json()
    if not news:
        console.print("[yellow]감성 분석된 뉴스가 없습니다. v2 analyzer.py를 먼저 실행하세요.[/yellow]")
        return {}

    # 매체별 감성 집계
    source_sentiments = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0, "total": 0})

    for item in news:
        source = item.get("source") or identify_source(item["url"])
        sentiment = item.get("sentiment", "neutral")
        source_sentiments[source][sentiment] += 1
        source_sentiments[source]["total"] += 1

    # 전체 평균 감성 비율
    total_all = sum(s["total"] for s in source_sentiments.values())
    total_pos = sum(s["positive"] for s in source_sentiments.values())
    total_neu = sum(s["neutral"] for s in source_sentiments.values())
    total_neg = sum(s["negative"] for s in source_sentiments.values())

    avg_pos = total_pos / total_all if total_all > 0 else 0
    avg_neu = total_neu / total_all if total_all > 0 else 0
    avg_neg = total_neg / total_all if total_all > 0 else 0

    # 매체별 Bias Score 산출
    bias_results = {}

    for source, counts in source_sentiments.items():
        total = counts["total"]
        if total < 2:  # 최소 2건 이상이어야 의미 있음
            continue

        p_pos = counts["positive"] / total
        p_neu = counts["neutral"] / total
        p_neg = counts["negative"] / total

        # Bias Score = (|P - Avg| 합) / 2 → 0.0 ~ 1.0
        bias_score = (
            abs(p_pos - avg_pos) +
            abs(p_neu - avg_neu) +
            abs(p_neg - avg_neg)
        ) / 2

        bias_results[source] = {
            "total": total,
            "positive": counts["positive"],
            "neutral": counts["neutral"],
            "negative": counts["negative"],
            "pos_pct": p_pos * 100,
            "neu_pct": p_neu * 100,
            "neg_pct": p_neg * 100,
            "bias_score": round(bias_score, 3)
        }

    return bias_results, {"pos": avg_pos * 100, "neu": avg_neu * 100, "neg": avg_neg * 100}

# ── 프레이밍 분석 (LLM) ───────────────────────────────────

def analyze_framing(keyword=None):
    """동일 키워드에 대한 매체별 프레이밍 차이 분석"""
    if not OPENAI_API_KEY:
        return None

    # 키워드와 연관된 뉴스 조회
    params = {
        "select": "title,source,sentiment",
        "sentiment": "not.is.null",
        "source": "not.is.null",
        "order": "created_at.desc",
        "limit": "30"
    }

    res = supabase_request("GET", "news_list", params=params)
    if res.status_code != 200 or not res.json():
        return None

    news = res.json()

    # 매체별 뉴스 그룹핑
    by_source = defaultdict(list)
    for item in news:
        by_source[item["source"]].append(item["title"])

    if len(by_source) < 2:
        return None

    # LLM 프레이밍 분석
    source_titles = ""
    for source, titles in by_source.items():
        titles_str = "\n  ".join(f"- {t}" for t in titles[:5])
        source_titles += f"\n[{source}]\n  {titles_str}\n"

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
                    "너는 미디어 편향 분석 전문가야.\n"
                    "여러 매체의 뉴스 제목을 비교하여 프레이밍 차이를 분석해.\n\n"
                    "JSON 형식으로 응답:\n"
                    "{\n"
                    '  "analysis": [\n'
                    '    {"source": "매체명", "frame": "주요 프레임", "tone": "보도 어조 특징"}\n'
                    "  ],\n"
                    '  "comparison": "매체 간 차이점 요약 (2-3문장)",\n'
                    '  "bias_direction": "가장 편향적인 매체와 그 방향"\n'
                    "}"
                )
            },
            {
                "role": "user",
                "content": f"다음 매체별 뉴스 제목을 비교 분석해:\n{source_titles}"
            }
        ],
        "temperature": 0.2,
        "max_tokens": 500
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            content = res.json()["choices"][0]["message"]["content"]
            return json.loads(content)
    except Exception as e:
        console.print(f"[red]프레이밍 분석 실패: {e}[/red]")

    return None

# ── 편향 분석 결과 저장 ────────────────────────────────────

def save_bias_report(bias_results):
    """편향 분석 결과를 bias_reports 테이블에 저장"""
    today = datetime.now().strftime("%Y-%m-%d")

    for source, data in bias_results.items():
        report = {
            "keyword": "_overall",
            "date": today,
            "source": source,
            "positive_pct": round(data["pos_pct"], 2),
            "neutral_pct": round(data["neu_pct"], 2),
            "negative_pct": round(data["neg_pct"], 2),
            "bias_score": data["bias_score"]
        }
        supabase_request("POST", "bias_reports", data=report)

# ── 메인 실행 ──────────────────────────────────────────────

def run_bias_analysis():
    console.print(Panel.fit(
        Text("📐 매체별 편향 분석기 (v3)", style="bold white on red", justify="center"),
        border_style="bright_red"
    ))
    console.print(f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n")

    # 1. 매체 정보 업데이트
    update_source_info()

    # 2. 편향 점수 산출
    console.print("[cyan]📊 편향 점수 산출 중...[/cyan]")
    result = calculate_bias_scores()
    if not result:
        return

    bias_results, avg = result

    if not bias_results:
        console.print("[yellow]분석할 데이터가 부족합니다.[/yellow]")
        return

    # 3. 결과 출력
    console.print(Panel.fit(
        Text("📊 매체별 감성 분포 & 편향 점수", style="bold white on purple", justify="center"),
        border_style="bright_magenta"
    ))

    # 전체 평균 표시
    console.print(f"\n[dim]전체 평균: 긍정 {avg['pos']:.1f}% / 중립 {avg['neu']:.1f}% / 부정 {avg['neg']:.1f}%[/dim]\n")

    table = Table(show_header=True, header_style="bold cyan", border_style="bright_black", show_lines=True)
    table.add_column("매체", min_width=12)
    table.add_column("기사 수", width=8, justify="right")
    table.add_column("긍정", width=8, justify="right", style="green")
    table.add_column("중립", width=8, justify="right", style="yellow")
    table.add_column("부정", width=8, justify="right", style="red")
    table.add_column("Bias Score", width=12, justify="center")
    table.add_column("판정", width=10, justify="center")

    for source, data in sorted(bias_results.items(), key=lambda x: x[1]["bias_score"], reverse=True):
        bs = data["bias_score"]
        if bs >= 0.3:
            level = "[red]높음[/red]"
        elif bs >= 0.15:
            level = "[yellow]보통[/yellow]"
        else:
            level = "[green]낮음[/green]"

        score_bar_len = int(bs * 20)
        score_color = "red" if bs >= 0.3 else "yellow" if bs >= 0.15 else "green"
        score_display = f"[{score_color}]{bs:.3f}[/{score_color}]"

        table.add_row(
            source,
            str(data["total"]),
            f"{data['pos_pct']:.1f}%",
            f"{data['neu_pct']:.1f}%",
            f"{data['neg_pct']:.1f}%",
            score_display,
            level
        )

    console.print(table)

    # Bias Score 설명
    console.print("\n[dim]Bias Score 해석:[/dim]")
    console.print("[dim]  0.00 ~ 0.15: 편향 낮음 (전체 평균과 유사)[/dim]")
    console.print("[dim]  0.15 ~ 0.30: 편향 보통 (약간의 감성 편중)[/dim]")
    console.print("[dim]  0.30 이상  : 편향 높음 (뚜렷한 감성 편중)[/dim]")

    # 4. 프레이밍 분석
    if OPENAI_API_KEY:
        console.print("\n[cyan]🔍 LLM 프레이밍 분석 중...[/cyan]")
        framing = analyze_framing()
        if framing:
            console.print(Panel.fit(
                Text("🔍 프레이밍 분석 결과", style="bold white on blue", justify="center"),
                border_style="bright_blue"
            ))

            if "analysis" in framing:
                for item in framing["analysis"]:
                    console.print(f"  [{item.get('source', '?')}]")
                    console.print(f"    프레임: {item.get('frame', '-')}")
                    console.print(f"    어조: {item.get('tone', '-')}\n")

            if "comparison" in framing:
                console.print(f"  [bold]비교 분석:[/bold] {framing['comparison']}\n")

            if "bias_direction" in framing:
                console.print(f"  [bold]편향 방향:[/bold] {framing['bias_direction']}")

    # 5. 결과 저장
    console.print("\n[cyan]💾 분석 결과 저장 중...[/cyan]")
    try:
        save_bias_report(bias_results)
        console.print("[green]✅ bias_reports 테이블에 저장 완료[/green]")
    except Exception as e:
        console.print(f"[yellow]저장 실패 (테이블이 없을 수 있음): {e}[/yellow]")
        console.print("[dim]Supabase에서 bias_reports 테이블을 먼저 생성하세요.[/dim]")


if __name__ == "__main__":
    run_bias_analysis()
