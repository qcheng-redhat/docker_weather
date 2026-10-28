#!/usr/bin/env python3
"""Query 5-day weather forecast from partner.weather.com.cn."""

import argparse
import json
import os
import re
import sys
import webbrowser

import requests

FORECAST_URL = "http://d1.weather.com.cn/weixinfc/{city_code}.html"
CURRENT_URL = "http://d1.weather.com.cn/sk_2d/{city_code}.html"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; Pixel 3) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.101 Mobile Safari/537.36"
    ),
    "Referer": "http://partner.weather.com.cn/",
}

WEATHER_CODES = {
    "00": "Clear",
    "01": "Partly Cloudy",
    "02": "Overcast",
    "03": "Showers",
    "04": "Thunderstorms",
    "05": "Hailstorms",
    "06": "Sleet",
    "07": "Light Rain",
    "08": "Moderate Rain",
    "09": "Heavy Rain",
    "10": "Rainstorm",
    "11": "Severe Rainstorm",
    "12": "Extreme Rainstorm",
    "13": "Snow Showers",
    "14": "Light Snow",
    "15": "Moderate Snow",
    "16": "Heavy Snow",
    "17": "Snowstorm",
    "18": "Fog",
    "19": "Freezing Rain",
    "20": "Sandstorm",
    "21": "Light to Mod. Rain",
    "22": "Mod. to Heavy Rain",
    "23": "Heavy to Rainstorm",
    "24": "Rainstorm to Severe",
    "25": "Severe to Extreme",
    "26": "Light to Mod. Snow",
    "27": "Mod. to Heavy Snow",
    "28": "Heavy to Snowstorm",
    "29": "Dust",
    "30": "Blowing Sand",
    "31": "Severe Sandstorm",
    "53": "Haze",
    "99": "N/A",
    "301": "Rain",
    "302": "Snow",
}

WIND_DIRECTIONS = {
    "东风": "E",
    "南风": "S",
    "西风": "W",
    "北风": "N",
    "东北风": "NE",
    "东南风": "SE",
    "西南风": "SW",
    "西北风": "NW",
    "旋转风": "Variable",
    "微风": "Light",
}

DAY_LABELS = {
    "昨天": "Yesterday",
    "今天": "Today",
    "明天": "Tomorrow",
    "星期一": "Monday",
    "星期二": "Tuesday",
    "星期三": "Wednesday",
    "星期四": "Thursday",
    "星期五": "Friday",
    "星期六": "Saturday",
    "星期日": "Sunday",
}

CITY_NAMES = {
    "北京": "Beijing",
    "上海": "Shanghai",
    "广州": "Guangzhou",
    "深圳": "Shenzhen",
    "杭州": "Hangzhou",
    "南京": "Nanjing",
    "成都": "Chengdu",
    "武汉": "Wuhan",
    "天津": "Tianjin",
    "重庆": "Chongqing",
    "西安": "Xi'an",
    "长沙": "Changsha",
    "郑州": "Zhengzhou",
    "济南": "Jinan",
    "青岛": "Qingdao",
    "大连": "Dalian",
    "厦门": "Xiamen",
    "苏州": "Suzhou",
    "福州": "Fuzhou",
    "合肥": "Hefei",
    "哈尔滨": "Harbin",
    "长春": "Changchun",
    "沈阳": "Shenyang",
    "昆明": "Kunming",
    "贵阳": "Guiyang",
    "南宁": "Nanning",
    "海口": "Haikou",
    "拉萨": "Lhasa",
    "乌鲁木齐": "Urumqi",
    "呼和浩特": "Hohhot",
    "银川": "Yinchuan",
    "兰州": "Lanzhou",
    "西宁": "Xining",
    "石家庄": "Shijiazhuang",
    "太原": "Taiyuan",
    "南昌": "Nanchang",
    "香港": "Hong Kong",
    "澳门": "Macau",
    "台北": "Taipei",
}

# ── helpers ──────────────────────────────────────────────────────────


def weather_label(code: str) -> str:
    """Convert a weather code to an English label."""
    return WEATHER_CODES.get(code, f"N/A({code})")


def wind_label(chinese_wind: str) -> str:
    """Convert a Chinese wind direction string to an English abbreviation."""
    return WIND_DIRECTIONS.get(chinese_wind, chinese_wind)


def day_label(chinese_day: str) -> str:
    """Convert a Chinese day-of-week label to English."""
    return DAY_LABELS.get(chinese_day, chinese_day)


def city_name(raw: str) -> str:
    """Convert a Chinese city name to English/pinyin if known."""
    return CITY_NAMES.get(raw, raw)


# ── data fetching ────────────────────────────────────────────────────


def fetch(url: str) -> str:
    """Fetch a URL and return the response text."""
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def parse_js_var(text: str, var_name: str) -> dict:
    """Extract a JavaScript variable assignment like `var name = {...}` from text."""
    pattern = rf"var\s+{var_name}\s*=\s*(.+)$"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find variable '{var_name}' in response")
    return parse_js_object(match.group(1))


