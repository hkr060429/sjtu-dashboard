#!/usr/bin/env python3
"""
SJTU Dashboard - 数据抓取脚本
聚合天气、交大要闻、水源热议、开学倒计时、邮箱未读
"""

import json
import os
import re
import sys
import subprocess
from datetime import datetime, date
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ── 路径配置 ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(BASE_DIR, "data.json")

# ── 公共 ──────────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
TIMEOUT = 15

SJTU_SKILL_DIR = os.path.expanduser(
    "~/.openclaw/workspace/skills/openclaw-sjtu"
)


# ════════════════════════════════════════════════════════════
# 模块 1: 天气
# ════════════════════════════════════════════════════════════
# 天气英文 → 中文映射
WEATHER_ZH_MAP = {
    "sunny": "晴", "clear": "晴", "clear sky": "晴",
    "partly cloudy": "多云", "cloudy": "多云", "overcast": "阴",
    "mist": "薄雾", "fog": "雾", "haze": "霾", "smoky haze": "霾",
    "light rain": "小雨", "moderate rain": "中雨", "heavy rain": "大雨",
    "light rain shower": "小阵雨", "moderate or heavy rain shower": "大阵雨",
    "patchy rain possible": "可能有零星小雨",
    "light drizzle": "毛毛雨",
    "thundery outbreaks possible": "可能有雷暴",
    "light snow": "小雪", "heavy snow": "大雪",
    "light sleet": "小冻雨", "heavy sleet": "大冻雨",
    "ice pellets": "冰雹",
    "blowing snow": "吹雪",
    "freezing fog": "冻雾",
    "patchy light rain with thunder": "雷阵雨",
    "moderate or heavy rain with thunder": "雷暴雨",
}


def weather_desc_zh(desc_en: str) -> str:
    """英文天气描述转中文"""
    desc_lower = desc_en.strip().lower()
    for eng, zh in WEATHER_ZH_MAP.items():
        if eng in desc_lower:
            return zh
    return desc_en  # 找不到就返回原文


