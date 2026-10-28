# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Query 5-day weather forecasts from weather.com.cn (China Weather Network) partner data APIs. A single Python script with no external dependencies. All output is in English.

## Commands

```bash
python weather.py                    # Beijing (default)
python weather.py 101020100          # Shanghai
python weather.py --help             # Usage info
```

## Architecture

`weather.py` fetches from two API endpoints that return JavaScript variable assignments (not JSON):

- **5-day forecast**: `http://d1.weather.com.cn/weixinfc/{city_code}.html` — returns `var fc = {...}` with `fc.f` array of 16 entries. Indices: 0=yesterday, 1=today, 2–6=next 5 days.
- **Current conditions**: `http://d1.weather.com.cn/sk_2d/{city_code}.html` — returns `var dataSK = {...}` with live temp, humidity, wind, AQI.

Responses are parsed by normalizing JS syntax (quoting unquoted keys, converting single quotes, removing trailing commas) then passing to `json.loads`.

### Key mappings (all English output)

- `WEATHER_CODES` — numeric weather codes to English labels (e.g. `"04"` → `"Thunderstorms"`)
- `WIND_DIRECTIONS` — Chinese wind direction strings to English abbreviations (e.g. `"西南风"` → `"SW"`)
- `DAY_LABELS` — Chinese day-of-week labels to English (e.g. `"星期五"` → `"Friday"`)
- `CITY_NAMES` — Chinese city names to English/pinyin for 36 major cities

City codes are 9-digit strings (e.g. `101010100` = Beijing, `101020100` = Shanghai). No pip packages needed.