def parse_js_object(js_obj: str) -> dict:
    """Parse a JavaScript object literal string into a Python dict."""
    js_obj = re.sub(r"//.*", "", js_obj)
    js_obj = re.sub(r"/\*.*?\*/", "", js_obj, flags=re.DOTALL)
    js_obj = re.sub(r"([{,]\s*)(\w+)\s*:", r'\1"\2":', js_obj)
    js_obj = re.sub(r"'([^'\\]*(\\.[^'\\]*)*)'", r'"\1"', js_obj)
    js_obj = re.sub(r",(\s*[}\]])", r"\1", js_obj)
    try:
        return json.loads(js_obj)
    except json.JSONDecodeError:
        return _parse_js_fallback(js_obj)


def _parse_js_fallback(js_str: str) -> dict:
    result = {}
    pattern = r'"(\w+)"\s*:\s*((?:"[^"]*")|(?:\[.*?\])|(?:\{[^}]*\})|(?:[^,}\]]+))'
    for match in re.finditer(pattern, js_str, re.DOTALL):
        key = match.group(1)
        value = match.group(2).strip()
        if value.startswith("["):
            try:
                result[key] = json.loads(value)
            except json.JSONDecodeError:
                result[key] = _parse_js_array(value)
        elif value.startswith('"'):
            result[key] = value.strip('"')
        else:
            result[key] = value
    return result


def _parse_js_array(js_arr: str) -> list:
    js_arr = js_arr.strip("[]")
    if not js_arr.strip():
        return []
    items = []
    depth = 0
    current = ""
    for ch in js_arr:
        if ch in "{[":
            depth += 1
            current += ch
        elif ch in "}]":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            items.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        items.append(current.strip())
    result = []
    for item in items:
        item = item.strip()
        if item.startswith("{"):
            result.append(parse_js_object(item))
        elif item.startswith('"'):
            result.append(item.strip('"'))
        elif item.isdigit():
            result.append(int(item))
        else:
            result.append(item)
    return result


def fetch_forecast(city_code: str) -> list[dict]:
    url = FORECAST_URL.format(city_code=city_code)
    text = fetch(url)
    data = parse_js_var(text, "fc")
    return data.get("f", [])


def fetch_current(city_code: str) -> dict:
    url = CURRENT_URL.format(city_code=city_code)
    text = fetch(url)
    return parse_js_var(text, "dataSK")


# ── data normalisation ───────────────────────────────────────────────


def normalize_current(raw: dict) -> dict:
    """Pull the fields we display from a raw current-conditions dict."""
    c = city_name(raw.get("cityname", "Unknown"))

    rc = raw.get("weathercode", "")
    if rc and rc[0] in ("d", "n"):
        rc = rc[1:]
    cond = weather_label(rc) if rc else raw.get("weather", "")

    temp = raw.get("temp", "")
    humid = raw.get("SD", "")
    aqi = raw.get("aqi", "")

    wd = wind_label(raw.get("WD", ""))
    ws = raw.get("WS", "")
    ws = ws.replace("级", "") if "级" in ws else ws
    ws = f"Lvl {ws}" if ws.isdigit() else ws

    updated = raw.get("time", "")

    return {
        "city": c,
        "condition": cond,
        "temp": temp,
        "humidity": humid,
        "aqi": aqi,
        "wind_dir": wd,
        "wind_speed": ws,
        "updated": updated,
    }


def normalize_forecast_day(day: dict) -> dict:
    """Pull the fields we display from a raw forecast-day dict."""
    wf = day.get("fg", "")
    wf = wf.replace("级", "") if "级" in wf else wf
    wf = f"Lvl {wf}" if wf.strip().isdigit() else wf

    return {
        "date": f"{day.get('fi', '')} {day_label(day.get('fj', ''))}",
        "day_weather": weather_label(day.get("fa", "")),
        "night_weather": weather_label(day.get("fb", "")),
        "high": f"{day.get('fc', '')}°C",
        "low": f"{day.get('fd', '')}°C",
        "wind": wind_label(day.get("fe", "")),
        "wind_force": wf,
    }


# ── terminal display ─────────────────────────────────────────────────


def display_weather(current: dict, forecast_days: list[dict]) -> None:
    cc = normalize_current(current)
    print("┌" + "─" * 60 + "┐")
    print(f"│  {cc['city']}  Current Conditions  (updated {cc['updated']})".ljust(61) + "│")
    print(f"│  Temp: {cc['temp']}°C   Humidity: {cc['humidity']}   Wind: {cc['wind_dir']} {cc['wind_speed']}".ljust(61) + "│")
    print(f"│  Weather: {cc['condition']}   AQI: {cc['aqi']}".ljust(61) + "│")
    print("└" + "─" * 60 + "┘")
    print()

    header = f"{'Date':<16} {'Weather (Day/Night)':<24} {'High':<8} {'Low':<8} {'Wind':<10} {'Force':<6}"
    sep = "─" * len(header)
    print(header)
    print(sep)

    for day in forecast_days:
        d = normalize_forecast_day(day)
        print(f"{d['date']:<16} {d['day_weather'] + ' / ' + d['night_weather']:<24} "
              f"{d['high']:<8} {d['low']:<8} {d['wind']:<10} {d['wind_force']:<6}")

    print(sep)