def fetch_weather() -> dict:
    """获取上海当前天气"""
    try:
        resp = requests.get(
            "https://wttr.in/Shanghai?format=j1",
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        cc = data["current_condition"][0]

        desc_en = cc["weatherDesc"][0]["value"]

        # 获取今明后天预报
        forecast = []
        for day in data.get("weather", [])[:3]:
            forecast.append({
                "date": day["date"],
                "high": day["maxtempC"],
                "low": day["mintempC"],
                "desc": weather_desc_zh(day["hourly"][0]["weatherDesc"][0]["value"]),
            })

        return {
            "temp": cc["temp_C"],
            "feels_like": cc["FeelsLikeC"],
            "humidity": cc["humidity"],
            "wind": cc["windspeedKmph"],
            "desc_en": desc_en,
            "desc": weather_desc_zh(desc_en),
            "icon": cc["weatherIconUrl"][0]["value"],
            "forecast": forecast,
        }
    except Exception as e:
        return {"error": str(e)}


# ════════════════════════════════════════════════════════════
# 模块 2: 开学倒计时
# ════════════════════════════════════════════════════════════
def fetch_countdown() -> dict:
    """计算距离 2026年9月15日 秋季学期开学的天数"""
    today = date.today()
    target = date(2026, 9, 15)
    delta = (target - today).days

    return {
        "target": "2026年9月15日",
        "target_label": "秋季学期开学",
        "days_left": max(delta, 0),
        "is_passed": delta < 0,
        "passed_days": abs(delta) if delta < 0 else 0,
    }


# ════════════════════════════════════════════════════════════
# 模块 3: 交大邮箱（未读邮件数）
# ════════════════════════════════════════════════════════════
def fetch_mail_unread() -> dict:
    """直连 IMAP 获取未读邮件数及最近5封"""
    config_path = os.path.join(SJTU_SKILL_DIR, "config.json")
    if not os.path.isfile(config_path):
        return {"error": "config.json 不存在", "count": 0, "emails": []}

    with open(config_path) as f:
        cfg = json.load(f)

    username = cfg.get("sjtu_username", "")
    password = cfg.get("sjtu_password", "")
    if not username or not password:
        return {"error": "config.json 中缺少 sjtu_username 或 sjtu_password", "count": 0, "emails": []}

    email_addr = f"{username}@sjtu.edu.cn"

    try:
        import imaplib
        import email
        from email.header import decode_header
        from email.utils import parsedate_to_datetime

        imap = imaplib.IMAP4_SSL("mail.sjtu.edu.cn", 993, timeout=15)
        imap.login(email_addr, password)
        imap.select("INBOX")

        # 未读计数
        status, msgs = imap.search(None, "UNSEEN")
        unread_ids = msgs[0].split() if msgs[0] else []
        total_unread = len(unread_ids)

        # 取最近5封未读
        emails = []
        recent_ids = unread_ids[-5:] if len(unread_ids) > 5 else unread_ids
        for mid in reversed(recent_ids):
            status, data = imap.fetch(mid, "(RFC822)")
            if status != "OK":
                continue
            msg = email.message_from_bytes(data[0][1])

            subject = ""
            if msg["Subject"]:
                parts = decode_header(msg["Subject"])
                for part, charset in parts:
                    if isinstance(part, bytes):
                        charset = charset or "utf-8"
                        try:
                            subject += part.decode(charset, errors="replace")
                        except:
                            subject += part.decode("utf-8", errors="replace")
                    else:
                        subject += str(part)

            sender = msg.get("From", "")
            date_str = msg.get("Date", "")
            try:
                dt = parsedate_to_datetime(date_str)
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass

            emails.append({
                "subject": subject.strip(),
                "sender": sender.strip(),
                "date": date_str,
            })

        imap.logout()
        return {"count": total_unread, "emails": emails}
    except Exception as e:
        return {"error": str(e), "count": 0, "emails": []}


# ════════════════════════════════════════════════════════════
# 模块 4: 交大要闻
# ════════════════════════════════════════════════════════════
def fetch_news(limit: int = 5) -> list:
    """爬取 news.sjtu.edu.cn/jdyw 最新新闻"""
    url = "https://news.sjtu.edu.cn/jdyw/index.html"
    results = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.encoding = "utf-8"
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        ul = soup.select_one("ul.list.list-11.item-4")
        if not ul:
            return [{"title": "⚠️ 页面结构解析失败", "url": url, "date": "", "summary": ""}]

        items = ul.find_all("li", recursive=False)

        for li in items:
            if len(results) >= limit:
                break

            card = li.find("a", class_="card")
            if not card:
                continue

            # 标题
            title_el = card.select_one("p.dot")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            # 链接
            href = card.get("href", "")
            if href and not href.startswith("http"):
                href = "https://news.sjtu.edu.cn" + href

            # 摘要
            summary_el = card.select_one("div.des")
            summary = summary_el.get_text(strip=True) if summary_el else ""

            # 日期
            date_el = card.select_one("div.time span")
            date_str = date_el.get_text(strip=True) if date_el else ""

            # 来源
            source_el = card.select_one("div.source p")
            source = source_el.get_text(strip=True) if source_el else ""

            results.append({
                "title": title,
                "url": href,
                "date": date_str,
                "source": source,
                "summary": summary,
            })

        return results if results else [{"title": "（暂无新闻）", "url": url, "date": "", "summary": ""}]

    except Exception as e:
        return [{"title": f"⚠️ 抓取失败: {e}", "url": url, "date": "", "summary": ""}]


# ════════════════════════════════════════════════════════════
# 模块 5: 水源热议
# ════════════════════════════════════════════════════════════
def fetch_shuiyuan(limit: int = 10) -> list:
    """获取水源社区最新话题"""
    script = os.path.join(
        SJTU_SKILL_DIR, "scripts", "shuiyuan_discourse.mjs"
    )
    if not os.path.isfile(script):
        return [{"error": "shuiyuan_discourse.mjs 不存在"}]

    try:
        result = subprocess.run(
            ["node", script, "latest"],
            capture_output=True,
            text=True,
            timeout=20,
            cwd=SJTU_SKILL_DIR,
        )
        data = json.loads(result.stdout)

        if not data.get("ok"):
            return [{"error": data.get("error", "请求失败")}]

        topics = data.get("results", [])
        results = []
        for t in topics[:limit]:
            # 计算相对时间
            posted = t.get("last_posted_at", "")
            results.append({
                "id": t.get("id"),
                "title": t.get("title", ""),
                "url": t.get("url", ""),
                "posts_count": t.get("posts_count", 0),
                "views": t.get("views", 0),
                "like_count": t.get("like_count", 0),
                "last_posted_at": posted,
                "category_id": t.get("category_id"),
            })

        return results
    except Exception as e:
        return [{"error": str(e)}]


# ════════════════════════════════════════════════════════════
# 主函数
# ════════════════════════════════════════════════════════════
def main():
    print("🔍 正在抓取数据...")

    print("  [1/5] 天气...", end=" ")
    weather = fetch_weather()
    print("OK" if "error" not in weather else f"FAIL ({weather.get('error','')[:30]})")

    print("  [2/5] 开学倒计时...", end=" ")
    countdown = fetch_countdown()
    print(f"{countdown['days_left']}天")

    print("  [3/5] 邮箱未读...", end=" ")
    mail = fetch_mail_unread()
    print(f"{mail.get('count', 0)}封未读" if mail.get('count', 0) > 0 else "OK")

    print("  [4/5] 交大要闻...", end=" ")
    news = fetch_news(limit=5)
    print(f"{len(news)}条")

    print("  [5/5] 水源热议...", end=" ")
    shuiyuan = fetch_shuiyuan(limit=10)
    print(f"{len(shuiyuan)}个话题")

    # 聚合
    data = {
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "weather": weather,
        "countdown": countdown,
        "mail": mail,
        "news": news,
        "shuiyuan": shuiyuan,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 数据已保存到 {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
