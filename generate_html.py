#!/usr/bin/env python3
"""
SJTU Dashboard - HTML 生成脚本
读取 data.json 生成漂亮的静态页面
"""

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "index.html")

# ── 天气图标映射（支持中英文） ─────────────────
WEATHER_EMOJI = {
    "晴": "☀️", "sunny": "☀️", "clear": "☀️",
    "多云": "⛅", "partly cloudy": "⛅",
    "阴": "☁️", "cloudy": "☁️", "overcast": "☁️",
    "霾": "🌫️", "薄雾": "🌫️", "雾": "🌫️", "mist": "🌫️", "fog": "🌫️", "haze": "🌫️",
    "小雨": "🌦️", "阵雨": "🌦️", "毛毛雨": "🌦️", "light rain": "🌦️",
    "中雨": "🌧️", "大雨": "🌧️", "雷阵雨": "🌧️", "雷暴雨": "🌧️", "moderate rain": "🌧️", "heavy rain": "🌧️",
    "雪": "❄️", "snow": "❄️",
    "雷暴": "⛈️", "thunder": "⛈️", "thunderstorm": "⛈️",
}


def weather_emoji(desc: str) -> str:
    for key, emoji in WEATHER_EMOJI.items():
        if key in desc:
            return emoji
    return "🌡️"


def _weather_block(w, has_err, weather_icon, forecast_html):
    """Build weather HTML block."""
    if has_err:
        return (
            '<div class="brief-item">'
            '<div class="brief-emoji">❌</div>'
            '<div class="brief-text"><div class="label">天气</div><div class="value" style="color:#999;">暂不可用</div></div>'
            '</div>'
        )
    parts = [
        '<div class="brief-item" style="flex-direction:column;align-items:stretch;">',
        '<div style="display:flex;align-items:center;gap:12px;">',
        '<div class="brief-emoji">', weather_icon, '</div>',
        '<div class="brief-text">',
        '<div class="label">上海 · 天气</div>',
        '<div class="value temp">', w["temp"], '°C</div>',
        '<div style="font-size:12px;color:#888;">',
        w["desc"], ' · 体感', w["feels_like"], '°C · 湿度', w["humidity"], '% · 风速', w["wind"], 'km/h',
        '</div></div></div>',
        '<div class="forecast">',
        forecast_html,
        '</div>',
        '</div>',
    ]
    return "".join(parts)


def _mail_block(m, has_err):
    """Build mail HTML block."""
    items = []
    for e in m.get("emails", [])[:5]:
        subj = e.get("subject", "")
        dt = e.get("date", "")
        items.append(
            '<div class="mail-list-item">'
            '<a class="mail-subject" href="https://mail.sjtu.edu.cn" target="_blank" title="' + subj + '">' + subj + '</a>'
            '<span class="mail-date">' + dt + '</span>'
            '</div>'
        )
    mail_list = "\n".join(items)

    error_html = ('<div class="mail-error">' + m.get("error", "") + '</div>') if has_err else ""

    return (
        '<div class="brief-item" style="flex-direction:column;align-items:stretch;">'
        '<div style="display:flex;align-items:center;gap:12px;">'
        '<div class="brief-emoji">📬</div>'
        '<div class="brief-text">'
        '<div class="label">交大邮箱未读</div>'
        '<div class="value" style="font-size:20px;">' + str(m.get("count", 0)) + '<span style="font-size:14px;color:#888;font-weight:400;"> 封</span></div>'
        + error_html +
        '</div></div>'
        '<div class="mail-list">' + mail_list + '</div>'
        '</div>'
    )