# ── HTML display ─────────────────────────────────────────────────────


def generate_html(current: dict, forecast_days: list[dict], city_code: str) -> str:
    cc = normalize_current(current)
    days = [normalize_forecast_day(d) for d in forecast_days]

    cards = ""
    for d in days:
        cards += f"""\
            <div class="day-card">
                <div class="day-date">{d['date']}</div>
                <div class="day-weather">{d['day_weather']} / {d['night_weather']}</div>
                <div class="day-temps"><span class="high">{d['high']}</span> <span class="low">{d['low']}</span></div>
                <div class="day-wind">Wind {d['wind']} {d['wind_force']}</div>
            </div>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Weather — {cc['city']}</title>
<style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        color: #e0e0e0;
        min-height: 100vh;
        display: flex;
        justify-content: center;
        padding: 40px 16px;
    }}
    .container {{ max-width: 720px; width: 100%; }}

    .current-card {{
        background: rgba(255,255,255,0.08);
        backdrop-filter: blur(12px);
        border-radius: 20px;
        padding: 32px;
        margin-bottom: 28px;
        text-align: center;
    }}
    .current-card .city {{ font-size: 26px; font-weight: 600; margin-bottom: 4px; }}
    .current-card .updated {{ font-size: 12px; color: #999; margin-bottom: 20px; }}
    .current-card .temp {{ font-size: 56px; font-weight: 200; line-height: 1; }}
    .current-card .condition {{ font-size: 18px; color: #ccc; margin: 8px 0 16px; }}
    .current-details {{
        display: flex;
        justify-content: center;
        gap: 32px;
        flex-wrap: wrap;
        font-size: 14px;
        color: #aaa;
    }}
    .current-details span {{ display: flex; align-items: center; gap: 6px; }}

    .forecast-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
        gap: 12px;
    }}
    .day-card {{
        background: rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 20px 16px;
        text-align: center;
        transition: background 0.2s;
    }}
    .day-card:hover {{ background: rgba(255,255,255,0.12); }}
    .day-date {{ font-size: 13px; color: #aaa; margin-bottom: 10px; }}
    .day-weather {{ font-size: 14px; margin-bottom: 10px; line-height: 1.4; }}
    .day-temps {{ margin-bottom: 8px; }}
    .high {{ color: #ff9c00; font-size: 18px; font-weight: 600; }}
    .low {{ color: #30a4d5; font-size: 18px; font-weight: 600; margin-left: 8px; }}
    .day-wind {{ font-size: 12px; color: #888; }}

    .aqi-dot {{
        display: inline-block;
        width: 10px; height: 10px;
        border-radius: 50%;
        margin-right: 4px;
        vertical-align: middle;
    }}
</style>
</head>
<body>
<div class="container">
    <div class="current-card">
        <div class="city">{cc['city']}</div>
        <div class="updated">updated {cc['updated']}</div>
        <div class="temp">{cc['temp']}°C</div>
        <div class="condition">{cc['condition']}</div>
        <div class="current-details">
            <span>💧 Humidity {cc['humidity']}</span>
            <span>🍃 {cc['wind_dir']} {cc['wind_speed']}</span>
            <span>🌬 AQI {cc['aqi']}</span>
        </div>
    </div>
    <div class="forecast-grid">
        {cards}
    </div>
</div>
</body>
</html>"""


# ── main ─────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query 5-day weather forecast from weather.com.cn",
    )
    parser.add_argument(
        "city_code",
        nargs="?",
        default="101010100",
        help="City code (default: 101010100 Beijing), e.g. 101020100=Shanghai, 101280101=Guangzhou",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate an HTML page and open it in the browser",
    )
    args = parser.parse_args()

    city_code = args.city_code.strip()
    if not re.match(r"^\d{9}$", city_code):
        print(f"Error: invalid city code '{city_code}', must be 9 digits", file=sys.stderr)
        sys.exit(1)

    # Fetch data
    try:
        current = fetch_current(city_code)
    except Exception as e:
        print(f"Failed to fetch current conditions: {e}", file=sys.stderr)
        current = {}

    try:
        all_days = fetch_forecast(city_code)
        forecast_5d = all_days[2:7]  # 0=yesterday, 1=today, 2–6=next 5 days
    except Exception as e:
        print(f"Failed to fetch forecast: {e}", file=sys.stderr)
        sys.exit(1)

    if not forecast_5d:
        print("No 5-day forecast data available", file=sys.stderr)
        sys.exit(1)

    if args.html:
        html = generate_html(current, forecast_5d, city_code)
        path = os.path.abspath("weather.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open("file://" + path)
        print(f"Opened {path}")
    else:
        display_weather(current, forecast_5d)


if __name__ == "__main__":
    main()