def render_page(data: dict) -> str:
    w = data.get("weather", {})
    c = data.get("countdown", {})
    m = data.get("mail", {})
    news_list = data.get("news", [])
    shuiyuan_list = data.get("shuiyuan", [])
    fetched_at = data.get("fetched_at", "")

    has_weather_err = "error" in w
    has_mail_err = "error" in m

    weather_icon = weather_emoji(w.get("desc", "")) if not has_weather_err else "❌"

    # ── 天气预报 ──
    forecast_html = ""
    if not has_weather_err and "forecast" in w:
        day_names = ["今天", "明天", "后天"]
        for i, f in enumerate(w["forecast"][:3]):
            forecast_html += (
                '<div class="forecast-item">'
                '<span class="forecast-day">' + day_names[i] + '</span>'
                '<span class="forecast-icon">' + weather_emoji(f["desc"]) + '</span>'
                '<span class="forecast-desc">' + f["desc"] + '</span>'
                '<span class="forecast-temp">'
                '<span class="forecast-high">' + f["high"] + '°</span>'
                ' / '
                '<span class="forecast-low">' + f["low"] + '°</span>'
                '</span>'
                '</div>'
            )

    weather_html = _weather_block(w, has_weather_err, weather_icon, forecast_html)
    mail_html = _mail_block(m, has_mail_err)

    # ── 要闻卡片 ──
    news_cards = ""
    for n in news_list:
        news_cards += (
            '<a class="news-item" href="' + n.get("url", "") + '" target="_blank">'
            '<span class="news-date">' + n.get("date", "") + '</span>'
            '<span class="news-title">' + n.get("title", "") + '</span>'
            '<p class="news-summary">' + n.get("summary", "") + '</p>'
            '</a>'
        )

    # ── 水源卡片 ──
    shuiyuan_cards = ""
    for s in shuiyuan_list:
        if "error" in s:
            shuiyuan_cards += '<div class="shuiyuan-item"><span class="shuiyuan-title" style="color:#999;">⚠️ ' + s["error"] + '</span></div>'
            continue
        sid = str(s.get("id", ""))
        title = s.get("title", "")
        url = s.get("url", "")
        posts = s.get("posts_count", 0)
        views = s.get("views", 0)
        likes = s.get("like_count", 0)
        likes_html = " ❤️ " + str(likes) if likes else ""
        shuiyuan_cards += (
            '<a class="shuiyuan-item" href="' + url + '" target="_blank">'
            '<span class="shuiyuan-rank">#' + sid + '</span>'
            '<span class="shuiyuan-title">' + title + '</span>'
            '<span class="shuiyuan-meta">💬 ' + str(posts) + '  👁️ ' + str(views) + likes_html + '</span>'
            '</a>'
        )

    no_data = '<div style="color:#ccc;text-align:center;padding:20px;">暂无数据</div>'

    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>交大看板 · SJTU Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
    background: #f5f6fa;
    color: #333;
    min-height: 100vh;
    padding: 20px;
  }
  .container { max-width: 1200px; margin: 0 auto; }

  .header { text-align: center; padding: 30px 0 20px; }
  .header h1 {
    font-size: 28px; font-weight: 700;
    background: linear-gradient(135deg, #c41e3a, #003366);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  }
  .header .subtitle { color: #888; font-size: 13px; margin-top: 6px; }
  .fetched-at { color: #aaa; font-size: 12px; margin-top: 4px; }

  .grid {
    display: grid;
    grid-template-columns: 1fr 1.2fr 1.2fr;
    gap: 20px;
    margin-top: 20px;
  }
  @media (max-width: 900px) { .grid { grid-template-columns: 1fr 1fr; } }
  @media (max-width: 600px) { .grid { grid-template-columns: 1fr; } }

  .card {
    background: #fff; border-radius: 14px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07); overflow: hidden;
    transition: box-shadow 0.2s;
  }
  .card:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.11); }
  .card-header {
    padding: 16px 20px 12px; font-size: 17px; font-weight: 600;
    display: flex; align-items: center; justify-content: space-between; gap: 8px;
    border-bottom: 1px solid #f0f0f0;
  }
  .card-header .more-link {
    font-size: 12px; color: #999; text-decoration: none; font-weight: 400;
  }
  .card-header .more-link:hover { color: #c41e3a; }
  .card-header .icon { font-size: 20px; }
  .card-body { padding: 14px 20px 18px; }

  .brief-grid { display: flex; flex-direction: column; gap: 12px; }
  .brief-item {
    display: flex; align-items: center; gap: 12px;
    padding: 12px 14px; background: #f8f9fc; border-radius: 10px;
  }
  .brief-emoji { font-size: 28px; width: 40px; text-align: center; }
  .brief-text { flex: 1; }
  .brief-text .label { font-size: 12px; color: #999; }
  .brief-text .value { font-size: 16px; font-weight: 600; color: #222; }
  .brief-text .value.temp { font-size: 22px; color: #e74c3c; }
  .brief-text .value.days { font-size: 26px; color: #c41e3a; }

  .forecast {
    display: flex; flex-direction: column; gap: 4px;
    padding-top: 6px; border-top: 1px solid #e8e8e8; width: 100%;
  }
  .forecast-item {
    display: flex; align-items: center; gap: 8px;
    font-size: 13px; padding: 3px 0;
  }
  .forecast-day { width: 32px; color: #888; font-size: 12px; }
  .forecast-icon { width: 20px; text-align: center; }
  .forecast-desc { flex: 1; color: #666; }
  .forecast-temp { text-align: right; }
  .forecast-high { color: #e74c3c; font-weight: 600; }
  .forecast-low { color: #3498db; font-weight: 600; }

  .mail-error { font-size: 12px; color: #bbb; margin-top: 2px; }
  .mail-list { margin-top: 4px; font-size: 13px; }
  .mail-list-item {
    padding: 4px 0; border-bottom: 1px solid #f5f5f5;
    display: flex; justify-content: space-between; gap: 8px;
  }
  .mail-list-item:last-child { border-bottom: none; }
  .mail-subject {
    color: #333; overflow: hidden; text-overflow: ellipsis;
    white-space: nowrap; max-width: 180px;
    text-decoration: none;
  }
  .mail-subject:hover { color: #c41e3a; text-decoration: underline; }
  .mail-date { color: #aaa; font-size: 11px; white-space: nowrap; }

  .news-item {
    display: block; padding: 12px 0; border-bottom: 1px solid #f2f2f2;
    text-decoration: none; color: inherit; transition: background 0.15s;
  }
  .news-item:last-child { border-bottom: none; }
  .news-item:hover { background: #fafbfc; margin: 0 -20px; padding: 12px 20px; }
  .news-date {
    display: inline-block; font-size: 11px; color: #c41e3a;
    background: #fef0f0; padding: 1px 8px; border-radius: 4px; margin-bottom: 4px;
  }
  .news-title { display: block; font-size: 14px; font-weight: 600; line-height: 1.4; margin-bottom: 4px; }
  .news-summary {
    font-size: 12px; color: #888; line-height: 1.5;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  }

  .shuiyuan-item {
    display: block; padding: 10px 0; border-bottom: 1px solid #f2f2f2;
    text-decoration: none; color: inherit; transition: background 0.15s;
  }
  .shuiyuan-item:last-child { border-bottom: none; }
  .shuiyuan-item:hover { background: #fafbfc; margin: 0 -20px; padding: 10px 20px; }
  .shuiyuan-rank { font-size: 11px; color: #999; margin-right: 6px; }
  .shuiyuan-title { display: block; font-size: 14px; font-weight: 500; line-height: 1.4; margin-bottom: 3px; }
  .shuiyuan-meta { font-size: 11px; color: #aaa; }

  .footer { text-align: center; padding: 30px 0; color: #bbb; font-size: 12px; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🎓 交大看板</h1>
    <div class="subtitle">天气 · 倒计时 · 要闻 · 水源 · 片刻交大</div>
    <div class="fetched-at">⏱ 数据更新于 """ + fetched_at + """</div>
  </div>

  <div class="grid">
    <div class="card">
      <div class="card-header"><span class="icon">📋</span> 今日简报</div>
      <div class="card-body">
        <div class="brief-grid">
""" + weather_html + """
          <div class="brief-item">
            <div class="brief-emoji">📅</div>
            <div class="brief-text">
              <div class="label">距离秋季学期开学</div>
              <div class="value days">""" + str(c.get("days_left", "?")) + """<span style="font-size:14px;color:#888;font-weight:400;"> 天</span></div>
              <div style="font-size:12px;color:#888;">目标：""" + c.get("target", "") + """</div>
            </div>
          </div>
""" + mail_html + """
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><span class="icon">📰</span> 交大要闻<a class="more-link" href="https://news.sjtu.edu.cn/jdyw/" target="_blank">更多></a></div>
      <div class="card-body">""" + (news_cards if news_cards else no_data) + """</div>
    </div>

    <div class="card">
      <div class="card-header"><span class="icon">💧</span> 水源热议<a class="more-link" href="https://shuiyuan.sjtu.edu.cn/" target="_blank">更多></a></div>
      <div class="card-body">""" + (shuiyuan_cards if shuiyuan_cards else no_data) + """</div>
    </div>
  </div>

  <div class="footer">
    上海交通大学 · <a href="https://news.sjtu.edu.cn" target="_blank" style="color:#999;text-decoration:none;">新闻学术网</a>
    · <a href="https://shuiyuan.sjtu.edu.cn" target="_blank" style="color:#999;text-decoration:none;">水源社区</a>
    · Powered by OpenClaw 🦞
  </div>
</div>
</body>
</html>"""


def main():
    if not os.path.isfile(DATA_PATH):
        print("⚠️ " + DATA_PATH + " 不存在，请先运行 fetch_all.py")
        return

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    html = render_page(data)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print("✅ HTML 已生成: " + OUTPUT_PATH)


if __name__ == "__main__":
    main()
